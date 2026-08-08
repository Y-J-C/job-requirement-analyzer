from typing import Protocol


class DocumentParser(Protocol):
    media_type: str

    def parse(self, content: bytes, *, pdf_max_pages: int) -> str: ...
