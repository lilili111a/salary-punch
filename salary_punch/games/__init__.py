# -*- coding: utf-8 -*-
"""摸鱼小游戏 / 小应用 — 嵌入主卡片内页。"""

from __future__ import annotations

import inspect
from pathlib import Path
from typing import Callable

import tkinter as tk

_REGISTRY = {
    "ttt": ("ttt", "TicTacToeView"),
    "gomoku": ("gomoku", "GomokuView"),
    "shooter": ("shooter", "ShooterView"),
    "advice": ("advice", "AdviceView"),
    "muyu": ("muyu", "MuyuView"),
    "coin": ("coin", "CoinView"),
    "dice": ("dice", "DiceView"),
    "novel": ("novel", "NovelView"),
    "memo": ("memo", "MemoView"),
    "video": ("video", "VideoView"),
    "market": ("market", "MarketView"),
}


def mount_game(
    parent: tk.Misc,
    kind: str,
    *,
    width: int,
    height: int,
    on_back: Callable[[], None] | None = None,
    data_dir: Path | str | None = None,
) -> tk.Widget:
    kind = (kind or "").lower()
    aliases = {
        "井字棋": "ttt", "tictactoe": "ttt",
        "五子棋": "gomoku",
        "雷霆": "shooter", "战机": "shooter", "plane": "shooter",
        "建议": "advice", "人生建议": "advice",
        "木鱼": "muyu",
        "硬币": "coin", "命运": "coin",
        "骰子": "dice",
        "小说": "novel", "txt": "novel", "阅读": "novel",
        "备忘": "memo", "备忘录": "memo",
        "视频": "video", "行情": "market", "股票": "market", "基金": "market", "market": "market", "video": "video", "mp4": "video",
    }
    kind = aliases.get(kind, kind)
    if kind not in _REGISTRY:
        raise ValueError(f"unknown game: {kind}")
    mod_name, cls_name = _REGISTRY[kind]
    mod = __import__(f"salary_punch.games.{mod_name}", fromlist=[cls_name])
    cls = getattr(mod, cls_name)
    kwargs = {"width": width, "height": height, "on_back": on_back}
    try:
        params = inspect.signature(cls.__init__).parameters
        if "data_dir" in params and data_dir is not None:
            kwargs["data_dir"] = Path(data_dir)
    except Exception:
        pass
    return cls(parent, **kwargs)
