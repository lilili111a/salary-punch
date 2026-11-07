# -*- coding: utf-8 -*-
"""Apply market module + drag fix + verify fish persist markers."""
from __future__ import annotations

import re
import shutil
from pathlib import Path

ROOT = Path(r"D:\ieswork\salary-punch")


def find_src(name: str) -> Path:
    for cand in (
        Path.home() / name,
        ROOT / "tools" / name,
        Path(r"C:\Users\iesla") / name,
    ):
        if cand.exists():
            return cand
    raise FileNotFoundError(name)


def patch_drag(ui_path: Path) -> None:
    t = ui_path.read_text(encoding="utf-8")
    orig = t

    if "self._dragging" not in t:
        t = t.replace(
            "        self._drag_x = 0\n        self._drag_y = 0\n",
            "        self._drag_x = 0\n        self._drag_y = 0\n        self._dragging = False\n",
            1,
        )

    # rewrite start/on drag
    old_start = '''    def _start_drag(self, e):
        self._on_activity()
        self._drag_x = e.x
        self._drag_y = e.y

    def _on_drag(self, e):
        x = self.root.winfo_x() + e.x - self._drag_x
        y = self.root.winfo_y() + e.y - self._drag_y
        self.root.geometry(f"+{x}+{y}")
'''
    new_start = '''    def _start_drag(self, e):
        self._on_activity()
        # 仅在薪资卡片空白处开始拖；进游戏/菜单后会 clear，避免误跟鼠标
        if getattr(self, "_view", "salary") != "salary":
            self._dragging = False
            return
        if getattr(self, "_menu_busy", False) or getattr(self, "_ad_camouflaged", False):
            # 广告卡仍允许拖，菜单打开时不允许
            if getattr(self, "_menu_busy", False):
                self._dragging = False
                return
        self._dragging = True
        self._drag_x = e.x
        self._drag_y = e.y

    def _end_drag(self, _e=None):
        self._dragging = False

    def _clear_drag(self) -> None:
        self._dragging = False

    def _on_drag(self, e):
        if not getattr(self, "_dragging", False):
            return
        if getattr(self, "_view", "salary") != "salary":
            self._dragging = False
            return
        if getattr(self, "_menu_busy", False):
            self._dragging = False
            return
        x = self.root.winfo_x() + e.x - self._drag_x
        y = self.root.winfo_y() + e.y - self._drag_y
        self.root.geometry(f"+{x}+{y}")
'''
    if "def _clear_drag" not in t:
        if old_start not in t:
            # looser match via regex
            m = re.search(
                r"    def _start_drag\(self, e\):.*?    def _on_drag\(self, e\):.*?\n        self\.root\.geometry\(f\"\+\{x\}\+\{y\}\"\)\n",
                t,
                flags=re.S,
            )
            if not m:
                raise SystemExit("drag block not found")
            t = t[: m.start()] + new_start + t[m.end() :]
        else:
            t = t.replace(old_start, new_start, 1)

    # bind ButtonRelease-1 to end drag on root/canvas/ad
    if 'w.bind("<ButtonRelease-1>", self._end_drag)' not in t:
        t = t.replace(
            '            w.bind("<ButtonPress-1>", self._start_drag)\n'
            '            w.bind("<B1-Motion>", self._on_drag)\n'
            '            w.bind("<Double-Button-1>", lambda _e: self._open_config())\n',
            '            w.bind("<ButtonPress-1>", self._start_drag)\n'
            '            w.bind("<B1-Motion>", self._on_drag)\n'
            '            w.bind("<ButtonRelease-1>", self._end_drag)\n'
            '            w.bind("<Double-Button-1>", lambda _e: self._open_config())\n',
            1,
        )
        t = t.replace(
            '            w.bind("<ButtonPress-1>", self._start_drag)\n'
            '            w.bind("<B1-Motion>", self._on_drag)\n',
            '            w.bind("<ButtonPress-1>", self._start_drag)\n'
            '            w.bind("<B1-Motion>", self._on_drag)\n'
            '            w.bind("<ButtonRelease-1>", self._end_drag)\n',
            1,  # ad_cover loop
        )

    # clear drag in show_game / show_salary / _popup / _dark_popup start
    if "self._clear_drag()" not in t:
        t = t.replace(
            "    def show_salary(self) -> None:\n"
            "        \"\"\"切回薪资视图；若摸鱼是进游戏自动开的，则结束本次摸鱼。\"\"\"\n"
            "        leaving_game = getattr(self, \"_view\", \"salary\") != \"salary\"\n",
            "    def show_salary(self) -> None:\n"
            "        \"\"\"切回薪资视图；若摸鱼是进游戏自动开的，则结束本次摸鱼。\"\"\"\n"
            "        self._clear_drag()\n"
            "        leaving_game = getattr(self, \"_view\", \"salary\") != \"salary\"\n",
            1,
        )
        t = t.replace(
            "    def show_game(self, kind: str) -> None:\n"
            "        \"\"\"卡片内打开小游戏/小应用，并默认进入摸鱼计时。\"\"\"\n"
            "        self._unmount_game()\n",
            "    def show_game(self, kind: str) -> None:\n"
            "        \"\"\"卡片内打开小游戏/小应用，并默认进入摸鱼计时。\"\"\"\n"
            "        self._clear_drag()\n"
            "        self._unmount_game()\n",
            1,
        )
        t = t.replace(
            "    def _popup(self, e):\n"
            "        self._on_activity()\n"
            "        self._on_card_enter()\n",
            "    def _popup(self, e):\n"
            "        self._clear_drag()\n"
            "        self._on_activity()\n"
            "        self._on_card_enter()\n",
            1,
        )
        # dark popup beginning
        if "def _dark_popup_menu" in t and "_clear_drag()" not in t[t.find("def _dark_popup_menu"): t.find("def _dark_popup_menu") + 200]:
            t = t.replace(
                "    def _dark_popup_menu(self, x_root: int, y_root: int) -> None:\n",
                "    def _dark_popup_menu(self, x_root: int, y_root: int) -> None:\n"
                "        self._clear_drag()\n",
                1,
            )

    if t != orig:
        ui_path.write_text(t, encoding="utf-8")
        print("patched drag in ui.py")
    else:
        print("drag already patched or no change")


def patch_market() -> None:
    src = find_src("market.py")
    dst = ROOT / "salary_punch" / "games" / "market.py"
    shutil.copy2(src, dst)
    print("copied", src, "->", dst)

    init = ROOT / "salary_punch" / "games" / "__init__.py"
    t = init.read_text(encoding="utf-8")
    if '"market"' not in t:
        t = t.replace(
            '"video": ("video", "VideoView"),\n}',
            '"video": ("video", "VideoView"),\n    "market": ("market", "MarketView"),\n}',
            1,
        )
        if "行情" not in t:
            t = t.replace(
                '"视频": "video"',
                '"视频": "video", "行情": "market", "股票": "market", "基金": "market", "market": "market"',
                1,
            )
        init.write_text(t, encoding="utf-8")
        print("patched games/__init__.py")
    else:
        print("games init already has market")

    ui = ROOT / "salary_punch" / "ui.py"
    ut = ui.read_text(encoding="utf-8")
    changed = False
    if "2065" not in ut:
        ut2 = ut.replace(
            '            2064: lambda: self.show_game("video"),\n            2063: self.toggle_ad_camouflage,',
            '            2064: lambda: self.show_game("video"),\n'
            '            2065: lambda: self.show_game("market"),\n'
            '            2063: self.toggle_ad_camouflage,',
            1,
        )
        if ut2 != ut:
            ut = ut2
            changed = True
        # office menu items
        for a, b in [
            (
                '("item", "视频播放", act(2064)),',
                '("item", "视频播放", act(2064)),\n            ("item", "股票基金", act(2065)),',
            ),
            (
                '("item", "🎬  视频播放", act(2064)),',
                '("item", "🎬  视频播放", act(2064)),\n            ("item", "📈  股票基金", act(2065)),',
            ),
        ]:
            if a in ut and "act(2065)" not in ut:
                ut = ut.replace(a, b, 1)
                changed = True
                break
        if changed:
            ui.write_text(ut, encoding="utf-8")
            print("patched ui market menu")
        else:
            print("WARN: could not wire 2065; dumping office lines")
            for n, line in enumerate(ut.splitlines(), 1):
                if "2064" in line or "视频" in line or "office" in line:
                    print(n, line)
    else:
        print("ui already has 2065")

    # tray
    tray = ROOT / "salary_punch" / "tray_win.py"
    tt = tray.read_text(encoding="utf-8")
    if "视频" in tt and "2065" not in tt:
        # try common patterns
        patterns = [
            (
                'win32gui.AppendMenu(menu, win32con.MF_STRING, 2064, "视频播放")',
                'win32gui.AppendMenu(menu, win32con.MF_STRING, 2064, "视频播放")\n'
                '        win32gui.AppendMenu(menu, win32con.MF_STRING, 2065, "股票基金")',
            ),
        ]
        for a, b in patterns:
            if a in tt:
                tt = tt.replace(a, b, 1)
                tray.write_text(tt, encoding="utf-8")
                print("patched tray menu label")
                break
        else:
            for n, line in enumerate(tt.splitlines(), 1):
                if "2064" in line or "视频" in line:
                    print("tray", n, line)

    # ensure tray action dispatch includes 2065 if it maps ids
    tt = tray.read_text(encoding="utf-8")
    if "2064" in tt and "2065" not in tt:
        # handler dict style
        if "2064:" in tt:
            tt = tt.replace(
                "2064:",
                "2064:",
            )
        # look for on_open_game("video")
        if 'on_open_game("video")' in tt or "on_open_game('video')" in tt:
            tt = tt.replace(
                'elif cmd_id == 2064:\n',
                'elif cmd_id == 2064:\n',
            )
        # dump for visibility
        for n, line in enumerate(tt.splitlines(), 1):
            if "2064" in line or "video" in line.lower():
                print("tray-h", n, line)

    for path_name in ("build_exe.ps1", "tools/rebuild_now.py", "SalaryPunch.spec"):
        p = ROOT / path_name
        if not p.exists():
            continue
        enc = "utf-8-sig" if p.suffix == ".ps1" else "utf-8"
        bt = p.read_text(encoding=enc)
        if "salary_punch.games.market" in bt:
            continue
        if p.suffix == ".ps1":
            bt = bt.replace(
                "--hidden-import salary_punch.games.video `",
                "--hidden-import salary_punch.games.video `\n"
                "  --hidden-import salary_punch.games.market `",
                1,
            )
        elif p.name == "rebuild_now.py":
            bt = bt.replace(
                '"--hidden-import", "salary_punch.games.video",',
                '"--hidden-import", "salary_punch.games.video",\n'
                '    "--hidden-import", "salary_punch.games.market",',
                1,
            )
        else:
            bt = bt.replace(
                "'salary_punch.games.video'",
                "'salary_punch.games.video', 'salary_punch.games.market'",
                1,
            )
        p.write_text(bt, encoding="utf-8" if p.suffix != ".ps1" else "utf-8")
        print("patched", path_name)


def verify_fish() -> None:
    run = (ROOT / "run.py").read_text(encoding="utf-8")
    fish = (ROOT / "salary_punch" / "fish.py").read_text(encoding="utf-8")
    assert "AppData" in run and "settle_fish_on_exit" in run
    assert "def checkpoint_fish" in fish
    print("fish persist markers OK")


def main() -> None:
    verify_fish()
    patch_market()
    patch_drag(ROOT / "salary_punch" / "ui.py")
    # syntax check
    import ast

    for rel in [
        "run.py",
        "salary_punch/ui.py",
        "salary_punch/fish.py",
        "salary_punch/games/market.py",
        "salary_punch/games/__init__.py",
    ]:
        ast.parse((ROOT / rel).read_text(encoding="utf-8"))
        print("syntax OK", rel)


if __name__ == "__main__":
    main()
