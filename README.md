# Hermes — Vehicle Image Streamer

Asynchronous, non-blocking vehicle image streaming client that preloads images from `data/` into RAM, dispatches parallel batches of 2 images every 0.5 seconds to an upstream recognition server using native `asyncio` and `httpx.AsyncClient`, and logs recognized license plates.

## Features

- **RAM Preloading**: Loads all images into memory at startup as `InMemoryImage` objects, eliminating disk I/O during streaming.
- **Natural Order Sorting**: Sequences images by numeric index (`1.jpg`, `2.jpg`, ... `57.jpg`).
- **Native AsyncIO & httpx.AsyncClient**: Fully asynchronous network I/O with concurrent task dispatching via `asyncio.create_task`.
- **Concurrency Throttling**: Protects system and network memory with an `asyncio.Semaphore` (default: 8).
- **First Plate Rule**: Automatically extracts strictly the first recognized license plate (`results[0]["plate"]`), ignoring secondary plates.
- **Barebones Loguru**: Clean, colorful console logging via `loguru`.
- **Instant Ctrl+C Termination**: Native `KeyboardInterrupt` handling in `main()` for instant terminal exit with zero traceback.
- **NASA JPL Rule 4 Architecture**: Every module and function strictly ≤ 60 lines. See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for full architectural patterns and topology.

## Requirements

- Python ≥ 3.14
- [uv](https://docs.astral.sh/uv/)

## Usage

### 1. Install Dependencies
```bash
uv sync
```

### 2. Start Streaming
Streams images once (single-pass) from RAM to `http://127.0.0.1:8000/recognize`:
```bash
uv run python main.py
```

## Running Tests & Quality Gates

```bash
uv run ruff check --fix
uv run ty check
uv run pytest
```
