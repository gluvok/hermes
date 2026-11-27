"""test_freethreaded_runtime.py — Hermes runs on free-threaded CPython 3.14t with the GIL off."""
from __future__ import annotations

import signal
import subprocess
import sys
import sysconfig

# Fresh interpreter so the first module that flips the GIL back on is the one named.
# -W error turns CPython's "GIL has been enabled" RuntimeWarning into an import failure.
_IMPORT_ALL = """
import importlib, pkgutil, sys
import src
from src.services.image_compressor import compress_image_bytes
for m in pkgutil.walk_packages(src.__path__, "src."):
    importlib.import_module(m.name)
    assert not sys._is_gil_enabled(), m.name
compress_image_bytes(b"\\xff\\xd8not-a-jpeg")  # loads Pillow's lazy JPEG plugin path
import main  # noqa: F401
assert not sys._is_gil_enabled(), "main"
"""


def test_interpreter_is_free_threaded_build():
    assert sysconfig.get_config_var("Py_GIL_DISABLED") == 1, (
        f"{sys.version} has a GIL; .python-version pins 3.14t, re-run `uv sync`"
    )


def test_importing_all_of_src_keeps_gil_disabled():
    res = subprocess.run(
        [sys.executable, "-W", "error::RuntimeWarning", "-c", _IMPORT_ALL],
        capture_output=True, text=True, timeout=60, check=False,
        env={"SUPERADMIN_PASS": "x", "HERMES_HOTSPOT_PASS": "x" * 8, "PATH": ""},
    )
    assert res.returncode == 0, res.stderr[-2000:]


def test_startup_warns_when_gil_is_enabled(monkeypatch):
    saved = {sig: signal.getsignal(sig) for sig in (signal.SIGINT, signal.SIGTERM)}
    try:
        import main  # module-level code installs SIGINT/SIGTERM handlers and resets logging; undone below
    finally:
        for sig, handler in saved.items():
            signal.signal(sig, handler)

    warnings: list[str] = []
    monkeypatch.setattr(main.logger, "warning", warnings.append)
    monkeypatch.setattr(sys, "_is_gil_enabled", lambda: False)
    main._warn_if_gil_enabled()
    assert warnings == []
    monkeypatch.setattr(sys, "_is_gil_enabled", lambda: True)
    main._warn_if_gil_enabled()
    assert len(warnings) == 1 and "GIL is enabled" in warnings[0]
