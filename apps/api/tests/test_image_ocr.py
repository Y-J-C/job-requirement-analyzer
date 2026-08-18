from dataclasses import dataclass
from io import BytesIO

import pytest
from PIL import Image

from app.parsing.errors import DocumentError
from app.parsing.ocr import RapidOcrImageOcr


@dataclass
class FakeRapidOcrOutput:
    txts: tuple[str, ...] | None


class FakeRapidOcrEngine:
    def __init__(self, output: FakeRapidOcrOutput) -> None:
        self.output = output
        self.inputs: list[bytes] = []

    def __call__(self, content: bytes) -> FakeRapidOcrOutput:
        self.inputs.append(content)
        return self.output


class FailingRapidOcrEngine:
    def __call__(self, content: bytes) -> FakeRapidOcrOutput:
        del content
        raise RuntimeError("third-party internal path")


def image_bytes(*, size: tuple[int, int] = (30, 10), orientation: int | None = None) -> bytes:
    output = BytesIO()
    exif = Image.Exif()
    if orientation is not None:
        exif[274] = orientation
    Image.new("RGB", size, "white").save(output, format="JPEG", exif=exif)
    return output.getvalue()


def test_rapid_ocr_adapter_returns_lines_in_engine_order() -> None:
    engine = FakeRapidOcrEngine(
        FakeRapidOcrOutput(("示例科技", "Data Analyst", "2028 届"))
    )
    ocr = RapidOcrImageOcr(engine=engine)

    content = image_bytes()
    text = ocr.extract_text(content)

    assert text == "示例科技\nData Analyst\n2028 届"
    assert len(engine.inputs) == 1
    with Image.open(BytesIO(engine.inputs[0])) as normalized:
        assert normalized.size == (30, 10)


@pytest.mark.parametrize("lines", [None, (), (" ", "\t")])
def test_rapid_ocr_adapter_rejects_an_image_without_text(
    lines: tuple[str, ...] | None,
) -> None:
    ocr = RapidOcrImageOcr(engine=FakeRapidOcrEngine(FakeRapidOcrOutput(lines)))

    with pytest.raises(DocumentError) as error:
        ocr.extract_text(image_bytes())

    assert error.value.code == "no_extractable_text"


def test_rapid_ocr_adapter_hides_engine_failures() -> None:
    ocr = RapidOcrImageOcr(engine=FailingRapidOcrEngine())

    with pytest.raises(DocumentError) as error:
        ocr.extract_text(image_bytes())

    assert error.value.code == "image_ocr_failed"
    assert "third-party internal path" not in str(error.value)


def test_rapid_ocr_adapter_applies_exif_orientation_before_recognition() -> None:
    engine = FakeRapidOcrEngine(FakeRapidOcrOutput(("岗位要求",)))
    ocr = RapidOcrImageOcr(engine=engine)

    ocr.extract_text(image_bytes(size=(30, 10), orientation=6))

    with Image.open(BytesIO(engine.inputs[0])) as normalized:
        assert normalized.size == (10, 30)
