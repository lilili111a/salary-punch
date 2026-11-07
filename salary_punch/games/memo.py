# -*- coding: utf-8 -*-
"""工作备忘录 — 卡片内读写，本地持久化。"""

from __future__ import annotations

from pathlib import Path
from typing import Callable

import tkinter as tk

BG, CARD, ACCENT, TEXT, MUTED = "#0B0F17", "#1A2332", "#F5C542", "#E8EEF7", "#8B9BB4"
MEMO_NAME = "work_memo.txt"


class MemoView(tk.Frame):
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
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.path = self.data_dir / MEMO_NAME
        self._dirty = False
        self._save_job: str | None = None

        top = tk.Frame(self, bg=BG)
        top.pack(fill="x", padx=8, pady=(6, 2))
        tk.Label(top, text="工作备忘录", bg=BG, fg=TEXT, font=("Microsoft YaHei UI", 10, "bold")).pack(side="left")
        self.status = tk.Label(top, text="", bg=BG, fg=MUTED, font=("Microsoft YaHei UI", 8))
        self.status.pack(side="left", padx=8)
        tk.Button(
            top, text="← 薪资", command=self._back, bg=ACCENT, fg="#1A1400", relief="flat",
            font=("Microsoft YaHei UI", 8), padx=6, cursor="hand2",
        ).pack(side="right")

        wrap = tk.Frame(self, bg=CARD)
        wrap.pack(fill="both", expand=True, padx=10, pady=4)
        self.text = tk.Text(
            wrap, bg=CARD, fg=TEXT, insertbackground=ACCENT, relief="flat",
            font=("Microsoft YaHei UI", 10), wrap="word", padx=8, pady=8,
            undo=True,
        )
        self.text.pack(fill="both", expand=True)
        self.text.bind("<<Modified>>", self._on_modified)
        self.text.bind("<Control-s>", lambda _e: self._save(manual=True) or "break")

        bar = tk.Frame(self, bg=BG)
        bar.pack(fill="x", padx=8, pady=(0, 8))
        tk.Button(
            bar, text="保存", command=lambda: self._save(manual=True), bg=ACCENT, fg="#1A1400",
            relief="flat", font=("Microsoft YaHei UI", 8, "bold"), padx=10, cursor="hand2",
        ).pack(side="left")
        tk.Button(
            bar, text="清空", command=self._clear, bg=CARD, fg=TEXT, relief="flat",
            font=("Microsoft YaHei UI", 8), padx=8, cursor="hand2",
        ).pack(side="left", padx=6)
        tk.Label(bar, text="自动保存 · Ctrl+S", bg=BG, fg=MUTED, font=("Microsoft YaHei UI", 8)).pack(side="right")

        self._load()

    def destroy_game(self):
        self._save(manual=False)
        self.destroy()

    def _back(self):
        self._save(manual=False)
        if self.on_back:
            self.on_back()

    def _load(self) -> None:
        if self.path.exists():
            try:
                body = self.path.read_text(encoding="utf-8")
            except Exception:
                body = self.path.read_text(encoding="gbk", errors="replace")
        else:
            body = "【工作备忘录】\n- 今日待办：\n- 会议纪要：\n- 跟进事项：\n"
        self.text.delete("1.0", "end")
        self.text.insert("1.0", body)
        self.text.edit_modified(False)
        self._dirty = False
        self.status.configure(text="已载入")

    def _on_modified(self, _e=None):
        if self.text.edit_modified():
            self._dirty = True
            self.status.configure(text="未保存…")
            self.text.edit_modified(False)
            if self._save_job is not None:
                try:
                    self.after_cancel(self._save_job)
                except Exception:
                    pass
            self._save_job = self.after(800, lambda: self._save(manual=False))

    def _save(self, *, manual: bool) -> None:
        self._save_job = None
        try:
            body = self.text.get("1.0", "end-1c")
            self.path.write_text(body, encoding="utf-8")
            self._dirty = False
            self.status.configure(text="已保存" if manual else "自动保存")
        except Exception as ex:
            self.status.configure(text=f"保存失败:{ex}"[:18])

    def _clear(self) -> None:
        self.text.delete("1.0", "end")
        self._dirty = True
        self._save(manual=True)
