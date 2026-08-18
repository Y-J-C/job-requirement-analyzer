from io import BytesIO
from typing import Protocol

from PIL import Image, ImageOps, UnidentifiedImageError

from app.parsing.errors import DocumentError


class RapidOcrOutput(Protocol):
    txts: tuple[str, ...] | None


class RapidOcrEngine(Protocol):
    def __call__(self, content: bytes) -> RapidOcrOutput: ...


class RapidOcrImageOcr:
    def __init__(self, engine: RapidOcrEngine | None = None) -> None:
        if engine is None:
            from rapidocr import RapidOCR

            engine = RapidOCR()
        self._engine = engine

    def extract_text(self, content: bytes) -> str:
        try:
            with Image.open(BytesIO(content)) as image:
                normalized = ImageOps.exif_transpose(image).convert("RGB")
                buffer = BytesIO()
                normalized.save(buffer, format="PNG")
                normalized_content = buffer.getvalue()
        except (Image.DecompressionBombError, OSError, UnidentifiedImageError) as error:
            raise DocumentError("invalid_file_structure", "Image is invalid or damaged") from error
        try:
            result = self._engine(normalized_content)
        except Exception as error:
            raise DocumentError("image_ocr_failed", "Image OCR failed") from error
        lines = [line.strip() for line in (result.txts or ()) if line.strip()]
        if not lines:
            raise DocumentError("no_extractable_text", "No text was found in the image")
        return "\n".join(lines)
