import argparse
import html
import re
import sys
import tkinter as tk
import webbrowser
from html.parser import HTMLParser
from tkinter import messagebox, ttk
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import Request, urlopen

REGIONS = [
    "서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종",
    "경기", "강원", "충북", "충남", "전북", "전남", "경북", "경남", "제주",
]
BASE_URL = "https://www.daangn.com/kr/buy-sell/"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"


class ListingAnchorParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.in_target_anchor = False
        self.current_href = ""
        self.current_text: list[str] = []
        self.anchors: list[tuple[str, str]] = []

    def handle_starttag(self, tag: str, attrs):
        if tag != "a":
            return
        href = dict(attrs).get("href", "")
        if "/articles/" in href or "/kr/buy-sell/" in href:
            self.in_target_anchor = True
            self.current_href = href
            self.current_text = []

    def handle_data(self, data: str):
        if self.in_target_anchor:
            self.current_text.append(data)

    def handle_endtag(self, tag: str):
        if tag == "a" and self.in_target_anchor:
            text = " ".join(part.strip() for part in self.current_text if part.strip())
            if text:
                self.anchors.append((self.current_href, re.sub(r"\s+", " ", text).strip()))
            self.in_target_anchor = False
            self.current_href = ""
            self.current_text = []


def build_search_link(keyword: str, region: str) -> str:
    params = urlencode({"in": region, "search": keyword})
    return f"{BASE_URL}?{params}"


def parse_anchor_text(text: str, fallback_region: str) -> tuple[str, str, str]:
    cleaned = html.unescape(text)
    parts = [p.strip() for p in re.split(r"\s{2,}|\|", cleaned) if p.strip()]
    title = parts[0] if parts else cleaned[:60]
    price = ""
    location = fallback_region
    for part in parts[1:]:
        if not price and ("원" in part or "나눔" in part):
            price = part
            continue
        if location == fallback_region and len(part) <= 20:
            location = part
    return title, price, location




def fetch_html(url: str) -> str:
    req = Request(url, headers={"User-Agent": UA, "Accept-Language": "ko-KR,ko;q=0.9"})
    with urlopen(req, timeout=15) as resp:
        return resp.read().decode("utf-8", errors="ignore")


def extract_neighborhood_urls(html_text: str, keyword: str, max_count: int = 12) -> list[str]:
    links = re.findall(r'href=["\'](/kr/buy-sell/\?in=[^"\']+)["\']', html_text)
    urls: list[str] = []
    seen: set[str] = set()
    for href in links:
        href = html.unescape(href)
        in_value = parse_qs(urlparse(href).query).get("in", [""])[0]
        if not in_value:
            continue
        full = f"https://www.daangn.com/kr/buy-sell/?{urlencode({'in': in_value, 'search': keyword})}"
        if full in seen:
            continue
        seen.add(full)
        urls.append(full)
        if len(urls) >= max_count:
            break
    return urls

def fetch_region_items(keyword: str, region: str, limit: int) -> list[dict[str, str]]:
    items = []
    seen = set()
    urls = [build_search_link(keyword, region)]

    for url in list(urls):
        html_text = fetch_html(url)
        for nearby in extract_neighborhood_urls(html_text, keyword):
            if nearby not in urls:
                urls.append(nearby)

        parser = ListingAnchorParser()
        parser.feed(html_text)

        for href, text in parser.anchors:
            full_url = href if href.startswith("http") else f"https://www.daangn.com{href}"
            if full_url in seen:
                continue
            seen.add(full_url)
            title, price, location = parse_anchor_text(text, region)
            items.append({
                "region": region,
                "title": title,
                "price": price,
                "location": location,
                "url": full_url,
            })
            if len(items) >= limit:
                return items

    return items


class DaangnSearchApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("당근 통합 매물 검색기")
        self.root.geometry("980x640")

        self.keyword_var = tk.StringVar()
        self.city_var = tk.StringVar(value="서울")
        self.status_var = tk.StringVar(value="검색어를 입력하고 [매물 가져오기]를 누르세요.")
        self.rows: list[dict[str, str]] = []

        self._build_ui()

    def _build_ui(self) -> None:
        frame = ttk.Frame(self.root, padding=12)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="🥕 당근 통합 매물 검색기", font=("Arial", 18, "bold")).pack(anchor="w")
        ttk.Label(
            frame,
            text="구/동을 직접 체크할 필요 없습니다. 도시 1개만 고르면 해당 도시 전체 권역 매물을 자동 조회합니다.",
        ).pack(anchor="w", pady=(4, 10))

        top = ttk.Frame(frame)
        top.pack(fill="x")

        ttk.Label(top, text="검색어").pack(side="left")
        entry = ttk.Entry(top, textvariable=self.keyword_var)
        entry.pack(side="left", fill="x", expand=True, padx=6)
        entry.bind("<Return>", lambda _e: self.search_items())

        ttk.Label(top, text="도시").pack(side="left", padx=(8, 0))
        city_combo = ttk.Combobox(top, values=REGIONS, textvariable=self.city_var, state="readonly", width=8)
        city_combo.pack(side="left", padx=(6, 0))

        ttk.Button(top, text="매물 가져오기", command=self.search_items).pack(side="left", padx=(8, 0))

        ttk.Label(frame, textvariable=self.status_var).pack(anchor="w", pady=(8, 6))

        cols = ("title", "price", "location", "url")
        self.tree = ttk.Treeview(frame, columns=cols, show="headings", height=20)
        self.tree.heading("title", text="제목")
        self.tree.heading("price", text="가격")
        self.tree.heading("location", text="지역")
        self.tree.heading("url", text="링크")
        self.tree.column("title", width=300)
        self.tree.column("price", width=120)
        self.tree.column("location", width=120)
        self.tree.column("url", width=420)
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<Double-1>", self.open_selected)

        actions = ttk.Frame(frame)
        actions.pack(fill="x", pady=(8, 0))
        ttk.Button(actions, text="선택 매물 열기", command=self.open_selected).pack(side="left")
        ttk.Button(actions, text="결과 복사", command=self.copy_rows).pack(side="left", padx=(8, 0))

    def search_items(self) -> None:
        keyword = self.keyword_var.get().strip()
        region = self.city_var.get().strip()

        if not keyword:
            messagebox.showwarning("입력 필요", "검색어를 입력해 주세요.")
            return
        if region not in REGIONS:
            messagebox.showwarning("선택 필요", "도시를 선택해 주세요.")
            return

        self.status_var.set("매물을 가져오는 중... 잠시만 기다려 주세요.")
        self.root.update_idletasks()

        try:
            self.rows = fetch_region_items(keyword, region, limit=80)
        except Exception as exc:
            messagebox.showerror("조회 실패", f"매물 조회 중 오류가 발생했습니다.\n{exc}")
            self.status_var.set("조회 실패")
            return

        for iid in self.tree.get_children():
            self.tree.delete(iid)

        for row in self.rows:
            self.tree.insert("", "end", values=(row["title"], row["price"], row["location"], row["url"]))

        self.status_var.set(f"{region} 전체 권역에서 '{keyword}' 검색 결과 {len(self.rows)}건")

    def open_selected(self, _event=None) -> None:
        selected = self.tree.selection()
        if not selected:
            return
        values = self.tree.item(selected[0], "values")
        if len(values) >= 4:
            webbrowser.open_new_tab(values[3])

    def copy_rows(self) -> None:
        if not self.rows:
            return
        text = "\n".join([f"{r['title']} | {r['price']} | {r['location']} | {r['url']}" for r in self.rows])
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.root.update()
        messagebox.showinfo("복사 완료", "검색 결과를 클립보드에 복사했습니다.")


def run_cli(keyword: str, city: str, limit: int) -> int:
    if city not in REGIONS:
        print(f"지원하지 않는 도시입니다: {city}", file=sys.stderr)
        return 1
    if not keyword.strip():
        print("키워드는 비어 있을 수 없습니다.", file=sys.stderr)
        return 1

    try:
        rows = fetch_region_items(keyword, city, limit=limit)
    except Exception as exc:
        print(f"조회 실패: {exc}", file=sys.stderr)
        return 1

    for row in rows:
        print(f"{row['title']} | {row['price']} | {row['location']} | {row['url']}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="당근 통합 매물 검색기")
    parser.add_argument("--keyword", help="검색 키워드")
    parser.add_argument("--city", default="서울", help="도시명(예: 서울)")
    parser.add_argument("--limit", type=int, default=30, help="최대 출력 건수")
    args = parser.parse_args()

    if args.keyword:
        return run_cli(args.keyword, args.city.strip(), args.limit)

    root = tk.Tk()
    app = DaangnSearchApp(root)
    del app
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
