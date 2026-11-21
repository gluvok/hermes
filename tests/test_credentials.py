import os
import subprocess

import pytest

LEAKED = "/private/tmp/claude-501/-Users-kaalu--claude-spares-spare-pAflsh/c1ba9ee0-9af4-4634-8b9c-479c7406fca9/scratchpad/leaked.txt"


@pytest.mark.skipif(not os.path.exists(LEAKED), reason="leaked-value list only exists on the maintainer machine")
def test_no_credential_literal_outside_tests():
    out = subprocess.run(
        ["git", "grep", "-l", "-F", "-f", LEAKED, "--", ".", ":!tests"],
        check=False, capture_output=True, text=True,
    )
    assert out.stdout == "", out.stdout


def test_verify_credentials_rejects_everything_when_password_unset(monkeypatch):
    from src.web import auth
    monkeypatch.setattr(auth, "SUPERADMIN_PASS", "")
    assert auth.verify_credentials("superadmin", "") is False


def test_require_runtime_secrets_exits_when_unset(monkeypatch):
    from src.web import auth
    monkeypatch.delenv("SUPERADMIN_PASS", raising=False)
    with pytest.raises(SystemExit):
        auth.require_runtime_secrets()


def test_hotspot_refuses_short_or_missing_psk(monkeypatch):
    from src.devices.wifi import hotspot, runner
    monkeypatch.setitem(runner.SIMULATION_STATE, "enabled", False)
    monkeypatch.setattr(runner, "is_nmcli_available", lambda: True)
    calls = []
    monkeypatch.setattr(runner, "run_nmcli", lambda *a, **k: calls.append(a) or (0, ""))
    assert hotspot.start_hotspot(password="") is False
    assert calls == []


def test_deploy_env_text_requires_and_escapes_secrets(monkeypatch):
    from scripts import deploy
    monkeypatch.setenv("SUPERADMIN_PASS", 'a"b\\c')
    monkeypatch.setenv("HERMES_HOTSPOT_PASS", "test-hotspot-pass")
    assert deploy.secrets_env_text() == 'SUPERADMIN_PASS="a\\"b\\\\c"\nHERMES_HOTSPOT_PASS="test-hotspot-pass"\n'
    monkeypatch.delenv("HERMES_HOTSPOT_PASS")
    with pytest.raises(SystemExit):
        deploy.secrets_env_text()
