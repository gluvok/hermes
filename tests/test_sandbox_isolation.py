"""Verify tests cannot invoke real subprocess sudo or unmocked serial ports."""
import subprocess
import pytest

def test_unmocked_sudo_is_blocked():
    with pytest.raises(RuntimeError, match="Direct system execution blocked in test suite"):
        from tests.conftest import assert_sandbox_active
        assert_sandbox_active()
        subprocess.run(["sudo", "whoami"], check=True)
