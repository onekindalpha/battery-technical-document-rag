# Battery Monitoring Application Notes

배터리 RUL 모델은 노트북의 성능 지표만으로 운영 활용성을 설명하기 어렵다. 사용자가 특정 배터리의 상태를 조회하고, 열화 추세와 예측 불확실성을 함께 확인할 수 있어야 한다.

## Inference flow

대시보드에서 배터리를 선택하면 API가 해당 배터리의 feature를 조회하고 추론 결과를 반환한다. 응답에는 RUL 예측값, SoH, degradation trend, uncertainty band를 포함할 수 있다. 미리 계산한 결과와 live reinference 결과는 응답 구조와 화면에서 구분해 표시하는 편이 좋다.

## Explainability and uncertainty

단일 예측값만 보여주면 사용자가 결과의 신뢰 수준을 판단하기 어렵다. uncertainty band를 함께 제공하고, 주요 feature 변화와 예측 결과를 연결해 확인할 수 있도록 구성한다. Explainability는 복잡한 모델을 단순화하는 장식이 아니라, 사용자가 결과를 검토할 수 있도록 돕는 장치다.

## Deployment

모델, API, feature store, dashboard를 분리하면 각 계층의 문제를 확인하기 쉽다. Docker 기반 배포는 로컬 환경과 공개 데모 환경의 차이를 줄이는 데 도움이 된다. 공개 데모에서는 응답 지연, 초기 로딩 시간, 외부 API 의존성을 별도로 확인해야 한다.
