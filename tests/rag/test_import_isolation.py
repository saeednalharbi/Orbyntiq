import subprocess
import sys


def test_rag_imports_in_fresh_python_process() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "from orbyntiq.rag.chunking "
                "import TextChunker; "
                "from orbyntiq.rag.service "
                "import RAGService; "
                "print(TextChunker.__name__, "
                "RAGService.__name__)"
            ),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, (
        result.stdout
        + result.stderr
    )

    assert (
        "TextChunker RAGService"
        in result.stdout
    )
