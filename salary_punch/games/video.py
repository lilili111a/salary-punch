# -*- coding: utf-8 -*-
"""卡片内视频播放 — OpenCV 逐帧 + PIL；无 OpenCV 时回退系统播放器。"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Callable

import tkinter as tk
from tkinter import filedialog

BG, CARD, ACCENT, TEXT, MUTED = "#0B0F17", "#1A2332", "#F5C542", "#E8EEF7", "#8B9BB4"
STATE_NAME = "video_state.json"

try:
    import cv2  # type: ignore
except Exception:
    cv2 = None  # type: ignore

try:
    import numpy as np  # type: ignore
    from PIL import Image, ImageTk  # type: ignore
except Exception:
    np = None  # type: ignore
    Image = None  # type: ignore
    ImageTk = None  # type: ignore


class VideoView(tk.Frame):
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
        self.W, self.H = width, height
        self.data_dir = Path(data_dir) if data_dir else Path.cwd() / "data"
        self.videos_dir = self.data_dir / "videos"
        self.videos_dir.mkdir(parents=True, exist_ok=True)
        self.state_path = self.data_dir / STATE_NAME

        self.files: list[str] = []
        self.file_idx = 0
        self.playing = False
        self._cap = None
        self._job: str | None = None
        self._photo = None
        self._frame_delay = 33
        self._pos_frame = 0

        top = tk.Frame(self, bg=BG)
        top.pack(fill="x", padx=8, pady=(6, 2))
        tk.Label(top, text="视频", bg=BG, fg=TEXT, font=("Microsoft YaHei UI", 10, "bold")).pack(side="left")
        self.meta = tk.Label(top, text="", bg=BG, fg=MUTED, font=("Microsoft YaHei UI", 8))
        self.meta.pack(side="left", padx=8)
        tk.Button(
            top, text="← 薪资", command=self._back, bg=ACCENT, fg="#1A1400", relief="flat",
            font=("Microsoft YaHei UI", 8), padx=6, cursor="hand2",
        ).pack(side="right")

        self.screen = tk.Label(self, bg="#000000", fg=MUTED, text="添加 mp4 后播放", font=("Microsoft YaHei UI", 9))
        self.screen.pack(fill="both", expand=True, padx=10, pady=4)

        bar = tk.Frame(self, bg=BG)
        bar.pack(fill="x", padx=8, pady=(0, 8))
        for txt, cmd in (
            ("添加", self._add_files),
            ("▶/❚❚", self._toggle_play),
            ("下一部", self._next_file),
            ("系统播", self._open_system),
        ):
            tk.Button(
                bar, text=txt, command=cmd, bg=CARD, fg=TEXT, relief="flat",
                font=("Microsoft YaHei UI", 8), padx=6, cursor="hand2",
            ).pack(side="left", padx=2)

        self._engine_ok = bool(cv2 is not None and Image is not None and ImageTk is not None)
        if not self._engine_ok:
            self.screen.configure(text="未装 OpenCV：可「添加」后用「系统播」\n(打包版已内嵌播放引擎)")

        self._load_state()
        if self.files:
            self._open_current(resume=True)

    def destroy_game(self):
        self._stop_playback(save=True)
        self.destroy()

    def _back(self):
        self._stop_playback(save=True)
        if self.on_back:
            self.on_back()

    def _load_state(self) -> None:
        st = {"files": [], "file_idx": 0, "pos_frame": 0}
        if self.state_path.exists():
            try:
                st.update(json.loads(self.state_path.read_text(encoding="utf-8")))
            except Exception:
                pass
        disk = sorted(p.name for p in self.videos_dir.glob("*") if p.suffix.lower() in {".mp4", ".avi", ".mkv", ".mov", ".webm"})
        files = [f for f in st.get("files", []) if (self.videos_dir / f).exists()]
        for name in disk:
            if name not in files:
                files.append(name)
        self.files = files
        self.file_idx = max(0, min(int(st.get("file_idx") or 0), max(0, len(self.files) - 1)))
        self._pos_frame = max(0, int(st.get("pos_frame") or 0))

    def _save_state(self) -> None:
        if self._cap is not None and self._engine_ok:
            try:
                self._pos_frame = int(self._cap.get(cv2.CAP_PROP_POS_FRAMES) or self._pos_frame)
            except Exception:
                pass
        payload = {"files": self.files, "file_idx": self.file_idx, "pos_frame": self._pos_frame}
        try:
            self.state_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass

    def _add_files(self) -> None:
        paths = filedialog.askopenfilenames(
            title="选择视频",
            filetypes=[
                ("Video", "*.mp4;*.avi;*.mkv;*.mov;*.webm"),
                ("MP4", "*.mp4"),
                ("All", "*.*"),
            ],
        )
        if not paths:
            return
        for p in paths:
            src = Path(p)
            if not src.is_file():
                continue
            dest = self.videos_dir / src.name
            n = 1
            while dest.exists() and dest.resolve() != src.resolve():
                dest = self.videos_dir / f"{src.stem}_{n}{src.suffix}"
                n += 1
            if dest.resolve() != src.resolve():
                shutil.copy2(src, dest)
            if dest.name not in self.files:
                self.files.append(dest.name)
        self.file_idx = len(self.files) - 1
        self._pos_frame = 0
        self._save_state()
        self._open_current(resume=False)
        if self._engine_ok:
            self._start_playback()

    def _current_path(self) -> Path | None:
        if not self.files:
            return None
        self.file_idx = max(0, min(self.file_idx, len(self.files) - 1))
        return self.videos_dir / self.files[self.file_idx]

    def _release_cap(self) -> None:
        if self._cap is not None:
            try:
                self._cap.release()
            except Exception:
                pass
            self._cap = None

    def _stop_playback(self, *, save: bool) -> None:
        self.playing = False
        if self._job is not None:
            try:
                self.after_cancel(self._job)
            except Exception:
                pass
            self._job = None
        if save:
            self._save_state()
        self._release_cap()

    def _open_current(self, *, resume: bool) -> None:
        self._stop_playback(save=False)
        path = self._current_path()
        if not path:
            self.screen.configure(image="", text="请「添加」mp4 等视频")
            self.meta.configure(text="")
            return
        self.meta.configure(text=f"{self.file_idx + 1}/{len(self.files)} {path.name}")
        if not self._engine_ok:
            self.screen.configure(image="", text=f"已选：{path.name}\n点「系统播」用默认播放器\n或安装 opencv 后重打包以卡片内播放")
            return
        cap = cv2.VideoCapture(str(path))
        if not cap.isOpened():
            self.screen.configure(image="", text=f"无法打开：{path.name}")
            return
        fps = float(cap.get(cv2.CAP_PROP_FPS) or 0) or 24.0
        self._frame_delay = max(15, int(1000 / fps))
        if resume and self._pos_frame > 0:
            cap.set(cv2.CAP_PROP_POS_FRAMES, float(self._pos_frame))
        self._cap = cap
        self._show_frame(force_one=True)

    def _toggle_play(self) -> None:
        if not self._engine_ok:
            self._open_system()
            return
        if self._cap is None:
            self._open_current(resume=True)
        if self._cap is None:
            return
        if self.playing:
            self.playing = False
            if self._job is not None:
                try:
                    self.after_cancel(self._job)
                except Exception:
                    pass
                self._job = None
            self._save_state()
        else:
            self._start_playback()

    def _start_playback(self) -> None:
        if not self._engine_ok or self._cap is None:
            return
        self.playing = True
        self._tick()

    def _tick(self) -> None:
        self._job = None
        if not self.playing or not self.winfo_exists():
            return
        ok = self._show_frame(force_one=False)
        if ok:
            self._job = self.after(self._frame_delay, self._tick)
        else:
            # next file or loop
            self.playing = False
            self._save_state()
            if self.file_idx + 1 < len(self.files):
                self.file_idx += 1
                self._pos_frame = 0
                self._open_current(resume=False)
                self._start_playback()
            else:
                self.file_idx = 0
                self._pos_frame = 0
                self._open_current(resume=False)

    def _show_frame(self, *, force_one: bool) -> bool:
        if self._cap is None:
            return False
        ok, frame = self._cap.read()
        if not ok or frame is None:
            return False
        try:
            self._pos_frame = int(self._cap.get(cv2.CAP_PROP_POS_FRAMES) or self._pos_frame)
        except Exception:
            pass
        # BGR -> RGB
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w = frame.shape[:2]
        # fit into screen area (~ card minus chrome)
        max_w = max(80, self.W - 24)
        max_h = max(60, self.H - 86)
        scale = min(max_w / max(w, 1), max_h / max(h, 1))
        nw, nh = max(1, int(w * scale)), max(1, int(h * scale))
        if nw != w or nh != h:
            frame = cv2.resize(frame, (nw, nh), interpolation=cv2.INTER_AREA)
        img = Image.fromarray(frame)
        self._photo = ImageTk.PhotoImage(img)
        self.screen.configure(image=self._photo, text="")
        return True

    def _next_file(self) -> None:
        if not self.files:
            return
        self._save_state()
        self.file_idx = (self.file_idx + 1) % len(self.files)
        self._pos_frame = 0
        self._open_current(resume=False)
        if self.playing or self._engine_ok:
            self._start_playback()

    def _open_system(self) -> None:
        path = self._current_path()
        if not path or not path.exists():
            self._add_files()
            path = self._current_path()
        if not path:
            return
        try:
            if sys.platform.startswith("win"):
                subprocess.Popen(["cmd", "/c", "start", "", str(path)], shell=False)
            else:
                subprocess.Popen(["xdg-open", str(path)])
        except Exception as ex:
            self.screen.configure(text=f"系统播放失败: {ex}"[:40])
