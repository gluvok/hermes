# Hermes Architecture Reference

Hermes is an asynchronous, paced vehicle image streaming client that preloads image assets into memory, streams them in parallel batches to an upstream recognition server using native `asyncio` and `httpx.AsyncClient`, and logs vehicle plate detections.

## System Topology & Dataflow

```mermaid
flowchart TD
    MAIN["Main Async Entrypoint (main.py)\n[StreamerConfig]"] --> LOAD["Image Loader (src/image_loader.py)"]
    MAIN --> STR["Async Streamer Engine (src/streamer.py)"]
    
    LOAD -->|Preload RAM| RAM[("InMemoryImage Buffer")]
    STR -->|Slice Batches| RAM
    STR -->|Semaphore Guard (max 8)| CLT["Async HTTP Client (src/client.py)"]
    CLT -->|POST /recognize (httpx.AsyncClient)| API["FastAPI Recognition Server"]
    API -->|JSON Result| CLT
    CLT -->|Log Detection| LOG["Console / Loguru"]
```

## NASA JPL Rule 4 Adherence (Single Sheet of Paper)

Every file and function is designed to fit on a single printed sheet of standard paper (strictly ≤ 60 lines of code) with single cohesive concerns:

| Component | Responsibility | Lines | Hard Limit |
|:---|:---|:---:|:---:|
| `main.py` | Process entrypoint and KeyboardInterrupt handling | ~23 | ≤ 60 |
| `src/config.py` | Immutable configuration dataclass | ~15 | ≤ 60 |
| `src/image_loader.py` | RAM preloading & natural order sorting | ~42 | ≤ 60 |
| `src/client.py` | Async HTTP posting & plate extraction | ~39 | ≤ 60 |
| `src/streamer.py` | Paced batch dispatch & async loop | ~41 | ≤ 60 |

## Concurrency & Resource Management

1. **Preloading in RAM**: All images are loaded into RAM once as immutable `InMemoryImage` dataclasses, eliminating disk I/O bottlenecks during streaming.
2. **Native AsyncIO Dispatch**: Dispatches image recognition requests concurrently via `asyncio.create_task` and `httpx.AsyncClient`, decoupling network latency from scheduling intervals.
3. **Semaphore Throttling**: An `asyncio.Semaphore` guards active requests against upstream latency spikes, preventing excessive memory consumption from 2K (2.5MB) images.
4. **Instant Ctrl+C Termination**: Clean process exit on `KeyboardInterrupt` caught in `main()`, halting immediately without shutdown delays or tracebacks.

## Python 3.14 Standards

- **PEP 649 (Deferred Evaluation of Annotations)**: All type hints evaluate lazily; string-quoted forward references and `from __future__ import annotations` are forbidden.
- **PEP 695 (Type Parameter Syntax)**: Type aliases use the native `type` statement (e.g., `type RecognitionPayload = dict[str, Any]`, `type VehicleNumber = str | None`).
- **Modern Collections & Unions**: Native syntax exclusively (`list`, `dict`, `tuple`, `|` union operators).
