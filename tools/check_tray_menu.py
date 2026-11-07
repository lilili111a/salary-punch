# -*- coding: utf-8 -*-
"""回归：托盘右键菜单不得再被 CANCELMODE 打掉；菜单项与卡片能力对齐。"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TRAY = ROOT / "salary_punch" / "tray_win.py"
RUN = ROOT / "run.py"
UI = ROOT / "salary_punch" / "ui.py"


def fail(msg: str) -> None:
    print(f"FAIL: {msg}")
    raise SystemExit(1)


def main() -> int:
    tray = TRAY.read_text(encoding="utf-8")
    run = RUN.read_text(encoding="utf-8")
    ui = UI.read_text(encoding="utf-8")

    # 语法
    for label, text in (("tray_win.py", tray), ("run.py", run), ("ui.py", ui)):
        try:
            ast.parse(text)
        except SyntaxError as e:
            fail(f"{label} syntax {e}")

    # 禁止在弹菜单前 Post/Send CANCELMODE（历史根因）
    popup = re.search(r"def _popup_menu\([\s\S]*?(?=\n    def |\Z)", tray)
    if not popup:
        fail("_popup_menu missing")
    body = popup.group(0)
    if re.search(r"(?:Post|Send)Message[^\n]*CANCELMODE", body):
        fail("_popup_menu must not Post/Send CANCELMODE (cancels tray menu)")
    if "TrackPopupMenu" not in body:
        fail("TrackPopupMenu missing in _popup_menu")
    if "TPM_RETURNCMD" not in body and "0x0100" not in body:
        fail("TPM_RETURNCMD missing")

    # 必须延迟弹出，避免在 notify 回调里直接 TrackPopupMenu 被系统吞掉
    if "WM_TRAY_POPUP" not in tray:
        fail("WM_TRAY_POPUP missing")
    if "on_toggle_ad_camouflage" not in tray:
        fail("tray missing on_toggle_ad_camouflage")
    if "GetClassAtom" in tray:
        fail("tray must not call win32gui.GetClassAtom")
    compact = tray.replace(" ", "")
    if "PostMessage(hwnd,WM_TRAY_POPUP" not in compact:
        fail("RBUTTON should PostMessage WM_TRAY_POPUP")

    # 必备菜单文案（与卡片对齐）
    required_labels = [
        "打开配置",
        "进入/退出摸鱼",
        "切换摸鱼统计",
        "摸鱼小游戏",
        "摸鱼小应用",
        "人生建议书",
        "敲木鱼",
        "命运硬币",
        "决策骰子",
        "井字棋",
        "五子棋",
        "雷霆",
        "返回薪资视图",
        "上班打卡",
        "下班打卡",
        "退出",
        "TXT小说",
        "工作备忘录",
        "视频播放",
        "广告伪装",
    ]
    for lab in required_labels:
        if lab not in tray:
            fail(f"tray menu missing label: {lab}")

    # 命令派发覆盖
    for cmd in (1001, 1002, 1003, 1004, 1005, 1011, 1012, 1013, 1021, 1022, 1023, 1024, 1030, 1041, 1042, 1043, 1051, 1052):
        if str(cmd) not in tray:
            fail(f"tray cmd id missing: {cmd}")

    # run.py 必须把扩展回调接到 TrayApp
    for kw in (
        "on_toggle_fish",
        "on_open_game",
        "on_cycle_fish_stats",
        "on_show_salary",
        "on_punch_in",
        "on_punch_out",
        "on_toggle_pause",
        "on_toggle_topmost",
        "on_toggle_visible",
    ):
        if kw not in run:
            fail(f"run.py TrayApp wiring missing: {kw}")

    # 卡片菜单仍在
    if "DarkContextMenu" not in ui and "_dark_popup_menu" not in ui:
        fail("card dark menu missing")
    for lab in ("打开配置", "摸鱼小游戏", "摸鱼小应用", "人生建议书"):
        if lab not in ui:
            fail(f"card menu missing: {lab}")

    if "ad_camouflage" not in (ROOT / "salary_punch" / "config.py").read_text(encoding="utf-8"):
        fail("config missing ad_camouflage")
    if "_show_ad_camouflage" not in ui:
        fail("ui missing ad camouflage")
    if "NovelView" not in (ROOT / "salary_punch" / "games" / "novel.py").read_text(encoding="utf-8"):
        fail("novel view missing")
    if "MemoView" not in (ROOT / "salary_punch" / "games" / "memo.py").read_text(encoding="utf-8"):
        fail("memo view missing")
    if "VideoView" not in (ROOT / "salary_punch" / "games" / "video.py").read_text(encoding="utf-8"):
        fail("video view missing")
    if 'show_game("video")' not in ui:
        fail("ui missing video menu action")
    print("OK tray/card menu regression passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
