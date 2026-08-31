from dataclasses import dataclass
from uuid import NAMESPACE_URL, uuid5

from orbyntiq.rag.documents import SourceDocument


@dataclass(frozen=True, slots=True)
class DocumentChunk:
    id: str
    document_id: str
    chunk_index: int
    text: str
    source_path: str
    file_name: str
    checksum: str
    page_number: int | None = None


class TextChunker:
    def __init__(
        self,
        *,
        chunk_size: int = 1200,
        overlap: int = 200,
    ) -> None:
        if chunk_size < 1:
            raise ValueError(
                "chunk_size must be greater than zero"
            )

        if overlap < 0:
            raise ValueError(
                "overlap cannot be negative"
            )

        if overlap >= chunk_size:
            raise ValueError(
                "overlap must be smaller than chunk_size"
            )

        self.chunk_size = chunk_size
        self.overlap = overlap

    def _split_text(self, text: str) -> list[str]:
        chunks: list[str] = []
        start = 0

        while start < len(text):
            end = min(
                start + self.chunk_size,
                len(text),
            )

            if end < len(text):
                search_start = start + (
                    self.chunk_size // 2
                )

                boundary = text.rfind(
                    " ",
                    search_start,
                    end,
                )

                if boundary > start:
                    end = boundary

            chunk = text[start:end].strip()

            if chunk:
                chunks.append(chunk)

            if end >= len(text):
                break

            next_start = end - self.overlap

            if next_start <= start:
                next_start = end

            start = next_start

        return chunks

    def split(
        self,
        document: SourceDocument,
    ) -> list[DocumentChunk]:
        chunks: list[DocumentChunk] = []
        chunk_index = 0

        for section in document.sections:
            section_chunks = self._split_text(
                section.text
            )

            for text in section_chunks:
                chunk_id = str(
                    uuid5(
                        NAMESPACE_URL,
                        (
                            f"{document.id}:"
                            f"{document.checksum}:"
                            f"{chunk_index}"
                        ),
                    )
                )

                chunks.append(
                    DocumentChunk(
                        id=chunk_id,
                        document_id=document.id,
                        chunk_index=chunk_index,
                        text=text,
                        source_path=document.source_path,
                        file_name=document.file_name,
                        checksum=document.checksum,
                        page_number=section.page_number,
                    )
                )

                chunk_index += 1

        return chunks