#!/usr/bin/env python3
"""당근 검색기 웹 화면을 '프로그램처럼' 실행하는 원클릭 런처."""

from __future__ import annotations

import atexit
import http.server
import socket
import socketserver
import threading
import time
import webbrowser
from pathlib import Path

HOST = "127.0.0.1"


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((HOST, 0))
        return int(sock.getsockname()[1])


def main() -> None:
    project_dir = Path(__file__).resolve().parent
    port = find_free_port()

    handler = lambda *args, **kwargs: QuietHandler(*args, directory=str(project_dir), **kwargs)
    server = socketserver.TCPServer((HOST, port), handler)

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    def cleanup() -> None:
        server.shutdown()
        server.server_close()

    atexit.register(cleanup)

    url = f"http://{HOST}:{port}/index.html"
    print("=" * 60)
    print("당근 전국 검색기 웹앱을 실행했습니다.")
    print(f"브라우저 주소: {url}")
    print("종료하려면 이 창에서 Ctrl+C 를 누르세요.")
    print("=" * 60)

    webbrowser.open(url)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n앱을 종료합니다.")


if __name__ == "__main__":
    main()
