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
    description="Domain RAG portfolio for battery technical documents.",
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
  <title>Battery Technical Document RAG Assistant</title>
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
      white-space: pre-wrap;
      line-height: 1.55;
    }
    .message.user {
      border-color: rgba(125, 167, 255, 0.55);
    }
    .message.assistant {
      border-color: rgba(70, 194, 163, 0.55);
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
    <h1>Battery Technical Document RAG Assistant</h1>
    <p class="subtitle">Battery RUL 문서를 검색하고, 근거 chunk와 함께 답변을 확인합니다.</p>
    <div class="layout">
      <section>
        <div id="chat" class="panel chat"></div>
        <div class="input-row">
          <textarea id="question" placeholder="예: 초기 cycle 기반 RUL 예측에서 데이터 누수를 막으려면 무엇을 확인해야 하나요?"></textarea>
          <button id="ask">검색</button>
        </div>
      </section>
      <aside class="panel">
        <h2>문서 업로드</h2>
        <input id="files" type="file" multiple accept=".pdf,.txt,.md" />
        <button id="upload" class="secondary">벡터DB에 추가</button>
        <div id="status" class="status"></div>
        <div class="sources">
          <h2>Indexed Sources</h2>
          <ul id="sources"></ul>
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

    function addMessage(role, text) {
      const div = document.createElement("div");
      div.className = `message ${role}`;
      div.textContent = text;
      chat.appendChild(div);
      chat.scrollTop = chat.scrollHeight;
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
        const labels = data.sources.map((s) => `- ${s.source}#${s.chunk_index} (${s.distance?.toFixed(3) ?? "n/a"})`).join("\\n");
        addMessage("assistant", `${data.answer}\\n\\n검색 출처\\n${labels}`);
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
    loadSources();
  </script>
</body>
</html>
"""


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "7860")))
