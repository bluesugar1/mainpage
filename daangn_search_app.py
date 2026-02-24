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
MAX_RESULTS = 1000
PAGE_SIZE = 100

# 서울 25개 구 각각 최소 1개 동 시드
SEOUL_GU_DONG_SEEDS = {
    "강남구": "역삼동",
    "강동구": "천호동",
    "강북구": "수유동",
    "강서구": "화곡동",
    "관악구": "신림동",
    "광진구": "자양동",
    "구로구": "구로동",
    "금천구": "가산동",
    "노원구": "상계동",
    "도봉구": "창동",
    "동대문구": "장안동",
    "동작구": "사당동",
    "마포구": "합정동",
    "서대문구": "홍제동",
    "서초구": "서초동",
    "성동구": "성수동",
    "성북구": "길음동",
    "송파구": "잠실동",
    "양천구": "신정동",
    "영등포구": "여의도동",
    "용산구": "이태원동",
    "은평구": "불광동",
    "종로구": "혜화동",
    "중구": "신당동",
    "중랑구": "면목동",
}


REGION_KEYWORDS = {
    "서울": ["서울", "강남", "강동", "강북", "강서", "관악", "광진", "구로", "금천", "노원", "도봉", "동대문", "동작", "마포", "서대문", "서초", "성동", "성북", "송파", "양천", "영등포", "용산", "은평", "종로", "중구", "중랑", "신당동", "약수동"],
    "경기": ["경기", "성남", "수원", "고양", "용인", "부천", "안양", "화성", "남양주", "안산", "평택", "시흥", "파주", "김포", "의정부", "하남", "광명", "군포", "오산", "이천", "구리", "의왕", "양주", "분당", "판교", "영통", "망포", "광교", "동탄", "배곧", "정왕"],
    "인천": ["인천", "부평", "남동", "연수", "미추홀", "서구", "송도"],
    "부산": ["부산", "해운대", "수영", "부산진", "동래", "남구"],
    "대구": ["대구", "수성", "달서", "중구", "북구"],
    "광주": ["광주", "광산", "서구", "북구", "동구"],
    "대전": ["대전", "유성", "서구", "중구"],
    "울산": ["울산", "남구", "중구", "북구"],
    "세종": ["세종"],
    "강원": ["강원", "원주", "춘천", "강릉"],
    "충북": ["충북", "청주", "충주", "제천"],
    "충남": ["충남", "천안", "아산", "공주"],
    "전북": ["전북", "전주", "익산", "군산"],
    "전남": ["전남", "순천", "여수", "목포"],
    "경북": ["경북", "포항", "구미", "경산"],
    "경남": ["경남", "창원", "김해", "진주"],
    "제주": ["제주", "서귀포"],
}


def region_matches_text(region: str, raw_text: str, location: str, current_seed: str) -> bool:
    # 서울은 인근 확장 특성상 필터를 느슨하게 유지
    if region == "서울":
        return True

    normalized_text = re.sub(r"\s+", " ", f"{raw_text} {location}")
    words = REGION_KEYWORDS.get(region, [region])

    # 1) 지역 키워드가 텍스트/지역에 명시된 경우만 통과
    if any(word in normalized_text for word in words):
        return True

    # 2) 현재 검색 시드(예: 성남시/수원시)가 제목/지역에 포함되면 통과
    seed_token = re.sub(r"-\d+$", "", current_seed)
    if seed_token and seed_token in normalized_text:
        return True

    return False

REGION_SEED_IN = {
    "서울": list(SEOUL_GU_DONG_SEEDS.values()),
    "경기": [
        "성남시", "수원시", "고양시", "용인시", "부천시", "안양시", "화성시", "남양주시", "안산시", "평택시", "시흥시",
        "파주시", "김포시", "의정부시", "하남시", "광명시", "군포시", "오산시", "이천시", "구리시", "의왕시", "양주시",
    ],
    "인천": ["부평구", "남동구", "연수구", "미추홀구", "서구"],
    "부산": ["해운대구", "수영구", "부산진구", "동래구", "남구"],
    "대구": ["수성구", "달서구", "중구", "북구"],
    "광주": ["광산구", "서구", "북구", "동구"],
    "대전": ["유성구", "서구", "중구"],
    "울산": ["남구", "중구", "북구"],
    "세종": ["세종시"],
    "강원": ["원주시", "춘천시", "강릉시"],
    "충북": ["청주시", "충주시", "제천시"],
    "충남": ["천안시", "아산시", "공주시"],
    "전북": ["전주시", "익산시", "군산시"],
    "전남": ["순천시", "여수시", "목포시"],
    "경북": ["포항시", "구미시", "경산시"],
    "경남": ["창원시", "김해시", "진주시"],
    "제주": ["제주시", "서귀포시"],
}


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


def build_search_link(keyword: str, in_value: str) -> str:
    params = urlencode({"in": in_value, "search": keyword})
    return f"{BASE_URL}?{params}"


def build_search_links(keyword: str, region: str) -> list[str]:
    seeds = REGION_SEED_IN.get(region, [region])
    urls: list[str] = []
    for seed in seeds:
        urls.append(build_search_link(keyword, seed))
        params = urlencode({"in": seed, "search": keyword})
        urls.append(f"https://www.daangn.com/kr/buy-sell/s/?{params}")
    return urls


def parse_anchor_text(text: str, fallback_region: str) -> tuple[str, str, str, str]:
    cleaned = re.sub(r"\s+", " ", html.unescape(text)).strip()

    price_match = re.search(r"(\d{1,3}(?:,\d{3})*원|나눔)", cleaned)
    price = price_match.group(1) if price_match else ""

    # '갤럭시' 같은 상품명이 지역으로 잘못 잡히는 문제 방지: 시(市) 단일 접미사는 제외
    candidates = re.findall(r"([가-힣0-9]{2,}(?:동|읍|면|리|구|군))", cleaned)
    location = fallback_region
    if candidates:
        # 보통 텍스트 후반에 지역이 위치하므로 뒤에서부터 채택
        location = candidates[-1]

    date_match = re.search(r"(\d+\s*(?:초|분|시간|일|주|개월|년)\s*전|방금\s*전?)", cleaned)
    uploaded_at = re.sub(r"\s+", "", date_match.group(1)) if date_match else ""

    title = cleaned
    if price_match:
        title = cleaned[:price_match.start()].strip(" ·|-_") or cleaned

    return title, price, location, uploaded_at


def is_completed_listing_text(text: str) -> bool:
    normalized = re.sub(r"\s+", " ", text)
    return any(word in normalized for word in ("판매완료", "거래완료", "예약중"))


def is_listing_url(href: str) -> bool:
    if not href:
        return False
    full = href if href.startswith("http") else f"https://www.daangn.com{href}"
    parsed = urlparse(full)
    path = parsed.path

    if "/articles/" in path:
        return True
    if not path.startswith("/kr/buy-sell/"):
        return False
    if path.startswith("/kr/buy-sell/s/"):
        return False
    if path.rstrip("/") == "/kr/buy-sell" and parsed.query:
        return False
    return path.rstrip("/") != "/kr/buy-sell"


def fetch_html(url: str) -> str:
    req = Request(url, headers={"User-Agent": UA, "Accept-Language": "ko-KR,ko;q=0.9"})
    with urlopen(req, timeout=15) as resp:
        return resp.read().decode("utf-8", errors="ignore")


def extract_neighborhood_urls(html_text: str, keyword: str, max_count: int = 20) -> list[str]:
    links = re.findall(r'href=["\'](/kr/buy-sell/\?in=[^"\']+)["\']', html_text)
    urls: list[str] = []
    seen: set[str] = set()
    for href in links:
        in_value = parse_qs(urlparse(html.unescape(href)).query).get("in", [""])[0]
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


def should_expand_nearby(region: str) -> bool:
    return region == "서울"


def per_url_pick_limit(total_limit: int) -> int:
    return max(5, min(50, total_limit // 20 if total_limit >= 100 else 10))


def unique_locations_count(rows: list[dict[str, str]]) -> int:
    return len({r.get("location", "") for r in rows if r.get("location")})


def fetch_region_items(keyword: str, region: str, limit: int) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    seen: set[str] = set()
    urls = build_search_links(keyword, region)

    idx = 0
    while idx < len(urls):
        url = urls[idx]
        idx += 1
        html_text = fetch_html(url)

        if should_expand_nearby(region):
            for nearby in extract_neighborhood_urls(html_text, keyword):
                if nearby not in urls:
                    urls.append(nearby)

        parser = ListingAnchorParser()
        parser.feed(html_text)

        picked_here = 0
        cap = per_url_pick_limit(limit)
        current_seed = parse_qs(urlparse(url).query).get("in", [""])[0]
        for href, text in parser.anchors:
            if picked_here >= cap:
                break
            if not is_listing_url(href) or is_completed_listing_text(text):
                continue

            full_url = href if href.startswith("http") else f"https://www.daangn.com{href}"
            if full_url in seen:
                continue

            title, price, location, uploaded_at = parse_anchor_text(text, region)
            if not region_matches_text(region, text, location, current_seed):
                continue

            seen.add(full_url)
            items.append(
                {
                    "region": region,
                    "title": title,
                    "price": price,
                    "location": location,
                    "uploaded_at": uploaded_at,
                    "url": full_url,
                }
            )
            picked_here += 1
            if len(items) >= limit:
                return items

    return items


class DaangnSearchApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("당근 통합 매물 검색기")
        self.root.geometry("1100x700")

        self.keyword_var = tk.StringVar()
        self.city_var = tk.StringVar(value="서울")
        self.status_var = tk.StringVar(value="검색어를 입력하고 [매물 가져오기]를 누르세요.")
        self.page_var = tk.StringVar(value="페이지 0 / 0")

        self.rows: list[dict[str, str]] = []
        self.current_page = 1
        self.page_size = PAGE_SIZE

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

        ttk.Label(frame, textvariable=self.status_var).pack(anchor="w", pady=(8, 4))

        pager = ttk.Frame(frame)
        pager.pack(fill="x", pady=(0, 6))
        ttk.Button(pager, text="◀ 이전", command=self.prev_page).pack(side="left")
        ttk.Label(pager, textvariable=self.page_var).pack(side="left", padx=8)
        ttk.Button(pager, text="다음 ▶", command=self.next_page).pack(side="left")

        cols = ("title", "price", "location", "uploaded_at", "url")
        self.tree = ttk.Treeview(frame, columns=cols, show="headings", height=22)
        self.tree.heading("title", text="제목")
        self.tree.heading("price", text="가격")
        self.tree.heading("location", text="지역")
        self.tree.heading("uploaded_at", text="올린날짜")
        self.tree.heading("url", text="링크")
        self.tree.column("title", width=340)
        self.tree.column("price", width=110)
        self.tree.column("location", width=110)
        self.tree.column("uploaded_at", width=110)
        self.tree.column("url", width=430)
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
            self.rows = fetch_region_items(keyword, region, limit=MAX_RESULTS)
        except Exception as exc:
            detail = str(exc)
            if "403" in detail:
                detail += "\n\n현재 네트워크/보안 환경에서 당근 요청이 차단된 상태입니다. (브라우저에서는 보이지만 스크립트 요청은 차단될 수 있음)"
            messagebox.showerror("조회 실패", f"매물 조회 중 오류가 발생했습니다.\n{detail}")
            self.status_var.set("조회 실패")
            return

        self.current_page = 1
        self.render_current_page()
        self.status_var.set(f"{region} 전체 권역에서 '{keyword}' 검색 결과 {len(self.rows)}건 (최대 {MAX_RESULTS}건)")
        if region != '서울' and unique_locations_count(self.rows) < 3:
            self.status_var.set(self.status_var.get() + ' | 경고: 지역 다양성이 낮습니다(사이트 응답 제한 가능).')

    def total_pages(self) -> int:
        if not self.rows:
            return 0
        return (len(self.rows) + self.page_size - 1) // self.page_size

    def render_current_page(self) -> None:
        for iid in self.tree.get_children():
            self.tree.delete(iid)

        pages = self.total_pages()
        if pages == 0:
            self.page_var.set("페이지 0 / 0")
            return

        self.current_page = max(1, min(self.current_page, pages))
        start = (self.current_page - 1) * self.page_size
        end = start + self.page_size
        for row in self.rows[start:end]:
            self.tree.insert(
                "",
                "end",
                values=(row["title"], row["price"], row["location"], row.get("uploaded_at", ""), row["url"]),
            )
        self.page_var.set(f"페이지 {self.current_page} / {pages}")

    def next_page(self) -> None:
        if self.current_page < self.total_pages():
            self.current_page += 1
            self.render_current_page()

    def prev_page(self) -> None:
        if self.current_page > 1:
            self.current_page -= 1
            self.render_current_page()

    def open_selected(self, _event=None) -> None:
        selected = self.tree.selection()
        if not selected:
            return
        values = self.tree.item(selected[0], "values")
        if len(values) >= 5:
            webbrowser.open_new_tab(values[4])

    def copy_rows(self) -> None:
        if not self.rows:
            return
        text = "\n".join(
            [f"{r['title']} | {r['price']} | {r['location']} | {r.get('uploaded_at','')} | {r['url']}" for r in self.rows]
        )
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
        detail = str(exc)
        if "403" in detail:
            detail += " | 원인: 현재 환경의 보안/프록시 차단(브라우저 수동 접속과 스크립트 요청이 다르게 처리될 수 있음)"
        print(f"조회 실패: {detail}", file=sys.stderr)
        return 1

    for row in rows:
        print(f"{row['title']} | {row['price']} | {row['location']} | {row.get('uploaded_at','')} | {row['url']}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="당근 통합 매물 검색기")
    parser.add_argument("--keyword", help="검색 키워드")
    parser.add_argument("--city", default="서울", help="도시명(예: 서울)")
    parser.add_argument("--limit", type=int, default=MAX_RESULTS, help="최대 출력 건수")
    args = parser.parse_args()

    if args.keyword:
        return run_cli(args.keyword, args.city.strip(), max(1, min(args.limit, MAX_RESULTS)))

    root = tk.Tk()
    app = DaangnSearchApp(root)
    del app
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
