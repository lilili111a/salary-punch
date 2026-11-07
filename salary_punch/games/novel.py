# -*- coding: utf-8 -*-
"""TXT 小说阅读 — 多文件连续自动翻页，记住进度。"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Callable

import tkinter as tk
from tkinter import filedialog

BG, CARD, ACCENT, TEXT, MUTED = "#0B0F17", "#1A2332", "#F5C542", "#E8EEF7", "#8B9BB4"

STATE_NAME = "novel_state.json"
CHARS_PER_PAGE = 180


def _decode_bytes(raw: bytes) -> str:
    for enc in ("utf-8-sig", "utf-8", "gb18030", "gbk", "big5"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


class NovelView(tk.Frame):
    def __init__(
        self,
        master,
        *,
        width: int,
        height: int,
        on_back: Callable[[], None] | None = None,
        data_dir: Path | None = None,
    ):
        super().__init__(master, bg=BG, width=width, height=height)
        self.on_back = on_back
        self.pack_propagate(False)
        self.data_dir = Path(data_dir) if data_dir else Path.cwd() / "data"
        self.novels_dir = self.data_dir / "novels"
        self.novels_dir.mkdir(parents=True, exist_ok=True)
        self.state_path = self.data_dir / STATE_NAME
        self.files: list[str] = []
        self.file_idx = 0
        self.offset = 0
        self.auto = True
        self.interval_ms = 3500
        self._job: str | None = None
        self._text = ""

        top = tk.Frame(self, bg=BG)
        top.pack(fill="x", padx=8, pady=(6, 2))
        tk.Label(top, text="TXT小说", bg=BG, fg=TEXT, font=("Microsoft YaHei UI", 10, "bold")).pack(side="left")
        tk.Button(
            top, text="← 薪资", command=self._back, bg=ACCENT, fg="#1A1400", relief="flat",
            font=("Microsoft YaHei UI", 8), padx=6, cursor="hand2",
        ).pack(side="right")

        self.meta = tk.Label(self, text="", bg=BG, fg=MUTED, font=("Microsoft YaHei UI", 8), anchor="w")
        self.meta.pack(fill="x", padx=10)

        self.page = tk.Label(
            self, text="请添加 TXT…", bg=CARD, fg=TEXT, wraplength=width - 36,
            justify="left", font=("Microsoft YaHei UI", 10), padx=10, pady=10, anchor="nw",
        )
        self.page.pack(fill="both", expand=True, padx=10, pady=4)

        bar = tk.Frame(self, bg=BG)
        bar.pack(fill="x", padx=8, pady=(0, 8))
        for txt, cmd in (
            ("添加", self._add_files),
            ("上页", self._prev_page),
            ("下页", self._next_page),
            ("自动", self._toggle_auto),
        ):
            tk.Button(
                bar, text=txt, command=cmd, bg=CARD, fg=TEXT, relief="flat",
                font=("Microsoft YaHei UI", 8), padx=6, cursor="hand2",
            ).pack(side="left", padx=2)

        self._load_state()
        self._ensure_sample()
        self._reload_current(save=False)
        if self.auto:
            self._arm_auto()

    def destroy_game(self):
        self._cancel_auto()
        self._save_state()
        self.destroy()

    def _back(self):
        self._cancel_auto()
        self._save_state()
        if self.on_back:
            self.on_back()

    def _state_default(self) -> dict:
        return {
            "files": [],
            "file_idx": 0,
            "offset": 0,
            "auto": True,
            "interval_ms": 3500,
        }

    def _load_state(self) -> None:
        st = self._state_default()
        if self.state_path.exists():
            try:
                st.update(json.loads(self.state_path.read_text(encoding="utf-8")))
            except Exception:
                pass
        # reconcile with folder
        disk = sorted(p.name for p in self.novels_dir.glob("*.txt"))
        files = [f for f in st.get("files", []) if (self.novels_dir / f).exists()]
        for name in disk:
            if name not in files:
                files.append(name)
        self.files = files
        self.file_idx = max(0, min(int(st.get("file_idx") or 0), max(0, len(self.files) - 1)))
        self.offset = max(0, int(st.get("offset") or 0))
        self.auto = bool(st.get("auto", True))
        self.interval_ms = max(1200, int(st.get("interval_ms") or 3500))

    def _save_state(self) -> None:
        payload = {
            "files": self.files,
            "file_idx": self.file_idx,
            "offset": self.offset,
            "auto": self.auto,
            "interval_ms": self.interval_ms,
        }
        try:
            self.state_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass

    def _ensure_sample(self) -> None:
        if self.files:
            return
        sample = self.novels_dir / "示例短篇.txt"
        if not sample.exists():
            sample.write_text(
                "【示例】工位文学\n\n"
                "午后的阳光斜斜切进屏幕反光里。你把薪资卡片往角落一拖，假装在看广告。\n\n"
                "其实你在翻下一页小说。进度被悄悄记住，像一份只属于自己的备忘。\n\n"
                "鼠标一走，世界恢复正经；鼠标一回，故事接着讲。\n\n"
                "——完（可右键菜单→TXT小说→添加，导入更多 txt）\n",
                encoding="utf-8",
            )
        self.files = [sample.name]
        self.file_idx = 0
        self.offset = 0
        self._save_state()

    def _add_files(self) -> None:
        paths = filedialog.askopenfilenames(
            title="选择 TXT 小说",
            filetypes=[("Text", "*.txt"), ("All", "*.*")],
        )
        if not paths:
            return
        for p in paths:
            src = Path(p)
            if not src.is_file():
                continue
            dest = self.novels_dir / src.name
            n = 1
            while dest.exists() and dest.resolve() != src.resolve():
                dest = self.novels_dir / f"{src.stem}_{n}{src.suffix}"
                n += 1
            if dest.resolve() != src.resolve():
                shutil.copy2(src, dest)
            if dest.name not in self.files:
                self.files.append(dest.name)
        self._save_state()
        self._reload_current(save=True)

    def _current_path(self) -> Path | None:
        if not self.files:
            return None
        self.file_idx = max(0, min(self.file_idx, len(self.files) - 1))
        return self.novels_dir / self.files[self.file_idx]

    def _reload_current(self, *, save: bool) -> None:
        path = self._current_path()
        if not path or not path.exists():
            self._text = ""
            self.page.configure(text="暂无小说，点「添加」导入 TXT")
            self.meta.configure(text="")
            return
        self._text = _decode_bytes(path.read_bytes())
        if self.offset >= len(self._text):
            self.offset = max(0, len(self._text) - CHARS_PER_PAGE)
        self._render()
        if save:
            self._save_state()

    def _render(self) -> None:
        total = max(1, len(self._text))
        chunk = self._text[self.offset : self.offset + CHARS_PER_PAGE]
        if not chunk:
            chunk = "（本章结束）"
        name = self.files[self.file_idx] if self.files else "-"
        pct = int(self.offset * 100 / total)
        auto = "ON" if self.auto else "OFF"
        self.meta.configure(
            text=f"{self.file_idx + 1}/{len(self.files)} {name} · {pct}% · 自动{auto}"
        )
        self.page.configure(text=chunk)

    def _prev_page(self) -> None:
        self.offset = max(0, self.offset - CHARS_PER_PAGE)
        self._render()
        self._save_state()

    def _next_page(self) -> None:
        if not self._text:
            self._reload_current(save=False)
        nxt = self.offset + CHARS_PER_PAGE
        if nxt < len(self._text):
            self.offset = nxt
            self._render()
            self._save_state()
            return
        # next file
        if self.file_idx + 1 < len(self.files):
            self.file_idx += 1
            self.offset = 0
            self._reload_current(save=True)
        else:
            # loop
            self.file_idx = 0
            self.offset = 0
            self._reload_current(save=True)

    def _toggle_auto(self) -> None:
        self.auto = not self.auto
        self._save_state()
        self._render()
        if self.auto:
            self._arm_auto()
        else:
            self._cancel_auto()

    def _arm_auto(self) -> None:
        self._cancel_auto()
        if not self.auto:
            return
        self._job = self.after(self.interval_ms, self._auto_tick)

    def _auto_tick(self) -> None:
        self._job = None
        if not self.winfo_exists() or not self.auto:
            return
        self._next_page()
        self._arm_auto()

    def _cancel_auto(self) -> None:
        if self._job is not None:
            try:
                self.after_cancel(self._job)
            except Exception:
                pass
            self._job = None
