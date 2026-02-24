const regions = [
  "서울",
  "부산",
  "대구",
  "인천",
  "광주",
  "대전",
  "울산",
  "세종",
  "경기",
  "강원",
  "충북",
  "충남",
  "전북",
  "전남",
  "경북",
  "경남",
  "제주",
];

const regionRoot = document.getElementById("regions");
const selectAll = document.getElementById("select-all");
const form = document.getElementById("search-form");
const result = document.getElementById("result");

function createRegionSelector() {
  const html = regions
    .map(
      (region, index) => `
      <label class="region-item">
        <input type="checkbox" class="region" value="${region}" ${index >= 0 ? "checked" : ""} />
        <span>${region}</span>
      </label>
    `,
    )
    .join("");

  regionRoot.innerHTML = html;
}

function getSelectedRegions() {
  return [...document.querySelectorAll(".region:checked")].map((el) => el.value);
}

function buildSearchLink(keyword, region) {
  const base = "https://www.daangn.com/kr/buy-sell/";
  const params = new URLSearchParams({
    in: region,
    search: keyword,
  });
  return `${base}?${params.toString()}`;
}

form.addEventListener("submit", (event) => {
  event.preventDefault();

  const keyword = document.getElementById("keyword").value.trim();
  const selected = getSelectedRegions();

  if (!keyword) {
    result.innerHTML = '<p class="hint">키워드를 입력해 주세요.</p>';
    return;
  }

  if (!selected.length) {
    result.innerHTML = '<p class="hint">최소 1개 이상의 지역을 선택해 주세요.</p>';
    return;
  }

  const links = selected
    .map((region) => {
      const url = buildSearchLink(keyword, region);
      return `<li><a href="${url}" target="_blank" rel="noopener noreferrer">${region}에서 '${keyword}' 검색</a></li>`;
    })
    .join("");

  result.innerHTML = `
    <h2>'${keyword}' 검색 링크 (${selected.length}개 지역)</h2>
    <ul>${links}</ul>
    <div class="actions">
      <button id="open-all" type="button">모든 링크 새 탭으로 열기</button>
    </div>
    <p class="hint">※ 당근 웹 정책/URL 형식 변경 시 일부 링크가 동작하지 않을 수 있습니다.</p>
  `;

  const openAll = document.getElementById("open-all");
  openAll.addEventListener("click", () => {
    selected.forEach((region) => {
      const url = buildSearchLink(keyword, region);
      window.open(url, "_blank", "noopener,noreferrer");
    });
  });
});

selectAll.addEventListener("change", (event) => {
  const checked = event.target.checked;
  document.querySelectorAll(".region").forEach((checkbox) => {
    checkbox.checked = checked;
  });
});

createRegionSelector();
result.innerHTML = '<p class="hint">키워드를 넣고 버튼을 눌러 주세요.</p>';
