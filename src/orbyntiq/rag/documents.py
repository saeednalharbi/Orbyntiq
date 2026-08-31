from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from pypdf import PdfReader
from pypdf.errors import PdfReadError

SUPPORTED_DOCUMENT_TYPES = {
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".pdf": "application/pdf",
}


class DocumentLoadError(RuntimeError):
    """Raised when a document cannot be loaded."""


@dataclass(frozen=True, slots=True)
class DocumentSection:
    text: str
    page_number: int | None = None


@dataclass(frozen=True, slots=True)
class SourceDocument:
    id: str
    source_path: str
    file_name: str
    media_type: str
    checksum: str
    sections: tuple[DocumentSection, ...]

    @property
    def content(self) -> str:
        return "\n\n".join(
            section.text for section in self.sections
        )


def _normalize_text(text: str) -> str:
    lines = [
        line.rstrip()
        for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    ]

    return "\n".join(lines).strip()


def _document_id(path: Path) -> str:
    source_key = str(path.resolve()).casefold()

    return str(
        uuid5(
            NAMESPACE_URL,
            f"orbyntiq-document:{source_key}",
        )
    )


def load_document(path: str | Path) -> SourceDocument:
    source = Path(path)

    if not source.exists():
        raise DocumentLoadError(
            f"Document does not exist: {source}"
        )

    if not source.is_file():
        raise DocumentLoadError(
            f"Document path is not a file: {source}"
        )

    suffix = source.suffix.lower()

    if suffix not in SUPPORTED_DOCUMENT_TYPES:
        raise DocumentLoadError(
            f"Unsupported document type: {suffix or '<none>'}"
        )

    try:
        raw_bytes = source.read_bytes()
    except OSError as exc:
        raise DocumentLoadError(
            f"Failed to read document: {source}"
        ) from exc

    checksum = sha256(raw_bytes).hexdigest()
    sections: list[DocumentSection] = []

    if suffix in {".txt", ".md"}:
        try:
            text = raw_bytes.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise DocumentLoadError(
                "Text documents must use UTF-8 encoding"
            ) from exc

        normalized = _normalize_text(text)

        if normalized:
            sections.append(
                DocumentSection(text=normalized)
            )

    elif suffix == ".pdf":
        try:
            reader = PdfReader(source)

            for page_number, page in enumerate(
                reader.pages,
                start=1,
            ):
                text = _normalize_text(
                    page.extract_text() or ""
                )

                if text:
                    sections.append(
                        DocumentSection(
                            text=text,
                            page_number=page_number,
                        )
                    )

        except (PdfReadError, OSError) as exc:
            raise DocumentLoadError(
                f"Failed to parse PDF: {source}"
            ) from exc

    if not sections:
        raise DocumentLoadError(
            "Document contains no extractable text"
        )

    return SourceDocument(
        id=_document_id(source),
        source_path=str(source.resolve()),
        file_name=source.name,
        media_type=SUPPORTED_DOCUMENT_TYPES[suffix],
        checksum=checksum,
        sections=tuple(sections),
    )