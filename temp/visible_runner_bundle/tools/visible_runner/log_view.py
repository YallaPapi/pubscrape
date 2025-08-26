#!/usr/bin/env python3
"""
log_view.py — Live view of the most recent run_visible log.
Usage:
  python log_view.py
"""
import time, pathlib, sys
from rich.live import Live
from rich.panel import Panel
from rich.text import Text

root = pathlib.Path(__file__).resolve().parent
logs = root / "logs"
target = logs / "latest.log"

def read_tail(path, last_size=[0]):
    if not path.exists():
        return "No log yet. Run run_visible.py first."
    size = path.stat().st_size
    if size < last_size[0]:
        last_size[0] = 0  # rotated
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        f.seek(last_size[0])
        data = f.read()
        last_size[0] = size
        return data or ""

def main():
    with Live(refresh_per_second=10) as live:
        while True:
            chunk = read_tail(target)
            if chunk:
                live.update(Panel.fit(Text.from_ansi(chunk[-8000:])))  # show last ~8KB
            else:
                live.update(Panel.fit(Text("Waiting for output...")))
            time.sleep(0.1)

if __name__ == "__main__":
    main()
