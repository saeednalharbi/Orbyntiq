from orbyntiq.core.config import Settings

RAG_ENV_NAMES = (
    "ORBYNTIQ_RAG_RETRIEVAL_LIMIT",
    "ORBYNTIQ_RAG_CHUNK_CHARACTER_LIMIT",
    "ORBYNTIQ_RAG_MAX_OUTPUT_TOKENS",
)


def test_rag_runtime_defaults(
    monkeypatch,
) -> None:
    for name in RAG_ENV_NAMES:
        monkeypatch.delenv(
            name,
            raising=False,
        )

    settings = Settings(_env_file=None)

    assert settings.rag_retrieval_limit == 3

    assert settings.rag_chunk_character_limit == 700

    assert settings.rag_max_output_tokens == 160


def test_rag_runtime_env_overrides(
    monkeypatch,
) -> None:
    monkeypatch.setenv(
        "ORBYNTIQ_RAG_RETRIEVAL_LIMIT",
        "5",
    )

    monkeypatch.setenv(
        "ORBYNTIQ_RAG_CHUNK_CHARACTER_LIMIT",
        "1400",
    )

    monkeypatch.setenv(
        "ORBYNTIQ_RAG_MAX_OUTPUT_TOKENS",
        "320",
    )

    settings = Settings(_env_file=None)

    assert settings.rag_retrieval_limit == 5

    assert settings.rag_chunk_character_limit == 1400

    assert settings.rag_max_output_tokens == 320
