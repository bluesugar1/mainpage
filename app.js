const regions = ["서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종", "경기", "강원", "충북", "충남", "전북", "전남", "경북", "경남", "제주"];

const cityEl = document.getElementById("city");
const form = document.getElementById("search-form");
const result = document.getElementById("result");

cityEl.innerHTML = regions.map((r) => `<option value="${r}">${r}</option>`).join("");
cityEl.value = "서울";

function renderRows(items) {
  if (!items.length) {
    result.innerHTML = `<p class="hint">검색 결과가 0건입니다. 당근 측 차단(봇 방지) 또는 순간적인 페이지 구조 변경일 수 있어요.</p>`;
    return;
  }

  const rows = items
    .map(
      (row) => `
      <tr>
        <td>${row.title || ""}</td>
        <td>${row.price || ""}</td>
        <td>${row.location || ""}</td>
        <td><a href="${row.url}" target="_blank" rel="noopener noreferrer">열기</a></td>
      </tr>`,
    )
    .join("");

  result.innerHTML = `
    <p class="hint">총 ${items.length}건</p>
    <div class="table-wrap">
      <table>
        <thead><tr><th>제목</th><th>가격</th><th>지역</th><th>링크</th></tr></thead>
        <tbody>${rows}</tbody>
      </table>
    </div>
  `;
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
    const resp = await fetch(`/api/search?keyword=${encodeURIComponent(keyword)}&city=${encodeURIComponent(city)}&limit=80`);
    const data = await resp.json();
    if (!resp.ok || !data.ok) {
      throw new Error(data.error || "조회 실패");
    }
    renderRows(data.items || []);
  } catch (err) {
    result.innerHTML = `<p class="hint">실패: ${err.message}</p>`;
  }
});

result.innerHTML = '<p class="hint">검색어를 넣고 매물 가져오기를 눌러 주세요.</p>';
