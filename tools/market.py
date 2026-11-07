# -*- coding: utf-8 -*-
"""股票/基金简要行情 — 卡片内关注列表，公开接口拉取。

注意：禁止在工作线程直接调用 Tk after/widget；用 Queue + 主线程轮询投递结果。
"""

from __future__ import annotations

import json
import queue
import re
import ssl
import threading
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable

import tkinter as tk
from tkinter import simpledialog

BG, CARD, ACCENT, TEXT, MUTED = "#0B0F17", "#1A2332", "#F5C542", "#E8EEF7", "#8B9BB4"
UP, DOWN, FLAT = "#F87171", "#34D399", "#94A3B8"
WATCH_NAME = "market_watchlist.json"

DEFAULT_WATCH: list[dict[str, str]] = [
    {"code": "sh600519", "kind": "stock", "note": "贵州茅台"},
    {"code": "sz000001", "kind": "stock", "note": "平安银行"},
    {"code": "sh000001", "kind": "stock", "note": "上证指数"},
    {"code": "f_110022", "kind": "fund", "note": "易方达消费"},
]

_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def _normalize_code(raw: str, kind: str | None = None) -> tuple[str, str]:
    """返回 (sina_list_code, kind). kind=stock|fund."""
    s = (raw or "").strip().lower().replace(" ", "")
    if not s:
        raise ValueError("空代码")
    if s.startswith("f_"):
        return s, "fund"
    if s.startswith("fund:"):
        digits = re.sub(r"\D", "", s.split(":", 1)[1])
        if len(digits) != 6:
            raise ValueError(f"无法识别基金代码: {raw}")
        return "f_" + digits, "fund"
    if s.startswith(("sh", "sz", "bj")) and kind != "fund":
        return s, "stock"
    digits = re.sub(r"\D", "", s)
    if len(digits) != 6:
        raise ValueError(f"无法识别代码: {raw}")
    if kind == "fund":
        return "f_" + digits, "fund"
    if digits.startswith(("5", "6", "9")):
        return "sh" + digits, "stock"
    if digits.startswith(("0", "1", "2", "3")):
        return "sz" + digits, "stock"
    if digits.startswith(("4", "8")):
        return "bj" + digits, "stock"
    return "sh" + digits, "stock"


def _http_get(url: str, *, referer: str | None, unverified: bool = False) -> bytes:
    headers = {"User-Agent": _UA}
    if referer:
        headers["Referer"] = referer
    req = urllib.request.Request(url, headers=headers)
    ctx = ssl._create_unverified_context() if unverified else ssl.create_default_context()
    with urllib.request.urlopen(req, timeout=8, context=ctx) as resp:
        return resp.read()


def _parse_sina(raw: str) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for line in raw.strip().splitlines():
        if "=" not in line:
            continue
        left, right = line.split("=", 1)
        code = left.replace("var hq_str_", "").strip()
        payload = right.strip().strip(";").strip().strip('"')
        if not payload:
            out[code] = {"ok": False, "error": "无数据"}
            continue
        parts = payload.split(",")
        try:
            if code.startswith("f_"):
                # 名称,最新净值,累计净值,前日净值,净值日期,...
                name = parts[0]
                nav = float(parts[1] or 0)
                prev = float(parts[3] or 0) if len(parts) > 3 else 0.0
                # 若 parts[3] 像日期则退回 parts[2]
                if prev <= 0 and len(parts) > 2:
                    try:
                        prev = float(parts[2] or 0)
                    except ValueError:
                        prev = 0.0
                pct = ((nav - prev) / prev * 100.0) if prev else 0.0
                out[code] = {
                    "ok": True,
                    "kind": "fund",
                    "name": name,
                    "price": nav,
                    "prev": prev,
                    "pct": pct,
                    "extra": parts[4] if len(parts) > 4 else "",
                }
            else:
                name = parts[0]
                prev = float(parts[2] or 0)
                price = float(parts[3] or 0)
                high = float(parts[4] or 0) if len(parts) > 4 else 0.0
                low = float(parts[5] or 0) if len(parts) > 5 else 0.0
                pct = ((price - prev) / prev * 100.0) if prev else 0.0
                out[code] = {
                    "ok": True,
                    "kind": "stock",
                    "name": name,
                    "price": price,
                    "prev": prev,
                    "pct": pct,
                    "high": high,
                    "low": low,
                }
        except (ValueError, IndexError) as e:
            out[code] = {"ok": False, "error": str(e)}
    return out


def _parse_tencent(raw: str) -> dict[str, dict[str, Any]]:
    """腾讯行情备用：v_sh600519=\"1~名~代码~现价~昨收~...\""""
    out: dict[str, dict[str, Any]] = {}
    for line in raw.strip().splitlines():
        if "=" not in line:
            continue
        left, right = line.split("=", 1)
        key = left.strip()
        if key.startswith("v_"):
            code = key[2:]
        else:
            code = key
        payload = right.strip().strip(";").strip().strip('"')
        if not payload or payload == "":
            out[code] = {"ok": False, "error": "无数据"}
            continue
        parts = payload.split("~")
        try:
            if len(parts) < 5:
                out[code] = {"ok": False, "error": "字段不足"}
                continue
            name = parts[1]
            price = float(parts[3] or 0)
            prev = float(parts[4] or 0)
            pct = ((price - prev) / prev * 100.0) if prev else 0.0
            high = float(parts[33] or 0) if len(parts) > 33 else 0.0
            low = float(parts[34] or 0) if len(parts) > 34 else 0.0
            out[code] = {
                "ok": True,
                "kind": "stock",
                "name": name,
                "price": price,
                "prev": prev,
                "pct": pct,
                "high": high,
                "low": low,
            }
        except (ValueError, IndexError) as e:
            out[code] = {"ok": False, "error": str(e)}
    return out


def _fetch_sina(codes: list[str]) -> dict[str, dict[str, Any]]:
    if not codes:
        return {}
    url = "https://hq.sinajs.cn/list=" + ",".join(codes)
    last_err: Exception | None = None
    for unverified in (False, True):
        try:
            blob = _http_get(
                url, referer="https://finance.sina.com.cn", unverified=unverified
            )
            text = blob.decode("gbk", errors="replace")
            parsed = _parse_sina(text)
            if parsed:
                return parsed
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as e:
            last_err = e
            continue
    # 腾讯备用（仅股票；基金仍依赖新浪）
    stocks = [c for c in codes if not c.startswith("f_")]
    funds = [c for c in codes if c.startswith("f_")]
    out: dict[str, dict[str, Any]] = {}
    if stocks:
        try:
            turl = "https://qt.gtimg.cn/q=" + ",".join(stocks)
            blob = _http_get(turl, referer=None, unverified=True)
            # 腾讯常用 gbk
            text = blob.decode("gbk", errors="replace")
            out.update(_parse_tencent(text))
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as e:
            last_err = e
    if funds:
        # 基金单独再打一次新浪
        try:
            furl = "https://hq.sinajs.cn/list=" + ",".join(funds)
            blob = _http_get(
                furl, referer="https://finance.sina.com.cn", unverified=True
            )
            out.update(_parse_sina(blob.decode("gbk", errors="replace")))
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as e:
            last_err = e
    if out:
        return out
    if last_err:
        raise last_err
    return {c: {"ok": False, "error": "无数据"} for c in codes}


class MarketView(tk.Frame):
    def __init__(
        self,
        master,
        *,
        width: int,
        height: int,
        on_back: Callable[[], None] | None = None,
        data_dir: Path | None = None,
        **_kwargs,
    ):
        super().__init__(master, bg=BG, width=width, height=height)
        self.on_back = on_back
        self.pack_propagate(False)
        self.data_dir = Path(data_dir) if data_dir else Path.cwd() / "data"
        try:
            self.data_dir.mkdir(parents=True, exist_ok=True)
        except OSError:
            # 打包目录可能只读，退回用户目录
            import os

            fallback = Path(os.environ.get("APPDATA") or Path.home()) / "SalaryPunch"
            fallback.mkdir(parents=True, exist_ok=True)
            self.data_dir = fallback
        self.path = self.data_dir / WATCH_NAME
        self.watch: list[dict[str, str]] = self._load_watch()
        self._quotes: dict[str, dict[str, Any]] = {}
        self._job: str | None = None
        self._poll_job: str | None = None
        self._fetching = False
        self._result_q: queue.Queue = queue.Queue()

        top = tk.Frame(self, bg=BG)
        top.pack(fill="x", padx=8, pady=(6, 2))
        tk.Label(
            top, text="股票 · 基金", bg=BG, fg=TEXT, font=("Microsoft YaHei UI", 10, "bold")
        ).pack(side="left")
        self.status = tk.Label(top, text="", bg=BG, fg=MUTED, font=("Microsoft YaHei UI", 8))
        self.status.pack(side="left", padx=8)
        tk.Button(
            top,
            text="← 薪资",
            command=self._back,
            bg=ACCENT,
            fg="#1A1400",
            relief="flat",
            font=("Microsoft YaHei UI", 8),
            padx=6,
            cursor="hand2",
        ).pack(side="right")

        bar = tk.Frame(self, bg=BG)
        bar.pack(fill="x", padx=8, pady=(0, 4))
        for text, cmd in (
            ("刷新", self.refresh),
            ("加股票", lambda: self._add("stock")),
            ("加基金", lambda: self._add("fund")),
            ("删选中", self._remove_selected),
        ):
            tk.Button(
                bar,
                text=text,
                command=cmd,
                bg=CARD,
                fg=TEXT,
                relief="flat",
                font=("Microsoft YaHei UI", 8),
                padx=8,
                cursor="hand2",
            ).pack(side="left", padx=(0, 4))

        wrap = tk.Frame(self, bg=CARD)
        wrap.pack(fill="both", expand=True, padx=10, pady=(0, 8))
        self.listbox = tk.Listbox(
            wrap,
            bg=CARD,
            fg=TEXT,
            selectbackground="#334155",
            selectforeground=TEXT,
            relief="flat",
            font=("Microsoft YaHei UI", 9),
            activestyle="none",
            highlightthickness=0,
            borderwidth=0,
        )
        self.listbox.pack(fill="both", expand=True, padx=4, pady=4)

        hint = tk.Label(
            self,
            text="代码例：600519 / sh600519 · 基金 110022  · 约 20 秒自动刷新",
            bg=BG,
            fg=MUTED,
            font=("Microsoft YaHei UI", 7),
        )
        hint.pack(fill="x", padx=10, pady=(0, 6))

        self._render_rows()
        self.refresh()
        self._schedule()
        self._poll_results()

    def _load_watch(self) -> list[dict[str, str]]:
        if self.path.exists():
            try:
                raw = json.loads(self.path.read_text(encoding="utf-8"))
                if isinstance(raw, list) and raw:
                    cleaned = []
                    for item in raw:
                        if not isinstance(item, dict):
                            continue
                        code = str(item.get("code") or "").strip()
                        kind = str(item.get("kind") or "stock").strip().lower()
                        note = str(item.get("note") or "").strip()
                        if not code:
                            continue
                        try:
                            sina, kind2 = _normalize_code(code, kind)
                        except ValueError:
                            continue
                        cleaned.append({"code": sina, "kind": kind2, "note": note})
                    if cleaned:
                        return cleaned
            except (OSError, json.JSONDecodeError, TypeError, ValueError):
                pass
        self._save_watch(DEFAULT_WATCH)
        return [dict(x) for x in DEFAULT_WATCH]

    def _save_watch(self, items: list[dict[str, str]] | None = None) -> None:
        data = items if items is not None else self.watch
        try:
            self.path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except OSError:
            pass

    def _back(self) -> None:
        self.destroy_game()
        if self.on_back:
            self.on_back()

    def destroy_game(self) -> None:
        if self._job:
            try:
                self.after_cancel(self._job)
            except Exception:
                pass
            self._job = None
        if self._poll_job:
            try:
                self.after_cancel(self._poll_job)
            except Exception:
                pass
            self._poll_job = None

    def _schedule(self) -> None:
        self._job = self.after(20000, self._tick)

    def _tick(self) -> None:
        self.refresh()
        self._schedule()

    def _poll_results(self) -> None:
        """主线程轮询工作线程结果（禁止工作线程直接 after 更新 UI）。"""
        try:
            while True:
                item = self._result_q.get_nowait()
                self._fetching = False
                err = item.get("err")
                data = item.get("data") or {}
                if err:
                    self.status.configure(text=f"失败: {str(err)[:40]}", fg=UP)
                else:
                    self._quotes = data
                    ok_n = sum(1 for v in data.values() if v.get("ok"))
                    self.status.configure(text=f"已更新 {ok_n}/{len(data)}", fg=FLAT)
                self._render_rows()
        except queue.Empty:
            pass
        try:
            self._poll_job = self.after(200, self._poll_results)
        except Exception:
            self._poll_job = None

    def _add(self, kind: str) -> None:
        title = "添加股票代码" if kind == "stock" else "添加基金代码"
        prompt = "如 600519 或 sh600519" if kind == "stock" else "如 110022"
        raw = simpledialog.askstring(title, prompt, parent=self)
        if not raw:
            return
        try:
            sina, kind2 = _normalize_code(raw, kind)
        except ValueError as e:
            self.status.configure(text=str(e), fg=UP)
            return
        for item in self.watch:
            if item["code"] == sina:
                self.status.configure(text="已在关注列表", fg=MUTED)
                return
        self.watch.append({"code": sina, "kind": kind2, "note": ""})
        self._save_watch()
        self._render_rows()
        self.refresh()

    def _remove_selected(self) -> None:
        sel = list(self.listbox.curselection())
        if not sel:
            self.status.configure(text="先点选一行再删", fg=MUTED)
            return
        idx = sel[0]
        if 0 <= idx < len(self.watch):
            self.watch.pop(idx)
            self._save_watch()
            self._render_rows()
            self.refresh()

    def _render_rows(self) -> None:
        self.listbox.delete(0, "end")
        for item in self.watch:
            code = item["code"]
            q = self._quotes.get(code) or {}
            fg = MUTED
            if q.get("ok"):
                name = q.get("name") or item.get("note") or code
                price = q.get("price") or 0.0
                pct = float(q.get("pct") or 0.0)
                sign = "+" if pct > 0 else ""
                tag = "基" if item.get("kind") == "fund" else "股"
                line = f"[{tag}] {name}  {price:.3f}  {sign}{pct:.2f}%"
                # A股习惯：涨红跌绿
                if pct > 0:
                    fg = UP
                elif pct < 0:
                    fg = DOWN
                else:
                    fg = FLAT
            else:
                note = item.get("note") or code
                err = (q.get("error") if q else None) or "等待行情…"
                tag = "基" if item.get("kind") == "fund" else "股"
                line = f"[{tag}] {note}  —  {err}"
                fg = MUTED
            self.listbox.insert("end", line)
            try:
                self.listbox.itemconfig("end", foreground=fg)
            except Exception:
                pass

    def refresh(self) -> None:
        if self._fetching:
            return
        codes = [x["code"] for x in self.watch]
        if not codes:
            self.status.configure(text="关注列表为空", fg=MUTED)
            self._render_rows()
            return
        self._fetching = True
        self.status.configure(text="拉取中…", fg=MUTED)

        def work() -> None:
            err = None
            data: dict[str, dict[str, Any]] = {}
            try:
                data = _fetch_sina(codes)
            except (urllib.error.URLError, TimeoutError, OSError, ValueError) as e:
                err = str(e)
            except Exception as e:  # noqa: BLE001 — 展示给用户
                err = f"{type(e).__name__}: {e}"
            self._result_q.put({"err": err, "data": data})

        threading.Thread(target=work, daemon=True).start()
