"""Bitácora de auditoría append-only (JSONL): qué se detectó, propuso, verificó y aplicó."""
from __future__ import annotations
import json, os, time
from typing import Any, Dict, List, Optional


class Ledger:
    def __init__(self, path: Optional[str] = None):
        self.path, self.rows = path, []

    def log(self, event: str, **data: Any) -> None:
        row: Dict[str, Any] = {"ts": time.time(), "event": event, **data}
        self.rows.append(row)
        if self.path:
            os.makedirs(os.path.dirname(os.path.abspath(self.path)) or ".", exist_ok=True)
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")

    def events(self) -> List[str]:
        return [r["event"] for r in self.rows]
