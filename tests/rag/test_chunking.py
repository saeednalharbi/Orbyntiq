import pytest

from orbyntiq.rag.chunking import TextChunker
from orbyntiq.rag.documents import (
    DocumentSection,
    SourceDocument,
)


def make_document(text: str) -> SourceDocument:
    return SourceDocument(
        id="document-1",
        source_path="example.txt",
        file_name="example.txt",
        media_type="text/plain",
        checksum="abc123",
        sections=(
            DocumentSection(text=text),
        ),
    )


def test_short_document_produces_one_chunk() -> None:
    chunker = TextChunker(
        chunk_size=100,
        overlap=20,
    )

    chunks = chunker.split(
        make_document("short document")
    )

    assert len(chunks) == 1
    assert chunks[0].text == "short document"
    assert chunks[0].chunk_index == 0


def test_long_document_produces_multiple_chunks() -> None:
    chunker = TextChunker(
        chunk_size=40,
        overlap=10,
    )

    text = (
        "Orbyntiq builds enterprise AI systems "
        "with retrieval and multiple agents. "
        "This text should produce several chunks."
    )

    chunks = chunker.split(make_document(text))

    assert len(chunks) > 1
    assert [
        chunk.chunk_index
        for chunk in chunks
    ] == list(range(len(chunks)))


def test_chunk_ids_are_deterministic() -> None:
    chunker = TextChunker(
        chunk_size=30,
        overlap=5,
    )
    document = make_document(
        "A deterministic document used for testing."
    )

    first = chunker.split(document)
    second = chunker.split(document)

    assert [
        chunk.id for chunk in first
    ] == [
        chunk.id for chunk in second
    ]


@pytest.mark.parametrize(
    ("chunk_size", "overlap"),
    [
        (0, 0),
        (100, -1),
        (100, 100),
        (100, 101),
    ],
)
def test_invalid_chunk_configuration(
    chunk_size,
    overlap,
) -> None:
    with pytest.raises(ValueError):
        TextChunker(
            chunk_size=chunk_size,
            overlap=overlap,
        )