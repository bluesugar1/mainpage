#!/usr/bin/env python3
"""당근 검색기 웹 화면을 '프로그램처럼' 실행하는 원클릭 런처."""

from __future__ import annotations

import atexit
import json
import socket
import socketserver
import threading
import time
import webbrowser
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from daangn_search_app import REGIONS, fetch_region_items

HOST = "127.0.0.1"


class AppHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, directory: str, **kwargs):
        self._root = directory
        super().__init__(*args, directory=directory, **kwargs)

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return

    def _send_json(self, payload: dict, status: int = 200) -> None:
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/api/search":
            query = parse_qs(parsed.query)
            keyword = query.get("keyword", [""])[0].strip()
            city = query.get("city", ["서울"])[0].strip()
            limit_raw = query.get("limit", ["1000"])[0]
            try:
                limit = max(1, min(1000, int(limit_raw)))
            except ValueError:
                limit = 1000

            if not keyword:
                self._send_json({"ok": False, "error": "검색어를 입력해 주세요."}, status=HTTPStatus.BAD_REQUEST)
                return
            if city not in REGIONS:
                self._send_json({"ok": False, "error": f"지원하지 않는 도시: {city}"}, status=HTTPStatus.BAD_REQUEST)
                return

            try:
                items = fetch_region_items(keyword, city, limit=limit)
            except Exception as exc:  # noqa: BLE001
                self._send_json({"ok": False, "error": f"매물 조회 실패: {exc}"}, status=HTTPStatus.BAD_GATEWAY)
                return

            self._send_json({"ok": True, "items": items, "count": len(items)})
            return

        super().do_GET()


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((HOST, 0))
        return int(sock.getsockname()[1])


def main() -> None:
    project_dir = Path(__file__).resolve().parent
    port = find_free_port()

    handler = lambda *args, **kwargs: AppHandler(*args, directory=str(project_dir), **kwargs)
    server = socketserver.ThreadingTCPServer((HOST, port), handler)

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
