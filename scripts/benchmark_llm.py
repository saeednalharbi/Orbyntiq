import asyncio
import statistics
import time

from orbyntiq.core.config import get_settings
from orbyntiq.llm import create_llm_provider
from orbyntiq.services import LLMService

RUNS = 5

PROMPT = """
Explain retrieval-augmented generation in approximately 80 words.
Discuss retrieval, context, and generation.
Do not use bullet points.
""".strip()


async def run_once(service: LLMService) -> dict[str, float | int]:
    start = time.perf_counter()

    response = await service.chat(PROMPT)

    wall_seconds = time.perf_counter() - start

    total_seconds = (
        response.total_duration_ns / 1_000_000_000
        if response.total_duration_ns is not None
        else 0.0
    )

    completion_tokens = response.completion_tokens or 0

    return {
        "wall_seconds": wall_seconds,
        "ollama_seconds": total_seconds,
        "prompt_tokens": response.prompt_tokens or 0,
        "completion_tokens": completion_tokens,
    }


async def main() -> None:
    settings = get_settings()

    service = LLMService(
        create_llm_provider(settings)
    )

    print(f"Model: {settings.llm_model}")
    print("Warm-up request...")

    await run_once(service)

    print("Warm-up complete.\n")

    results: list[dict[str, float | int]] = []

    for index in range(1, RUNS + 1):
        result = await run_once(service)
        results.append(result)

        print(
            f"Run {index}: "
            f"wall={result['wall_seconds']:.2f}s | "
            f"ollama={result['ollama_seconds']:.2f}s | "
            f"prompt={result['prompt_tokens']} | "
            f"completion={result['completion_tokens']}"
        )

    wall_times = [
        float(result["wall_seconds"])
        for result in results
    ]

    ollama_times = [
        float(result["ollama_seconds"])
        for result in results
    ]

    completion_tokens = [
        int(result["completion_tokens"])
        for result in results
    ]

    total_generated_tokens = sum(completion_tokens)
    total_ollama_time = sum(ollama_times)

    tokens_per_second = (
        total_generated_tokens / total_ollama_time
        if total_ollama_time > 0
        else 0.0
    )

    print("\n--- Benchmark Summary ---")
    print(f"Measured runs: {RUNS}")
    print(f"Average wall latency: {statistics.mean(wall_times):.2f}s")
    print(f"Minimum wall latency: {min(wall_times):.2f}s")
    print(f"Maximum wall latency: {max(wall_times):.2f}s")
    print(f"Average Ollama duration: {statistics.mean(ollama_times):.2f}s")
    print(f"Generated tokens: {total_generated_tokens}")
    print(f"Approx throughput: {tokens_per_second:.2f} tokens/sec")


if __name__ == "__main__":
    asyncio.run(main())