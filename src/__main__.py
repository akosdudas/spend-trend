"""Launcher: start Streamlit and open it in a native pywebview window. See specs/08-tech-stack.md."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

from src.storage.paths import resolve_data_home

PORT = 8765
APP_FILE = Path(__file__).resolve().parent / "app.py"


def main() -> None:
    parser = argparse.ArgumentParser(description="spend-trends")
    parser.add_argument("--data-dir", dest="data_dir", default=None)
    args = parser.parse_args()

    data_home = resolve_data_home(args.data_dir)

    env = os.environ.copy()
    env["SPENDTRENDS_HOME"] = str(data_home)

    server = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            str(APP_FILE),
            "--server.port",
            str(PORT),
            "--server.headless",
            "true",
            "--browser.gatherUsageStats",
            "false",
        ],
        env=env,
    )

    try:
        time.sleep(2)  # give the server a moment to bind before opening the window
        import webview

        webview.create_window("spend-trends", f"http://localhost:{PORT}")
        webview.start()
    finally:
        server.terminate()
        server.wait()


if __name__ == "__main__":
    main()
