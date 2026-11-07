# -*- coding: utf-8 -*-
"""Windows 托盘图标。"""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Callable

try:
    import win32api  # type: ignore
    import win32con  # type: ignore
    import win32gui  # type: ignore
except ImportError:  # pragma: no cover
    win32api = None  # type: ignore


# 自定义消息：在通知回调外再弹菜单，避免嵌套模态失败
WM_TRAY_NOTIFY = win32con.WM_USER + 20 if win32api else 0x0414
WM_TRAY_POPUP = win32con.WM_USER + 21 if win32api else 0x0415


class TrayApp:
    """系统托盘。右键菜单与卡片功能对齐（配置/摸鱼/游戏/应用等）。"""

    def __init__(
        self,
        icon_path: Path,
        on_show: Callable[[], None],
        on_config: Callable[[], None],
        on_quit: Callable[[], None],
        on_toggle_fish: Callable[[], None] | None = None,
        on_open_game: Callable[[str], None] | None = None,
        on_cycle_fish_stats: Callable[[], None] | None = None,
        on_show_salary: Callable[[], None] | None = None,
        on_punch_in: Callable[[], None] | None = None,
        on_punch_out: Callable[[], None] | None = None,
        on_toggle_pause: Callable[[], None] | None = None,
        on_toggle_topmost: Callable[[], None] | None = None,
        on_toggle_visible: Callable[[], None] | None = None,
        on_toggle_ad_camouflage: Callable[[], None] | None = None,
        tooltip: str = "薪资打卡器",
    ):
        if win32api is None:
            raise RuntimeError("pywin32 not available")
        self.icon_path = Path(icon_path)
        self.on_show = on_show
        self.on_config = on_config
        self.on_quit = on_quit
        self.on_toggle_fish = on_toggle_fish
        self.on_open_game = on_open_game
        self.on_cycle_fish_stats = on_cycle_fish_stats
        self.on_show_salary = on_show_salary
        self.on_punch_in = on_punch_in
        self.on_punch_out = on_punch_out
        self.on_toggle_pause = on_toggle_pause
        self.on_toggle_topmost = on_toggle_topmost
        self.on_toggle_visible = on_toggle_visible
        self.on_toggle_ad_camouflage = on_toggle_ad_camouflage
        self.tooltip = tooltip
        self._thread: threading.Thread | None = None
        self._hwnd = None
        self._nid = None

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, name="salary-tray", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        hwnd = self._hwnd
        if hwnd:
            try:
                win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
            except Exception:
                pass

    def _run(self) -> None:
        wc = win32gui.WNDCLASS()
        hinst = win32api.GetModuleHandle(None)
        wc.hInstance = hinst
        wc.lpszClassName = "SalaryPunchTray"
        wc.lpfnWndProc = self._wnd_proc
        try:
            class_atom = win32gui.RegisterClass(wc)
        except Exception:
            class_atom = "SalaryPunchTray"

        hwnd = win32gui.CreateWindow(class_atom, "SalaryPunchTray", 0, 0, 0, 0, 0, 0, 0, hinst, None)
        self._hwnd = hwnd
        self._add_icon(hwnd)
        win32gui.PumpMessages()

    def _wnd_proc(self, hwnd, msg, wparam, lparam):
        if msg == win32con.WM_DESTROY:
            try:
                if self._nid:
                    win32gui.Shell_NotifyIcon(win32gui.NIM_DELETE, self._nid)
            except Exception:
                pass
            win32gui.PostQuitMessage(0)
            return 0
        if msg == WM_TRAY_POPUP:
            # 在通知回调外弹菜单，避免被系统立刻取消
            self._popup_menu(hwnd)
            return 0
        if msg == win32con.WM_COMMAND:
            # 兼容非 RETURNCMD 路径
            self._dispatch_tray_cmd(int(win32api.LOWORD(wparam)))
            return 0
        if msg == WM_TRAY_NOTIFY:
            if lparam == win32con.WM_LBUTTONDBLCLK:
                if self.on_show:
                    self.on_show()
            elif lparam in (win32con.WM_RBUTTONUP, win32con.WM_CONTEXTMENU):
                # 切勿在此处直接 TrackPopupMenu 前 Post CANCELMODE，
                # 否则模态循环会吃到 CANCELMODE，菜单一闪就没。
                win32gui.PostMessage(hwnd, WM_TRAY_POPUP, 0, 0)
            elif lparam == win32con.WM_LBUTTONUP:
                # 单击显示窗口（可选体验）
                pass
            return 0
        return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)

    def _dispatch_tray_cmd(self, cmd: int) -> None:
        """托盘菜单项选中后派发。"""
        if not cmd:
            return
        mapping: dict[int, Callable[[], None] | None] = {
            1001: self.on_show,
            1002: self.on_config,
            1003: self.on_quit,
            1004: self.on_toggle_fish,
            1005: self.on_cycle_fish_stats,
            1011: (lambda: self.on_open_game("ttt")) if self.on_open_game else None,
            1012: (lambda: self.on_open_game("gomoku")) if self.on_open_game else None,
            1013: (lambda: self.on_open_game("shooter")) if self.on_open_game else None,
            1021: (lambda: self.on_open_game("advice")) if self.on_open_game else None,
            1022: (lambda: self.on_open_game("muyu")) if self.on_open_game else None,
            1023: (lambda: self.on_open_game("coin")) if self.on_open_game else None,
            1024: (lambda: self.on_open_game("dice")) if self.on_open_game else None,
            1030: self.on_show_salary,
            1041: self.on_punch_in,
            1042: self.on_punch_out,
            1043: self.on_toggle_pause,
            1051: self.on_toggle_topmost,
            1052: self.on_toggle_visible,
            1061: (lambda: self.on_open_game("novel")) if self.on_open_game else None,
            1062: (lambda: self.on_open_game("memo")) if self.on_open_game else None,
            1064: (lambda: self.on_open_game("video")) if self.on_open_game else None,
            1065: (lambda: self.on_open_game("market")) if self.on_open_game else None,
            1063: self.on_toggle_ad_camouflage,
        }
        fn = mapping.get(int(cmd))
        if fn:
            try:
                fn()
            except Exception:
                pass

    def _append_games_menu(self, parent) -> None:
        games = win32gui.CreatePopupMenu()
        win32gui.AppendMenu(games, win32con.MF_STRING, 1011, "井字棋")
        win32gui.AppendMenu(games, win32con.MF_STRING, 1012, "五子棋")
        win32gui.AppendMenu(games, win32con.MF_STRING, 1013, "Q版雷霆战机")
        win32gui.AppendMenu(parent, win32con.MF_POPUP, games, "摸鱼小游戏")

    def _append_apps_menu(self, parent) -> None:
        apps = win32gui.CreatePopupMenu()
        win32gui.AppendMenu(apps, win32con.MF_STRING, 1021, "人生建议书")
        win32gui.AppendMenu(apps, win32con.MF_STRING, 1022, "敲木鱼")
        win32gui.AppendMenu(apps, win32con.MF_STRING, 1023, "命运硬币（做/不做）")
        win32gui.AppendMenu(apps, win32con.MF_STRING, 1024, "决策骰子")
        win32gui.AppendMenu(parent, win32con.MF_POPUP, apps, "摸鱼小应用")

    def _popup_menu(self, hwnd) -> None:
        """弹出完整托盘菜单。禁止在 TrackPopupMenu 前异步 Post CANCELMODE。"""
        menu = win32gui.CreatePopupMenu()
        win32gui.AppendMenu(menu, win32con.MF_STRING, 1001, "显示窗口")
        win32gui.AppendMenu(menu, win32con.MF_STRING, 1002, "打开配置")
        win32gui.AppendMenu(menu, win32con.MF_SEPARATOR, 0, "")
        win32gui.AppendMenu(menu, win32con.MF_STRING, 1004, "进入/退出摸鱼")
        win32gui.AppendMenu(menu, win32con.MF_STRING, 1005, "切换摸鱼统计（今日/本月/一共）")
        win32gui.AppendMenu(menu, win32con.MF_SEPARATOR, 0, "")
        self._append_games_menu(menu)
        self._append_apps_menu(menu)
        win32gui.AppendMenu(menu, win32con.MF_STRING, 1030, "返回薪资视图")
        win32gui.AppendMenu(menu, win32con.MF_SEPARATOR, 0, "")
        win32gui.AppendMenu(menu, win32con.MF_STRING, 1041, "上班打卡")
        win32gui.AppendMenu(menu, win32con.MF_STRING, 1042, "下班打卡")
        win32gui.AppendMenu(menu, win32con.MF_STRING, 1043, "今日暂停/恢复计时")
        win32gui.AppendMenu(menu, win32con.MF_SEPARATOR, 0, "")
        win32gui.AppendMenu(menu, win32con.MF_STRING, 1051, "切换置顶")
        win32gui.AppendMenu(menu, win32con.MF_STRING, 1052, "隐藏/显示窗口")
        win32gui.AppendMenu(menu, win32con.MF_SEPARATOR, 0, "")
        office = win32gui.CreatePopupMenu()
        win32gui.AppendMenu(office, win32con.MF_STRING, 1061, "TXT小说阅读")
        win32gui.AppendMenu(office, win32con.MF_STRING, 1062, "工作备忘录")
        win32gui.AppendMenu(office, win32con.MF_STRING, 1064, "视频播放")
        win32gui.AppendMenu(office, win32con.MF_STRING, 1065, "股票基金")
        win32gui.AppendMenu(menu, win32con.MF_POPUP, office, "办公工具")
        win32gui.AppendMenu(menu, win32con.MF_STRING, 1063, "开关广告伪装")
        win32gui.AppendMenu(menu, win32con.MF_SEPARATOR, 0, "")
        win32gui.AppendMenu(menu, win32con.MF_STRING, 1003, "退出")

        pos = win32gui.GetCursorPos()
        try:
            win32gui.SetForegroundWindow(hwnd)
        except Exception:
            pass
        flags = (
            win32con.TPM_LEFTALIGN
            | win32con.TPM_RIGHTBUTTON
            | getattr(win32con, "TPM_RETURNCMD", 0x0100)
        )
        cmd = win32gui.TrackPopupMenu(menu, flags, pos[0], pos[1], 0, hwnd, None)
        try:
            win32gui.DestroyMenu(menu)
        except Exception:
            pass
        # 让托盘菜单正确收起（Windows 经典做法）
        win32gui.PostMessage(hwnd, win32con.WM_NULL, 0, 0)
        if cmd:
            self._dispatch_tray_cmd(int(cmd))

    def _add_icon(self, hwnd) -> None:
        hicon = 0
        if self.icon_path.exists():
            icon_flags = win32con.LR_LOADFROMFILE | win32con.LR_DEFAULTSIZE
            try:
                hicon = win32gui.LoadImage(0, str(self.icon_path), win32con.IMAGE_ICON, 0, 0, icon_flags)
            except Exception:
                hicon = 0
        if not hicon:
            hicon = win32gui.LoadIcon(0, win32con.IDI_APPLICATION)
        flags = win32gui.NIF_ICON | win32gui.NIF_MESSAGE | win32gui.NIF_TIP
        nid = (hwnd, 0, flags, WM_TRAY_NOTIFY, hicon, self.tooltip)
        try:
            win32gui.Shell_NotifyIcon(win32gui.NIM_ADD, nid)
        except Exception:
            try:
                win32gui.Shell_NotifyIcon(win32gui.NIM_MODIFY, nid)
            except Exception:
                win32gui.Shell_NotifyIcon(win32gui.NIM_ADD, nid)
        self._nid = nid
