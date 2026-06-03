# Deployment and Operations Notes

이 문서는 Battery RUL AI Inference System을 운영 가능한 서비스로 연결할 때 확인해야 할 engineering notes를 정리한다.

## Backend and data access

Backend는 FastAPI 기반으로 inference, degradation monitoring, explainability, export endpoint를 제공한다. Feature data는 CSV/Parquet 형태로 저장되고 DuckDB를 통해 조회할 수 있다. Precomputed inference result는 JSON payload로 로드해 dashboard 초기 응답 속도를 개선한다.

## Dashboard operations

Frontend dashboard는 React/Vite 기반으로 prediction curve, support/query split, uncertainty band, degradation tabs, comparison view, explainability view, live reinference state를 렌더링한다. 사용자가 battery와 observation ratio를 바꾸면 backend payload와 frontend state가 일관되게 갱신되어야 한다.

## Deployment path handling

로컬 환경과 Docker/Hugging Face Spaces 환경에서는 checkpoint, data file, runtime path가 달라질 수 있다. 따라서 backend settings와 runtime entrypoint에서 deployment-aware path handling이 필요하다. 누락 파일이나 경로 mismatch는 500 error로 이어질 수 있으므로 fallback behavior와 diagnostics를 함께 설계한다.

## CPU live reinference

Hugging Face Spaces 같은 CPU-only 환경에서는 live reinference가 오래 걸릴 수 있다. 따라서 빠른 초기 로딩에는 precomputed cache를 사용하고, 상세 분석이 필요할 때만 on-demand live reinference를 실행하는 구조가 적합하다. 이때 timeout, loading state, baseline restore 기능을 함께 고려한다.

## Operational risk

운영자는 단일 RUL prediction보다 capacity trend, DCR/impedance, temperature stress, current stress, LLI/LAM proxy signal, uncertainty band를 함께 검토해야 한다. RAG Copilot은 이러한 운영 기준을 문서로 검색해 예측 이상 원인과 데이터 품질 점검 항목을 빠르게 확인하도록 돕는다.
