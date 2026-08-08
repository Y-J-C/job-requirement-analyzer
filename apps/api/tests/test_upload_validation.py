from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

import pytest

from app.parsing.errors import DocumentError
from app.parsing.validation import validate_upload


class NoUnboundedRead(BytesIO):
    def read(self, size: int = -1) -> bytes:
        if size < 0:
            raise AssertionError("upload validation must read in bounded chunks")
        return super().read(size)


def make_docx(*, oversized_compressed_entry: bool = False) -> bytes:
    output = BytesIO()
    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", "<Types />")
        archive.writestr("word/document.xml", "<document />")
        if oversized_compressed_entry:
            archive.writestr("word/media/filler.bin", b"0" * 2_000_000)
    return output.getvalue()


@pytest.mark.parametrize(
    ("filename", "mime_type", "content", "expected_media_type"),
    [
        ("岗位.md", "text/markdown", b"# Data role\nSQL", "text/markdown"),
        ("岗位.pdf", "application/pdf", b"%PDF-1.4\nexample", "application/pdf"),
        (
            "岗位.docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            make_docx(),
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ),
    ],
)
def test_validate_upload_detects_supported_documents(
    filename: str,
    mime_type: str,
    content: bytes,
    expected_media_type: str,
) -> None:
    result = validate_upload(BytesIO(content), filename, mime_type, max_bytes=10_000_000)

    assert result.original_filename == filename
    assert result.detected_media_type == expected_media_type
    assert result.size_bytes == len(content)
    assert len(result.sha256) == 64
    assert result.content.read() == content


def test_validate_upload_strips_path_from_display_filename() -> None:
    result = validate_upload(
        BytesIO(b"plain markdown"),
        "../../private/岗位.md",
        "text/plain",
        max_bytes=100,
    )

    assert result.original_filename == "岗位.md"


def test_validate_markdown_never_reads_source_without_a_bound() -> None:
    result = validate_upload(
        NoUnboundedRead(b"# JD\nSQL"), "岗位.md", "text/markdown", max_bytes=100
    )

    assert result.size_bytes == 8


def test_validate_upload_rejects_filename_too_long() -> None:
    with pytest.raises(DocumentError) as raised:
        validate_upload(
            BytesIO(b"plain"), f"{'a' * 253}.md", "text/markdown", max_bytes=100
        )

    assert raised.value.code == "invalid_file_structure"


@pytest.mark.parametrize(
    ("filename", "mime_type", "content", "code"),
    [
        ("岗位.pdf", "application/pdf", b"not a pdf", "file_signature_mismatch"),
        ("岗位.md", "text/markdown", b"bad\x00text", "invalid_file_structure"),
        ("岗位.exe", "application/octet-stream", b"MZ", "unsupported_file_type"),
        ("岗位.md", "application/pdf", b"plain text", "unsupported_file_type"),
    ],
)
def test_validate_upload_rejects_type_spoofing_and_invalid_content(
    filename: str,
    mime_type: str,
    content: bytes,
    code: str,
) -> None:
    with pytest.raises(DocumentError) as raised:
        validate_upload(BytesIO(content), filename, mime_type, max_bytes=100)

    assert raised.value.code == code


def test_validate_upload_rejects_size_before_reading_unbounded_content() -> None:
    with pytest.raises(DocumentError) as raised:
        validate_upload(BytesIO(b"#" * 101), "岗位.md", "text/markdown", max_bytes=100)

    assert raised.value.code == "file_too_large"


def test_validate_upload_rejects_docx_zip_bomb_ratio() -> None:
    with pytest.raises(DocumentError) as raised:
        validate_upload(
            BytesIO(make_docx(oversized_compressed_entry=True)),
            "岗位.docx",
            "application/octet-stream",
            max_bytes=10_000_000,
        )

    assert raised.value.code == "invalid_file_structure"
