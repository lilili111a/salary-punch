# -*- coding: utf-8 -*-
"""开机自启：HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run\\SalaryPunch。"""

from __future__ import annotations

import sys
from pathlib import Path

RUN_NAME = "SalaryPunch"
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def resolve_launch_target() -> str:
    if getattr(sys, "frozen", False):
        exe = Path(sys.executable).resolve()
        return f'"{exe}"'
    root = Path(__file__).resolve().parent.parent
    dist_exe = root / "dist" / "SalaryPunch" / "SalaryPunch.exe"
    if dist_exe.exists():
        return f'"{dist_exe}"'
    start_bat = root / "start.bat"
    if start_bat.exists():
        return f'"{start_bat}"'
    run_py = root / "run.py"
    return f'"{sys.executable}" "{run_py}"'


def is_enabled() -> bool:
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            winreg.QueryValueEx(key, RUN_NAME)
            return True
    except OSError:
        return False


def current_value() -> str | None:
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            val, _ = winreg.QueryValueEx(key, RUN_NAME)
            return str(val)
    except OSError:
        return None


def enable(command: str | None = None) -> str:
    cmd = command or resolve_launch_target()
    import winreg

    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
        winreg.SetValueEx(key, RUN_NAME, 0, winreg.REG_SZ, cmd)
    return cmd


def disable() -> None:
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
            winreg.DeleteValue(key, RUN_NAME)
    except OSError:
        pass


def sync(enabled: bool) -> str | None:
    if enabled:
        return enable()
    disable()
    return None
