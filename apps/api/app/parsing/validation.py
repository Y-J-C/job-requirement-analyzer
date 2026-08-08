import hashlib
from codecs import getincrementaldecoder
from dataclasses import dataclass
from pathlib import PurePosixPath
from tempfile import SpooledTemporaryFile
from typing import BinaryIO
from zipfile import BadZipFile, ZipFile

from app.parsing.errors import DocumentError

PDF_MEDIA_TYPE = "application/pdf"
MARKDOWN_MEDIA_TYPE = "text/markdown"
DOCX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
ALLOWED_MIME_TYPES = {
    ".pdf": {PDF_MEDIA_TYPE, "application/octet-stream"},
    ".md": {MARKDOWN_MEDIA_TYPE, "text/plain", "application/octet-stream"},
    ".markdown": {MARKDOWN_MEDIA_TYPE, "text/plain", "application/octet-stream"},
    ".docx": {DOCX_MEDIA_TYPE, "application/octet-stream"},
}


@dataclass(frozen=True)
class ValidatedUpload:
    original_filename: str
    declared_mime_type: str
    detected_media_type: str
    size_bytes: int
    sha256: str
    content: BinaryIO


def _safe_filename(filename: str) -> str:
    normalized = filename.replace("\\", "/")
    safe = PurePosixPath(normalized).name.strip()
    if not safe or safe in {".", ".."}:
        raise DocumentError("unsupported_file_type", "A valid filename is required")
    if len(safe) > 255:
        raise DocumentError("invalid_file_structure", "Filename exceeds the safe limit")
    return safe


def _validate_docx(content: BinaryIO) -> None:
    try:
        with ZipFile(content) as archive:
            entries = archive.infolist()
            names = {entry.filename for entry in entries}
            if "[Content_Types].xml" not in names or "word/document.xml" not in names:
                raise DocumentError("invalid_file_structure", "Invalid DOCX structure")
            if len(entries) > 2_000:
                raise DocumentError("invalid_file_structure", "DOCX contains too many entries")
            total_uncompressed = sum(entry.file_size for entry in entries)
            if total_uncompressed > 50 * 1024 * 1024:
                raise DocumentError("invalid_file_structure", "DOCX expands beyond the safe limit")
            for entry in entries:
                compressed_size = max(entry.compress_size, 1)
                if entry.file_size > 1_000_000 and entry.file_size > compressed_size * 100:
                    raise DocumentError(
                        "invalid_file_structure",
                        "DOCX compression ratio is unsafe",
                    )
    except (BadZipFile, OSError) as error:
        raise DocumentError("invalid_file_structure", "Invalid DOCX structure") from error
    finally:
        content.seek(0)


def _validate_markdown(content: BinaryIO) -> None:
    decoder = getincrementaldecoder("utf-8")()
    try:
        while chunk := content.read(64 * 1024):
            if b"\x00" in chunk:
                raise DocumentError("invalid_file_structure", "Markdown contains NUL bytes")
            decoder.decode(chunk)
        decoder.decode(b"", final=True)
    except UnicodeDecodeError as error:
        raise DocumentError("invalid_file_structure", "Markdown must be UTF-8") from error
    finally:
        content.seek(0)


def validate_upload(
    source: BinaryIO,
    filename: str,
    declared_mime_type: str | None,
    *,
    max_bytes: int,
) -> ValidatedUpload:
    safe_name = _safe_filename(filename)
    extension = PurePosixPath(safe_name).suffix.lower()
    mime_type = (declared_mime_type or "application/octet-stream").lower()
    if extension not in ALLOWED_MIME_TYPES or mime_type not in ALLOWED_MIME_TYPES[extension]:
        raise DocumentError("unsupported_file_type", "Unsupported file type")

    content = SpooledTemporaryFile(max_size=min(max_bytes, 1024 * 1024), mode="w+b")
    digest = hashlib.sha256()
    size = 0
    while chunk := source.read(64 * 1024):
        size += len(chunk)
        if size > max_bytes:
            content.close()
            raise DocumentError("file_too_large", "File exceeds the upload limit")
        digest.update(chunk)
        content.write(chunk)
    content.seek(0)

    try:
        prefix = content.read(8)
        content.seek(0)
        if extension == ".pdf":
            if not prefix.startswith(b"%PDF-"):
                raise DocumentError("file_signature_mismatch", "PDF signature does not match")
            detected = PDF_MEDIA_TYPE
        elif extension in {".md", ".markdown"}:
            _validate_markdown(content)
            detected = MARKDOWN_MEDIA_TYPE
        else:
            if not prefix.startswith(b"PK"):
                raise DocumentError("file_signature_mismatch", "DOCX signature does not match")
            _validate_docx(content)
            detected = DOCX_MEDIA_TYPE
    except Exception:
        content.close()
        raise

    return ValidatedUpload(
        original_filename=safe_name,
        declared_mime_type=mime_type,
        detected_media_type=detected,
        size_bytes=size,
        sha256=digest.hexdigest(),
        content=content,
    )
