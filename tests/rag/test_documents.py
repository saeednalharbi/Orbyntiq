import importlib

import pytest

from orbyntiq.rag.documents import (
    DocumentLoadError,
    load_document,
)

documents_module = importlib.import_module(
    "orbyntiq.rag.documents"
)


def test_load_text_document(tmp_path) -> None:
    path = tmp_path / "notes.txt"
    path.write_text(
        "Orbyntiq\n\nEnterprise RAG",
        encoding="utf-8",
    )

    document = load_document(path)

    assert document.file_name == "notes.txt"
    assert document.media_type == "text/plain"
    assert document.content == (
        "Orbyntiq\n\nEnterprise RAG"
    )
    assert len(document.checksum) == 64
    assert len(document.sections) == 1


def test_load_markdown_document(tmp_path) -> None:
    path = tmp_path / "notes.md"
    path.write_text(
        "# Orbyntiq\nRAG platform",
        encoding="utf-8",
    )

    document = load_document(path)

    assert document.media_type == "text/markdown"
    assert "# Orbyntiq" in document.content


def test_load_pdf_preserves_page_numbers(
    tmp_path,
    monkeypatch,
) -> None:
    path = tmp_path / "sample.pdf"
    path.write_bytes(b"%PDF-test")

    class FakePage:
        def __init__(self, text: str) -> None:
            self._text = text

        def extract_text(self) -> str:
            return self._text

    class FakeReader:
        def __init__(self, _path) -> None:
            self.pages = [
                FakePage("Page one"),
                FakePage("Page two"),
            ]

    monkeypatch.setattr(
        documents_module,
        "PdfReader",
        FakeReader,
    )

    document = load_document(path)

    assert len(document.sections) == 2
    assert document.sections[0].page_number == 1
    assert document.sections[1].page_number == 2


def test_rejects_unsupported_document(tmp_path) -> None:
    path = tmp_path / "file.docx"
    path.write_text("hello", encoding="utf-8")

    with pytest.raises(
        DocumentLoadError,
        match="Unsupported document type",
    ):
        load_document(path)


def test_rejects_empty_document(tmp_path) -> None:
    path = tmp_path / "empty.txt"
    path.write_text("", encoding="utf-8")

    with pytest.raises(
        DocumentLoadError,
        match="no extractable text",
    ):
        load_document(path)