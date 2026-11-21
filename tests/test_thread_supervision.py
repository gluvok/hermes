"""test_thread_supervision.py — Long-lived threads survive faults and get restarted (#10, #9, #13)."""
from __future__ import annotations

import signal

import pytest

from src.config import config
from src.core.stability import ScaleStabilityMachine, ScaleState
from src.devices.wifi import watchdog


def test_watchdog_tick_failure_does_not_kill_loop(monkeypatch):
    ticks = []

    def tick(fails, threshold):
        ticks.append(fails)
        if len(ticks) >= 2:
            monkeypatch.setattr(watchdog, "_running", False)
        raise RuntimeError("nmcli exploded")

    monkeypatch.setattr(watchdog, "_watchdog_tick", tick)
    monkeypatch.setattr(watchdog, "_running", True)
    watchdog._watchdog_loop(interval=0)
    assert len(ticks) == 2


def test_raising_start_emergency_hotspot_is_contained(monkeypatch):
    monkeypatch.setattr(watchdog, "is_watchdog_suspended", lambda: False)
    monkeypatch.setattr(watchdog, "is_nmcli_busy", lambda: False)
    monkeypatch.setattr(watchdog, "is_network_connected", lambda: False)
    monkeypatch.setattr(watchdog, "is_hotspot_active", lambda: False)

    def boom():
        raise RuntimeError("hotspot failed")

    monkeypatch.setattr(watchdog.hotspot, "start_emergency_hotspot", boom)
    monkeypatch.setattr(watchdog, "notify_network_status", lambda online: None)
    calls = []
    real_tick = watchdog._watchdog_tick

    def counting_tick(fails, threshold):
        calls.append(fails)
        if len(calls) >= 2:
            monkeypatch.setattr(watchdog, "_running", False)
        return real_tick(fails, threshold)

    monkeypatch.setattr(watchdog, "_watchdog_tick", counting_tick)
    monkeypatch.setattr(watchdog, "_running", True)
    watchdog._watchdog_loop(interval=0, threshold=1)
    assert len(calls) == 2


def test_led_fault_still_reaches_state_machine(monkeypatch):
    seen = []
    monkeypatch.setattr(
        "src.devices.led.led_controller.set_network_status",
        lambda online: (_ for _ in ()).throw(OSError("gpio gone")),
    )
    monkeypatch.setattr("src.core.stability.scale_state_machine.set_network_status", seen.append)
    watchdog.notify_network_status(False)
    assert seen == [False]


def test_start_session_failure_leaves_state_idle(monkeypatch):
    machine = ScaleStabilityMachine()
    monkeypatch.setattr("src.core.stability.session_manager.check_session_progress", lambda: None)

    def boom():
        raise RuntimeError("start_session failed")

    monkeypatch.setattr("src.core.stability.session_manager.start_session", boom)
    with pytest.raises(RuntimeError):
        machine.process_new_weight(config.weight_threshold + 1000.0)
    assert machine.state == ScaleState.SCALE_IDLE


class _FakeReader:
    def __init__(self, alive: bool):
        self.alive = alive
        self.starts = 0

    def is_alive(self) -> bool:
        return self.alive

    def start(self) -> None:
        self.starts += 1


def _supervise(monkeypatch, reader_alive: bool, watchdog_running: bool):
    saved = {sig: signal.getsignal(sig) for sig in (signal.SIGINT, signal.SIGTERM)}
    try:
        import main  # module-level code installs SIGINT/SIGTERM handlers; undone below
    finally:
        for sig, handler in saved.items():
            signal.signal(sig, handler)

    reader = _FakeReader(reader_alive)
    restarts = []
    monkeypatch.setattr(main, "get_uart_reader", lambda: reader)
    monkeypatch.setattr(main, "is_watchdog_running", lambda: watchdog_running)
    monkeypatch.setattr(main, "start_wifi_watchdog", lambda interval=1.0: restarts.append(interval) or True)
    main._supervise_threads()
    return reader, restarts


def test_dead_reader_is_restarted(monkeypatch):
    reader, restarts = _supervise(monkeypatch, reader_alive=False, watchdog_running=True)
    assert reader.starts == 1
    assert restarts == []


def test_dead_watchdog_is_restarted(monkeypatch):
    reader, restarts = _supervise(monkeypatch, reader_alive=True, watchdog_running=False)
    assert reader.starts == 0
    assert restarts == [1.0]
