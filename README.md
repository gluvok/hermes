# Hermes — Vehicle Image Streamer

Asynchronous, non-blocking multithreaded vehicle image streaming client that preloads images from `data/` into RAM, dispatches parallel batches of 2 images every 0.5 seconds to a FastAPI recognition server, and records results into a SQLite database.

## Features

- **RAM Preloading**: Loads all images into memory at startup as `InMemoryImage` objects, eliminating disk I/O during streaming.
- **Natural Order Sorting**: Sequences images by numeric index (`1.jpg`, `2.jpg`, ... `57.jpg`).
- **Parallel Multithreaded Dispatch**: Dispatches 2 images concurrently every 0.5s via a `ThreadPoolExecutor` without blocking the scheduling loop.
- **First Plate Rule**: Automatically extracts strictly the first recognized license plate (`results[0]["plate"]`), ignoring secondary plates.
- **SQLite Database Persistence**: Stores filename, recognized vehicle number, and raw image bytes (`BLOB`) in `data/vehicles.db` (WAL mode).
- **Barebones Loguru**: Clean, colorful console logging via `loguru`.
- **Cooperative Cancellation**: Clean shutdown on `SIGINT` / `SIGTERM` (`Ctrl+C`) via `threading.Event`.
- **NASA JPL Rule 4 Architecture**: Every module and function strictly ≤ 60 lines. See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for full architectural patterns and topology.

## Requirements

- Python ≥ 3.14
- [uv](https://docs.astral.sh/uv/)

## Usage

### 1. Install Dependencies
```bash
uv sync
```

### 2. Start Continuous Streaming (Default)
Streams images repeatedly from RAM to `http://127.0.0.1:8000/recognize` and saves to `data/vehicles.db`:
```bash
uv run python main.py
```

### 3. Single Pass (Stop After All Images Sent)
```bash
uv run python main.py --once
```

### 4. Custom Configuration
```bash
uv run python main.py \
  --url "http://127.0.0.1:8000/recognize" \
  --dir data \
  --db data/vehicles.db \
  --batch-size 2 \
  --interval 0.5 \
  --once
```

### 5. Inspect SQLite Database
```bash
sqlite3 data/vehicles.db "SELECT id, filename, vehicle_number, length(image_blob), created_at FROM vehicle_detections LIMIT 10;"
```

## Running Tests & Quality Gates

```bash
uv run ruff check --fix
uv run ty check
uv run pytest
```
