# -*- coding: utf-8 -*-
from pathlib import Path

ROOT = Path(r"D:\ieswork\salary-punch")

tray = ROOT / "salary_punch" / "tray_win.py"
t = tray.read_text(encoding="utf-8")
if "1065" not in t:
    t = t.replace(
        '            1064: (lambda: self.on_open_game("video")) if self.on_open_game else None,\n'
        "            1063: self.on_toggle_ad_camouflage,",
        '            1064: (lambda: self.on_open_game("video")) if self.on_open_game else None,\n'
        '            1065: (lambda: self.on_open_game("market")) if self.on_open_game else None,\n'
        "            1063: self.on_toggle_ad_camouflage,",
        1,
    )
    t = t.replace(
        '        win32gui.AppendMenu(office, win32con.MF_STRING, 1064, "视频播放")\n'
        '        win32gui.AppendMenu(menu, win32con.MF_POPUP, office, "办公工具")',
        '        win32gui.AppendMenu(office, win32con.MF_STRING, 1064, "视频播放")\n'
        '        win32gui.AppendMenu(office, win32con.MF_STRING, 1065, "股票基金")\n'
        '        win32gui.AppendMenu(menu, win32con.MF_POPUP, office, "办公工具")',
        1,
    )
    tray.write_text(t, encoding="utf-8")
    print("tray market wired")
else:
    print("tray already has 1065")

ui = ROOT / "salary_punch" / "ui.py"
u = ui.read_text(encoding="utf-8")
# dedupe consecutive identical ButtonRelease binds
lines = u.splitlines(keepends=True)
out = []
prev = None
removed = 0
for line in lines:
    if (
        prev is not None
        and 'bind("<ButtonRelease-1>", self._end_drag)' in line
        and line == prev
    ):
        removed += 1
        continue
    out.append(line)
    prev = line
if removed:
    ui.write_text("".join(out), encoding="utf-8")
    print(f"removed {removed} duplicate ButtonRelease binds")
else:
    print("no duplicate binds")

# ensure ad_cover also ends drag
u = ui.read_text(encoding="utf-8")
needle = (
    "        for w in (self.ad_cover,):\n"
    '            w.bind("<ButtonPress-1>", self._start_drag)\n'
    '            w.bind("<B1-Motion>", self._on_drag)\n'
)
repl = (
    "        for w in (self.ad_cover,):\n"
    '            w.bind("<ButtonPress-1>", self._start_drag)\n'
    '            w.bind("<B1-Motion>", self._on_drag)\n'
    '            w.bind("<ButtonRelease-1>", self._end_drag)\n'
)
if needle in u and 'ad_cover' in u:
    # only add if ad_cover loop lacks release
    idx = u.find("for w in (self.ad_cover,):")
    chunk = u[idx : idx + 220]
    if "_end_drag" not in chunk:
        u = u.replace(needle, repl, 1)
        ui.write_text(u, encoding="utf-8")
        print("ad_cover release bound")
    else:
        print("ad_cover already has release")

u = ui.read_text(encoding="utf-8")
print("ui 2065", "2065" in u, "股票基金" in u)
print("clear_drag calls", u.count("_clear_drag()"))
import ast
ast.parse(u)
ast.parse(tray.read_text(encoding="utf-8"))
ast.parse((ROOT / "salary_punch" / "games" / "market.py").read_text(encoding="utf-8"))
print("syntax ok")
