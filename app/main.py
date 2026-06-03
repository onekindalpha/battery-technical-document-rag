from __future__ import annotations

import os

import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from app.api import router
from app.service import service

service.ingest_samples_if_empty()

app = FastAPI(
    title="Battery Technical Document RAG Assistant",
    description="Battery RUL research copilot MVP with document RAG.",
    version="0.1.0",
)
app.include_router(router)


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return """
<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Battery RUL Research Copilot</title>
  <style>
    :root {
      color-scheme: dark;
      --bg: #0f141b;
      --panel: #171d26;
      --panel-2: #111722;
      --text: #eef3f8;
      --muted: #9da8b7;
      --line: #2a3441;
      --accent: #46c2a3;
      --accent-2: #7da7ff;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Apple SD Gothic Neo", "Noto Sans KR", sans-serif;
      background: var(--bg);
      color: var(--text);
    }
    main {
      width: min(1180px, calc(100vw - 40px));
      margin: 32px auto;
    }
    h1 {
      margin: 0 0 8px;
      font-size: 30px;
      line-height: 1.2;
    }
    .subtitle {
      margin: 0 0 24px;
      color: var(--muted);
    }
    .layout {
      display: grid;
      grid-template-columns: 1fr 360px;
      gap: 18px;
      align-items: start;
    }
    .panel {
      border: 1px solid var(--line);
      background: var(--panel);
      border-radius: 8px;
      padding: 18px;
    }
    .chat {
      min-height: 470px;
      display: flex;
      flex-direction: column;
      gap: 12px;
    }
    .message {
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 14px;
      background: var(--panel-2);
      line-height: 1.55;
    }
    .message p {
      margin: 0 0 10px;
    }
    .message p:last-child {
      margin-bottom: 0;
    }
    .message strong {
      color: #ffffff;
      font-weight: 800;
    }
    .message.user {
      border-color: rgba(125, 167, 255, 0.55);
      white-space: pre-wrap;
    }
    .message.assistant {
      border-color: rgba(70, 194, 163, 0.55);
    }
    .result-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      margin-bottom: 10px;
      color: var(--muted);
      font-size: 13px;
      font-weight: 700;
      letter-spacing: 0.02em;
      text-transform: uppercase;
    }
    .source-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
      gap: 10px;
      margin-top: 14px;
    }
    .source-card {
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #0d131c;
      padding: 11px;
    }
    .source-name {
      color: var(--text);
      font-size: 13px;
      font-weight: 750;
      word-break: break-all;
    }
    .source-meta {
      margin-top: 6px;
      color: var(--muted);
      font-size: 12px;
    }
    .input-row {
      display: grid;
      grid-template-columns: 1fr 96px;
      gap: 10px;
      margin-top: 14px;
    }
    textarea, input[type="file"] {
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #0c1118;
      color: var(--text);
      padding: 12px;
      font: inherit;
    }
    textarea {
      min-height: 54px;
      resize: vertical;
    }
    button {
      border: 0;
      border-radius: 8px;
      background: var(--accent);
      color: #07110e;
      font-weight: 700;
      cursor: pointer;
      font: inherit;
    }
    button.secondary {
      width: 100%;
      margin-top: 10px;
      padding: 12px;
      background: var(--accent-2);
      color: #08101e;
    }
    .examples {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-top: 12px;
    }
    .example {
      border: 1px solid var(--line);
      background: #101722;
      color: var(--text);
      padding: 9px 11px;
      font-size: 13px;
      font-weight: 600;
    }
    .note {
      margin: 0 0 14px;
      color: var(--muted);
      font-size: 14px;
      line-height: 1.55;
    }
    h2 {
      margin: 0 0 12px;
      font-size: 16px;
    }
    ul {
      margin: 8px 0 0;
      padding-left: 18px;
      color: var(--muted);
      line-height: 1.8;
      word-break: break-all;
    }
    .status {
      min-height: 22px;
      margin-top: 10px;
      color: var(--muted);
      font-size: 14px;
    }
    .sources {
      margin-top: 18px;
    }
    .service-note {
      margin-top: 18px;
      border-top: 1px solid var(--line);
      padding-top: 16px;
    }
    .capability-list {
      display: grid;
      gap: 8px;
      margin-top: 10px;
    }
    .capability {
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #0d131c;
      padding: 10px;
      color: var(--muted);
      font-size: 13px;
      line-height: 1.45;
    }
    .capability strong {
      display: block;
      margin-bottom: 4px;
      color: var(--text);
    }
    @media (max-width: 820px) {
      main { width: min(100vw - 24px, 680px); margin: 20px auto; }
      .layout { grid-template-columns: 1fr; }
      .input-row { grid-template-columns: 1fr; }
      button { padding: 12px; }
    }
  </style>
</head>
<body>
  <main>
    <h1>Battery RUL Research Copilot</h1>
    <p class="subtitle">Battery RUL 프로젝트의 논문 요약, 실험 메모, 데이터 검증 기준을 검색하고 근거 chunk와 함께 답변을 확인합니다.</p>
    <div class="layout">
      <section>
        <div id="chat" class="panel chat"></div>
        <div class="examples" aria-label="예시 질문">
          <button class="example" data-question="초기 cycle 기반 RUL 예측에서 데이터 누수를 막으려면 무엇을 확인해야 하나요?">데이터 누수 점검</button>
          <button class="example" data-question="RUL과 SoH는 무엇이 다르고 대시보드에서는 어떻게 보여줘야 하나요?">RUL / SoH 차이</button>
          <button class="example" data-question="배터리 RUL 모델에서 uncertainty band를 함께 보여주는 이유는 무엇인가요?">불확실성 표시</button>
          <button class="example" data-question="배터리 모니터링 앱에서 precomputed 결과와 live reinference 결과를 왜 구분해야 하나요?">추론 결과 구분</button>
          <button class="example" data-question="배터리 데이터 전처리에서 capacity, 전압, 전류, 온도 feature는 어떤 점을 확인해야 하나요?">전처리 체크리스트</button>
          <button class="example" data-question="Battery RUL 프로젝트를 다음 PoC로 확장한다면 어떤 실험을 먼저 설계해야 하나요?">다음 PoC 방향</button>
          <button class="example" data-question="운영 중인 배터리의 RUL 예측 결과를 점검할 때 어떤 항목을 우선 확인해야 하나요?">운영 점검 요약</button>
          <button class="example" data-question="RUL 예측 결과가 갑자기 흔들릴 때 데이터와 모델 관점에서 어떤 원인을 확인해야 하나요?">예측 이상 원인</button>
        </div>
        <div class="input-row">
          <textarea id="question" placeholder="예: 초기 cycle 기반 RUL 예측에서 데이터 누수를 막으려면 무엇을 확인해야 하나요?"></textarea>
          <button id="ask">검색</button>
        </div>
      </section>
      <aside class="panel">
        <h2>문서 업로드</h2>
        <p class="note">기본 배터리 RUL 샘플 문서가 이미 색인되어 있어 업로드 없이도 검색할 수 있습니다. 논문 요약, 실험 기록, README, 운영 메모를 추가하면 같은 방식으로 근거 검색에 포함됩니다.</p>
        <input id="files" type="file" multiple accept=".pdf,.txt,.md" />
        <button id="upload" class="secondary">벡터DB에 추가</button>
        <div id="status" class="status"></div>
        <div class="sources">
          <h2>Indexed Sources</h2>
          <ul id="sources"></ul>
        </div>
        <div class="service-note">
          <h2>Service Use Case</h2>
          <p class="note">Battery RUL AI Inference System을 보조하는 RAG 기반 Research Copilot MVP입니다. 현재는 근거 검색과 답변 생성을 수행하며, 향후 운영 점검 요약, 데이터 품질 체크리스트, 예측 이상 원인 분석, 다음 실험 설계 같은 agentic workflow로 확장할 수 있습니다.</p>
        </div>
        <div class="service-note">
          <h2>RAG Pipeline</h2>
          <div class="capability-list">
            <div class="capability">
              <strong>1. Retrieval</strong>
              질문과 유사한 기술문서 chunk를 먼저 검색합니다.
            </div>
            <div class="capability">
              <strong>2. Grounded Generation</strong>
              검색된 근거를 LLM prompt에 넣어 답변을 생성합니다.
            </div>
            <div class="capability">
              <strong>3. Enterprise Use</strong>
              사내 기술문서, 실험 메모, PoC 자료 검색 서비스로 확장할 수 있습니다.
            </div>
          </div>
        </div>
      </aside>
    </div>
  </main>
  <script>
    const chat = document.getElementById("chat");
    const question = document.getElementById("question");
    const ask = document.getElementById("ask");
    const upload = document.getElementById("upload");
    const files = document.getElementById("files");
    const status = document.getElementById("status");
    const sources = document.getElementById("sources");

    function escapeHtml(text) {
      return text
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
    }

    function renderMarkdownLite(text) {
      const escaped = escapeHtml(text);
      return escaped
        .replace(/\\*\\*(.+?)\\*\\*/g, "<strong>$1</strong>")
        .split(/\\n{2,}/)
        .map((paragraph) => `<p>${paragraph.replaceAll("\\n", "<br>")}</p>`)
        .join("");
    }

    function addMessage(role, text) {
      const div = document.createElement("div");
      div.className = `message ${role}`;
      div.textContent = text;
      chat.appendChild(div);
      chat.scrollTop = chat.scrollHeight;
    }

    function addAnswer(answer, retrievedSources) {
      const div = document.createElement("div");
      div.className = "message assistant";
      const sourceCards = retrievedSources.map((source) => `
        <div class="source-card">
          <div class="source-name">${escapeHtml(source.source)}#${source.chunk_index}</div>
          <div class="source-meta">Similarity distance ${source.distance?.toFixed(3) ?? "n/a"}</div>
        </div>
      `).join("");
      div.innerHTML = `
        <div class="result-header">
          <span>Grounded Answer</span>
          <span>${retrievedSources.length} sources</span>
        </div>
        <div>${renderMarkdownLite(answer)}</div>
        <div class="source-grid">${sourceCards}</div>
      `;
      chat.appendChild(div);
      chat.scrollTop = chat.scrollHeight;
    }

    function resetChat() {
      chat.innerHTML = "";
    }

    async function loadSources() {
      const res = await fetch("/api/documents");
      const data = await res.json();
      sources.innerHTML = "";
      data.documents.forEach((name) => {
        const li = document.createElement("li");
        li.textContent = name;
        sources.appendChild(li);
      });
    }

    async function askQuestion() {
      const text = question.value.trim();
      if (!text) return;
      resetChat();
      addMessage("user", text);
      question.value = "";
      ask.disabled = true;
      ask.textContent = "검색 중";
      try {
        const res = await fetch("/api/ask", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ question: text })
        });
        const data = await res.json();
        addAnswer(data.answer, data.sources);
      } catch (error) {
        addMessage("assistant", `오류: ${error.message}`);
      } finally {
        ask.disabled = false;
        ask.textContent = "검색";
      }
    }

    async function uploadFiles() {
      if (!files.files.length) {
        status.textContent = "업로드할 파일을 선택해 주세요.";
        return;
      }
      const form = new FormData();
      Array.from(files.files).forEach((file) => form.append("files", file));
      status.textContent = "저장 중...";
      const res = await fetch("/api/ingest", { method: "POST", body: form });
      const data = await res.json();
      status.textContent = data.detail || `${data.files.length}개 문서에서 ${data.chunks_added}개 chunk 저장`;
      await loadSources();
    }

    ask.addEventListener("click", askQuestion);
    question.addEventListener("keydown", (event) => {
      if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        askQuestion();
      }
    });
    upload.addEventListener("click", uploadFiles);
    document.querySelectorAll(".example").forEach((button) => {
      button.addEventListener("click", () => {
        question.value = button.dataset.question;
        question.focus();
      });
    });
    loadSources();
  </script>
</body>
</html>
"""


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "7860")))
