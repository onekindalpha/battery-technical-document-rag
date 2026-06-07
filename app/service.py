from __future__ import annotations

import shutil
import time
import hashlib
from pathlib import Path

from app.config import settings
from app.document_processor import SUPPORTED_EXTENSIONS, create_chunks
from app.llm_service import LLMService
from app.request_log import RequestLog
from app.retrieval_eval import evaluate_retrieval_cases
from app.schemas import (
    AskResponse,
    IngestResponse,
    RetrievalEvalRequest,
    RetrievalEvalResponse,
)
from app.vector_store import VectorStore


def normalize_question(question: str) -> str:
    return " ".join(question.strip().split()).lower()


FAQ_ANSWERS = {
    normalize_question("초기 cycle 기반 RUL 예측에서 데이터 누수를 막으려면 무엇을 확인해야 하나요?"): (
        "초기 cycle 기반 RUL 예측에서 데이터 누수를 막으려면 다음 항목을 함께 확인해야 합니다.\n\n"
        "1. **Cycle sequence**: 각 battery의 cycle 번호가 단조 증가하는지, 누락되거나 중복된 cycle이 있는지 확인해야 합니다. "
        "초기 일부 cycle만 보고 장기 RUL을 예측하는 구조에서는 cycle 순서가 깨지면 입력 윈도우와 label 관계가 흔들릴 수 있습니다. "
        "[battery_data_quality_checklist.md#0]\n"
        "2. **Train-test contamination**: 같은 battery의 앞쪽 cycle과 뒤쪽 cycle이 train과 validation/test에 동시에 들어가면 "
        "모델이 새로운 battery를 예측한 것이 아니라 이미 본 battery의 후속 패턴을 맞춘 결과가 될 수 있습니다. "
        "따라서 battery-level split이나 support/query 구성을 명확히 기록해야 합니다. [battery_data_quality_checklist.md#0]\n"
        "3. **Group difference**: 서로 다른 실험 조건과 열화 패턴을 그대로 섞으면 모델이 배터리의 일반적인 열화 특성보다 "
        "실험 환경의 차이를 먼저 학습할 수 있습니다. 따라서 group 차이, 초기 관측 비율, 검증 구조를 함께 고려해야 합니다. "
        "[battery_rul_project_overview.md#0]\n"
        "4. **Observation ratio**: 초기 몇 percent의 cycle을 보고 예측했는지 기록해야 합니다. r_ratio가 달라지면 같은 모델이라도 "
        "운영 활용성과 난이도가 크게 달라집니다. [battery_rul_basics.md#1]\n\n"
        "이런 점검을 통해 데이터 누수 가능성을 줄이고, 초기 cycle 기반 RUL 예측 결과를 더 방어 가능하게 만들 수 있습니다."
    ),
    normalize_question("RUL과 SoH는 무엇이 다르고 대시보드에서는 어떻게 보여줘야 하나요?"): (
        "RUL과 SoH는 모두 배터리 상태를 설명하지만, 보는 방향이 다릅니다.\n\n"
        "1. **RUL**: Remaining Useful Life는 배터리가 end-of-life threshold에 도달하기 전까지 남은 cycle 또는 사용 가능 기간을 의미합니다. "
        "즉 앞으로 얼마나 더 사용할 수 있는지를 예측하는 지표입니다. [battery_rul_basics.md#0]\n"
        "2. **SoH**: State of Health는 현재 capacity가 초기 capacity 대비 어느 정도 남아 있는지를 나타내는 상태 지표입니다. "
        "즉 현재 배터리의 열화 정도를 보여주는 지표입니다. [battery_rul_basics.md#0]\n"
        "3. **Dashboard 표현**: 운영 화면에서는 RUL 예측값만 단독으로 보여주기보다 SoH, degradation trend, uncertainty band를 함께 보여주는 편이 좋습니다. "
        "그래야 사용자가 현재 상태와 미래 예측을 동시에 검토할 수 있습니다. [battery_monitoring_application.md#0]\n"
        "4. **운영 판단**: SoH가 낮아지는 흐름과 RUL 예측값이 서로 어긋나는 경우에는 입력 feature, 관측 비율, 추론 결과 source를 다시 확인해야 합니다. "
        "[battery_monitoring_application.md#0]"
    ),
    normalize_question("배터리 RUL 모델에서 uncertainty band를 함께 보여주는 이유는 무엇인가요?"): (
        "배터리 RUL 모델에서 uncertainty band를 함께 보여주는 이유는 단일 예측값만으로는 운영 판단이 어렵기 때문입니다.\n\n"
        "1. **Point estimate의 한계**: RUL 예측값 하나만 보여주면 사용자는 그 결과가 얼마나 안정적인지 판단하기 어렵습니다. "
        "특히 초기 cycle만 관측하는 조기 예측에서는 예측 불확실성이 커질 수 있습니다. [battery_rul_basics.md#1]\n"
        "2. **배터리별 차이**: 배터리마다 실험 조건, 충방전 패턴, 열화 속도가 다르기 때문에 같은 RUL 값이라도 신뢰 수준이 다를 수 있습니다. "
        "[battery_data_quality_checklist.md#0]\n"
        "3. **운영 의사결정**: uncertainty band는 예측값 주변의 위험 범위를 보여주어, 사용자가 단순 수치가 아니라 신뢰 수준까지 함께 검토하도록 돕습니다. "
        "[battery_monitoring_application.md#0]\n"
        "4. **설명 가능성**: 대시보드에서 degradation trend와 uncertainty band를 함께 제공하면 모델 결과를 더 쉽게 검토하고, "
        "이상 예측이 발생했을 때 원인을 추적하기도 수월합니다. [battery_monitoring_application.md#0]"
    ),
    normalize_question("배터리 모니터링 앱에서 precomputed 결과와 live reinference 결과를 왜 구분해야 하나요?"): (
        "배터리 모니터링 앱에서 precomputed 결과와 live reinference 결과를 구분하는 이유는 응답 속도와 검증 가능성을 함께 확보하기 위해서입니다.\n\n"
        "1. **Precomputed result**: 미리 계산해둔 결과를 불러오는 방식입니다. 데모나 운영 화면에서 초기 로딩을 빠르게 하고, "
        "사용자가 즉시 RUL, SoH, degradation trend를 확인할 수 있게 합니다. [deployment_and_operations_notes.md#0]\n"
        "2. **Live reinference**: 사용자가 선택한 battery와 observation ratio 기준으로 모델 추론을 다시 수행하는 흐름입니다. "
        "실제 입력 조건에서 모델이 어떻게 동작하는지 확인할 수 있습니다. [battery_monitoring_application.md#0]\n"
        "3. **Source tracking**: 두 결과를 구분하면 현재 화면의 값이 저장된 baseline인지, 방금 재추론한 값인지 명확히 알 수 있습니다. "
        "운영 환경에서는 이 구분이 결과 검토와 장애 대응에 중요합니다. [deployment_and_operations_notes.md#0]\n"
        "4. **서비스 안정성**: precomputed 결과는 빠른 접근성을 제공하고, live reinference는 검증 가능성을 제공합니다. "
        "둘을 함께 두면 포트폴리오 데모와 실제 서비스 구조 모두를 설명하기 좋습니다."
    ),
    normalize_question("배터리 데이터 전처리에서 capacity, 전압, 전류, 온도 feature는 어떤 점을 확인해야 하나요?"): (
        "배터리 데이터 전처리에서는 feature 값 자체보다, 그 값이 RUL 예측에 사용할 수 있는 품질인지 먼저 확인해야 합니다.\n\n"
        "1. **Capacity**: capacity 변화가 열화 추세와 일관되는지 확인해야 합니다. 비정상적인 급증이나 급락이 있으면 측정 오류인지 실제 열화 신호인지 구분해야 합니다. "
        "[battery_data_quality_checklist.md#0]\n"
        "2. **Voltage/current/temperature**: 전압, 전류, 온도 feature는 결측값, 비정상 범위, 측정 간격 차이를 확인해야 합니다. "
        "이 feature들은 배터리 상태와 실험 조건을 함께 반영하므로 단순 평균값만 보는 것보다 변화 패턴을 함께 보는 편이 좋습니다. "
        "[modeling_and_inference_design.md#0]\n"
        "3. **Cycle alignment**: feature가 같은 cycle 기준으로 정렬되어 있는지 확인해야 합니다. cycle 순서가 어긋나면 입력 feature와 RUL label의 관계가 깨질 수 있습니다. "
        "[battery_data_quality_checklist.md#0]\n"
        "4. **Group difference**: 배터리별 실험 조건, EOL 기준, 열화 패턴이 다를 수 있으므로 모든 데이터를 무작정 섞기보다 데이터 품질과 group 차이를 함께 점검해야 합니다. "
        "[battery_rul_project_overview.md#0]"
    ),
    normalize_question("Battery RUL 프로젝트를 다음 PoC로 확장한다면 어떤 실험을 먼저 설계해야 하나요?"): (
        "Battery RUL 프로젝트를 다음 PoC로 확장한다면, 모델 성능만 추가로 비교하기보다 운영 적용 가능성을 확인하는 실험을 먼저 설계하는 것이 좋습니다.\n\n"
        "1. **External validation**: 새로운 battery group이나 외부 dataset을 대상으로 초기 관측 비율별 RUL 예측 성능을 비교합니다. "
        "이렇게 해야 모델이 특정 benchmark에만 맞춰진 것인지 확인할 수 있습니다. [modeling_and_inference_design.md#0]\n"
        "2. **Observation ratio test**: r_ratio 0.2, 0.3 등 초기 관측 비율을 바꿔가며 예측 성능과 uncertainty 변화를 기록합니다. "
        "운영 환경에서는 얼마나 이른 시점에 예측할 수 있는지가 중요합니다. [battery_rul_basics.md#1]\n"
        "3. **Live inference check**: precomputed 결과와 live reinference 결과를 비교해, 실제 API 추론 흐름에서도 결과가 안정적으로 나오는지 확인합니다. "
        "[deployment_and_operations_notes.md#0]\n"
        "4. **Operation review**: RUL 예측값, SoH, degradation trend, uncertainty band를 함께 보여주고, 예측 이상 발생 시 원인 점검 체크리스트를 연결합니다. "
        "이 흐름이 구축되면 단순 모델 실험에서 운영형 AI 서비스 PoC로 확장할 수 있습니다."
    ),
    normalize_question("운영 중인 배터리의 RUL 예측 결과를 점검할 때 어떤 항목을 우선 확인해야 하나요?"): (
        "운영 중인 배터리의 RUL 예측 결과를 점검할 때는 예측값 하나만 보지 말고, 결과가 나온 조건과 신뢰 수준을 함께 확인해야 합니다.\n\n"
        "1. **RUL/SoH consistency**: RUL 예측값과 SoH, degradation trend가 서로 자연스럽게 연결되는지 확인합니다. "
        "SoH는 낮아지는데 RUL만 비정상적으로 길게 나오면 입력 데이터나 모델 추론 조건을 다시 봐야 합니다. [battery_monitoring_application.md#0]\n"
        "2. **Uncertainty band**: uncertainty band가 갑자기 넓어졌는지 확인합니다. 예측값은 비슷해도 불확실성이 커지면 운영 판단에서 보수적으로 접근해야 합니다. "
        "[battery_rul_basics.md#1]\n"
        "3. **Input feature quality**: cycle sequence, capacity 변화, 전압·전류·온도·임피던스 feature의 결측이나 이상값을 확인합니다. "
        "[battery_data_quality_checklist.md#0]\n"
        "4. **Inference source**: 현재 결과가 precomputed baseline인지 live reinference 결과인지 확인합니다. "
        "두 결과가 크게 다르면 API 입력 조건, feature 조회, 모델 payload를 다시 점검해야 합니다. [deployment_and_operations_notes.md#0]"
    ),
    normalize_question("RUL 예측 결과가 갑자기 흔들릴 때 데이터와 모델 관점에서 어떤 원인을 확인해야 하나요?"): (
        "RUL 예측 결과가 갑자기 흔들릴 때는 데이터 문제와 모델 추론 조건을 나누어 확인하는 것이 좋습니다.\n\n"
        "1. **Data quality**: cycle 누락·중복, capacity 급변, 전압·전류·온도 feature의 결측이나 이상값이 있는지 확인합니다. "
        "입력 feature가 불안정하면 모델 예측도 흔들릴 수 있습니다. [battery_data_quality_checklist.md#0]\n"
        "2. **Experimental condition**: 특정 battery group의 실험 조건이나 EOL 기준이 다른지 확인합니다. "
        "서로 다른 조건이 섞이면 모델이 열화 특성보다 실험 환경 차이에 민감하게 반응할 수 있습니다. [battery_rul_project_overview.md#0]\n"
        "3. **Inference setting**: observation ratio, support/query 구성, battery 선택 조건이 바뀌었는지 확인합니다. "
        "초기 cycle 기반 예측에서는 관측 구간이 조금만 달라져도 예측 궤적이 달라질 수 있습니다. [modeling_and_inference_design.md#0]\n"
        "4. **Result comparison**: precomputed 결과와 live reinference 결과를 비교해 차이가 큰 경우 API 입력, feature 조회, 모델 payload를 순서대로 점검합니다. "
        "[deployment_and_operations_notes.md#0]"
    ),
}


class DocumentRAGService:
    def __init__(self):
        self.vector_store = VectorStore(
            settings.vector_store_path,
            settings.collection_name,
            settings.embedding_model,
            settings.vector_backend,
        )
        self.llm = LLMService(settings.groq_api_key, settings.groq_model)
        self.request_log = RequestLog(settings.request_log_db_path)
        self._answer_cache: dict[tuple[object, ...], AskResponse] = {}
        self.redis_client = self._connect_redis(settings.redis_url)
        settings.upload_path.mkdir(parents=True, exist_ok=True)

    def ingest_paths(self, paths: list[Path], copy_uploads: bool = True) -> IngestResponse:
        files: list[str] = []
        chunks_added = 0
        for source_path in paths:
            if source_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
                raise ValueError(f"Unsupported file type: {source_path.suffix}")
            target_path = settings.upload_path / source_path.name
            if copy_uploads and source_path.resolve() != target_path.resolve():
                shutil.copy2(source_path, target_path)
            else:
                target_path = source_path
            chunks_added += self.vector_store.add(
                create_chunks(target_path, settings.chunk_size, settings.chunk_overlap)
            )
            files.append(target_path.name)
        self._answer_cache.clear()
        return IngestResponse(files=files, chunks_added=chunks_added)

    def ingest_knowledge_base(self) -> None:
        existing_sources = set(self.vector_store.sources())
        paths = [
            path
            for path in sorted(settings.knowledge_base_path.glob("*"))
            if path.suffix.lower() in SUPPORTED_EXTENSIONS and path.name not in existing_sources
        ]
        if paths:
            self.ingest_paths(paths, copy_uploads=False)

    def ask(self, question: str, top_k: int | None = None) -> AskResponse:
        started_at = time.perf_counter()
        effective_top_k = top_k or settings.top_k
        sources = self._diversify_sources(
            self.vector_store.search(question, max(effective_top_k, settings.top_k + 2)),
            effective_top_k,
        )
        cache_key = self._cache_key(question, effective_top_k, sources)
        cached_response = self._get_cached_response(cache_key)
        if cached_response:
            response = self._with_response_time(cached_response, started_at)
            self._record_request(question, response)
            return response

        faq_answer = FAQ_ANSWERS.get(normalize_question(question))
        if faq_answer:
            response = AskResponse(
                answer=faq_answer,
                sources=sources,
                mode="faq-cache",
                response_time_ms=self._elapsed_ms(started_at),
            )
            self._set_cached_response(cache_key, response)
            self._record_request(question, response)
            return response

        answer, mode = self.llm.answer(question, sources)
        response = AskResponse(
            answer=answer,
            sources=sources,
            mode=mode,
            response_time_ms=self._elapsed_ms(started_at),
        )
        self._set_cached_response(cache_key, response)
        self._record_request(question, response)
        return response

    def sources(self) -> list[str]:
        return self.vector_store.sources()

    def evaluate_retrieval(self, request: RetrievalEvalRequest) -> RetrievalEvalResponse:
        return evaluate_retrieval_cases(
            request.cases,
            request.top_k,
            self.vector_store.search,
        )

    @staticmethod
    def _diversify_sources(sources, limit: int):
        selected = []
        seen_sources = set()

        for source in sources:
            if source.source in seen_sources:
                continue
            selected.append(source)
            seen_sources.add(source.source)
            if len(selected) >= limit:
                return selected

        for source in sources:
            if source in selected:
                continue
            selected.append(source)
            if len(selected) >= limit:
                return selected

        return selected

    @staticmethod
    def _cache_key(question: str, top_k: int, sources) -> tuple[object, ...]:
        source_signature = tuple(
            (source.source, source.chunk_index, round(source.distance or 0.0, 4))
            for source in sources
        )
        return (normalize_question(question), top_k, source_signature)

    @staticmethod
    def _elapsed_ms(started_at: float) -> float:
        return round((time.perf_counter() - started_at) * 1000, 1)

    def _with_response_time(self, response: AskResponse, started_at: float) -> AskResponse:
        return response.model_copy(
            update={
                "mode": f"{response.mode}-cached"
                if not response.mode.endswith("-cached")
                else response.mode,
                "response_time_ms": self._elapsed_ms(started_at),
            }
        )

    def _record_request(self, question: str, response: AskResponse) -> None:
        self.request_log.record(
            question=question,
            mode=response.mode,
            response_time_ms=response.response_time_ms,
            source_count=len(response.sources),
        )

    @staticmethod
    def _connect_redis(redis_url: str):
        if not redis_url:
            return None
        try:
            import redis

            client = redis.Redis.from_url(redis_url, decode_responses=True)
            client.ping()
            return client
        except Exception:
            return None

    def _get_cached_response(self, cache_key: tuple[object, ...]) -> AskResponse | None:
        if cache_key in self._answer_cache:
            return self._answer_cache[cache_key]
        if not self.redis_client:
            return None
        payload = self.redis_client.get(self._redis_key(cache_key))
        if not payload:
            return None
        return AskResponse.model_validate_json(payload)

    def _set_cached_response(self, cache_key: tuple[object, ...], response: AskResponse) -> None:
        self._answer_cache[cache_key] = response
        if self.redis_client:
            self.redis_client.setex(self._redis_key(cache_key), 3600, response.model_dump_json())

    @staticmethod
    def _redis_key(cache_key: tuple[object, ...]) -> str:
        raw_key = repr(cache_key).encode("utf-8")
        return f"rag-answer:{hashlib.sha256(raw_key).hexdigest()}"


service = DocumentRAGService()
