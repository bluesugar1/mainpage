const regions = ["서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종", "경기", "강원", "충북", "충남", "전북", "전남", "경북", "경남", "제주"];
const PAGE_SIZE = 100;

const cityEl = document.getElementById("city");
const form = document.getElementById("search-form");
const result = document.getElementById("result");

let rows = [];
let page = 1;

cityEl.innerHTML = regions.map((r) => `<option value="${r}">${r}</option>`).join("");
cityEl.value = "서울";

function totalPages() {
  return rows.length ? Math.ceil(rows.length / PAGE_SIZE) : 0;
}

function renderRows() {
  if (!rows.length) {
    result.innerHTML = `<p class="hint">검색 결과가 0건입니다. 당근 측 차단(봇 방지) 또는 페이지 구조 변경일 수 있어요.</p>`;
    return;
  }

  const pages = totalPages();
  page = Math.max(1, Math.min(page, pages));
  const start = (page - 1) * PAGE_SIZE;
  const pageRows = rows.slice(start, start + PAGE_SIZE);

  const body = pageRows
    .map(
      (row) => `
      <tr>
        <td>${row.title || ""}</td>
        <td>${row.price || ""}</td>
        <td>${row.location || ""}</td>
        <td>${row.uploaded_at || ""}</td>
        <td><a href="${row.url}" target="_blank" rel="noopener noreferrer">열기</a></td>
      </tr>`,
    )
    .join("");

  result.innerHTML = `
    <p class="hint">총 ${rows.length}건 (최대 1,000건) | 페이지 ${page} / ${pages}</p>
    <div class="actions">
      <button type="button" id="prev-page" ${page <= 1 ? "disabled" : ""}>◀ 이전</button>
      <button type="button" id="next-page" ${page >= pages ? "disabled" : ""}>다음 ▶</button>
    </div>
    <div class="table-wrap">
      <table>
        <thead><tr><th>제목</th><th>가격</th><th>지역</th><th>올린날짜</th><th>링크</th></tr></thead>
        <tbody>${body}</tbody>
      </table>
    </div>
  `;

  document.getElementById("prev-page").addEventListener("click", () => {
    page -= 1;
    renderRows();
  });
  document.getElementById("next-page").addEventListener("click", () => {
    page += 1;
    renderRows();
  });
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const keyword = document.getElementById("keyword").value.trim();
  const city = cityEl.value;

  if (!keyword) {
    result.innerHTML = '<p class="hint">키워드를 입력해 주세요.</p>';
    return;
  }

  result.innerHTML = '<p class="hint">매물 가져오는 중...</p>';

  try {
    const resp = await fetch(`/api/search?keyword=${encodeURIComponent(keyword)}&city=${encodeURIComponent(city)}&limit=1000`);
    const data = await resp.json();
    if (!resp.ok || !data.ok) {
      throw new Error(data.error || "조회 실패");
    }
    rows = data.items || [];
    page = 1;
    renderRows();
  } catch (err) {
    result.innerHTML = `<p class="hint">실패: ${err.message}</p>`;
  }
});

result.innerHTML = '<p class="hint">검색어를 넣고 매물 가져오기를 눌러 주세요.</p>';
