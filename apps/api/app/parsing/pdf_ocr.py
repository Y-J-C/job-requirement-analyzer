import math
from io import BytesIO

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from app.parsing.contracts import ImageOcr
from app.parsing.errors import DocumentError


def _render_page_as_png(page, *, scale: float) -> bytes:
    bitmap = page.render(scale=scale)
    try:
        image = bitmap.to_pil()
        output = BytesIO()
        image.save(output, format="PNG")
        return output.getvalue()
    finally:
        bitmap.close()


def extract_pdf_text_with_ocr(
    content: bytes,
    *,
    image_ocr: ImageOcr,
    pdf_max_pages: int,
    render_scale: float,
    max_page_pixels: int,
    max_total_pixels: int,
) -> str:
    try:
        reader = PdfReader(BytesIO(content))
        if reader.is_encrypted:
            raise DocumentError("encrypted_document", "Encrypted PDF is not supported")
        if len(reader.pages) > pdf_max_pages:
            raise DocumentError("pdf_page_limit_exceeded", "PDF exceeds the page limit")
        page_texts = [(page.extract_text() or "").strip() for page in reader.pages]
        missing_indexes = [index for index, text in enumerate(page_texts) if not text]
        if not missing_indexes:
            return "\n\n".join(page_texts)

        import pypdfium2 as pdfium

        document = pdfium.PdfDocument(content)
        total_pixels = 0
        try:
            for index in missing_indexes:
                page = document[index]
                try:
                    width, height = page.get_size()
                    pixels = math.ceil(width * render_scale) * math.ceil(height * render_scale)
                    total_pixels += pixels
                    if pixels > max_page_pixels or total_pixels > max_total_pixels:
                        raise DocumentError(
                            "pdf_render_pixel_limit_exceeded",
                            "PDF rendering exceeds the pixel limit",
                        )
                    rendered = _render_page_as_png(page, scale=render_scale)
                finally:
                    page.close()
                try:
                    page_texts[index] = image_ocr.extract_text(rendered)
                except DocumentError as error:
                    if error.code != "no_extractable_text":
                        raise
        finally:
            document.close()
        return "\n\n".join(text for text in page_texts if text)
    except DocumentError:
        raise
    except (PdfReadError, OSError, ValueError) as error:
        raise DocumentError("document_parse_failed", "PDF could not be parsed") from error
    except Exception as error:
        raise DocumentError("document_parse_failed", "PDF rendering failed") from error
