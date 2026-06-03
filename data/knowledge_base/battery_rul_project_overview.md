# Battery RUL Project Overview

이 문서는 Battery RUL AI Inference System의 운영 관점 개요를 정리한다. 이 시스템은 NASA battery cycle data를 기반으로 초기 cycle 관측값에서 배터리 잔여수명(RUL)을 예측하고, 예측 결과를 API와 대시보드로 연결하는 것을 목표로 한다.

## Operational problem

실제 배터리 운영 환경에서는 새 배터리의 전체 수명 데이터를 처음부터 알 수 없다. 따라서 전체 degradation trajectory가 확보된 뒤 모델을 평가하는 것만으로는 운영 활용성을 설명하기 어렵다. 초기 일부 cycle만 관측한 상태에서 장기 RUL과 degradation trend를 추정할 수 있어야 한다.

처음에는 NASA Battery Data Set의 B0005부터 B0056까지 가능한 모든 리튬이온 배터리 데이터를 하나의 모델로 학습시키려 했다. 그러나 배터리 그룹별 실험 조건, 충방전 프로토콜, cutoff voltage, 온도 조건, EOL 기준, 실험 종료 사유가 서로 달라 단순 통합이 어렵다는 점을 확인했다. B0005, B0006, B0007, B0018은 논문에서 자주 활용되는 benchmark set에 가까웠지만, 다른 그룹에는 square wave loading, 저온 조건, 다른 EOL 기준, 실험 중단 이슈가 섞여 있었다.

서로 다른 실험 조건과 열화 패턴을 그대로 섞으면 모델이 배터리의 열화 특성보다 실험 환경의 차이를 먼저 학습할 수 있다. 따라서 전체 데이터를 무작정 사용하는 것보다 그룹 차이, 데이터 누수 가능성, 초기 관측 비율, 배터리 단위 검증 구조를 함께 고려해야 한다.

이러한 확인을 통해 데이터 누수를 막을 수 있고, 초기 cycle 기반 RUL 예측의 정확성을 향상할 수 있다.

## System goal

목표는 모델 실험 결과를 노트북 내부에 남겨두지 않고, 사용자가 확인 가능한 AI inference application으로 연결하는 것이다. 예측값, SoH, degradation trend, uncertainty band, live reinference 결과를 dashboard에서 조회할 수 있어야 한다.

프로젝트의 핵심 목표는 세 가지였다. 첫째, 기존 논문들이 주로 다룬 일부 benchmark battery만 반복하지 않고 더 넓은 배터리군으로 범용 예측 가능성을 검토하는 것. 둘째, 같은 battery의 앞뒤 cycle이 학습과 검증에 함께 들어가 성능이 과장되는 데이터 누수를 피하는 것. 셋째, 새 배터리의 초기 일부 cycle만으로 먼 미래의 RUL trajectory를 예측하는 것이다. 이 목표는 BMS 모니터링 환경에서 새로 유입되는 배터리의 수명 위험을 조기에 파악하는 상황을 가정한다.

## Main components

시스템은 battery domain feature, sequence modeling, inference API, dashboard, deployment flow를 연결한다. 데이터 파이프라인은 NASA battery cycle data를 domain-informed feature engineering으로 변환하고, support/query task를 구성해 few-shot RUL prediction을 수행한다.

학습 초기에는 LSTM, GRU, CNN-LSTM, Transformer, ResNet1D, XGBoost 등 여러 모델을 비교했다. 이후 capacity와 discharge feature만으로는 배터리별 열화 차이를 충분히 설명하기 어렵다고 판단해 impedance, DCR, temperature, C-rate, IR drop 등 물리·전기화학적 feature를 검토했다. 정상열화그룹, 급격열화그룹, 심각한이상그룹, 이상 수평선 그룹을 시각화하며 데이터 특성을 확인했고, 최종적으로는 배터리 단위 support/query task를 구성해 전체 battery group에서 few-shot adaptation 가능성을 확인하는 방향으로 발전시켰다.

## Service interpretation

이 프로젝트는 단일 예측 숫자보다 운영자가 검토할 수 있는 흐름을 중요하게 둔다. 사용자는 특정 battery와 observation ratio를 선택해 예측 curve, uncertainty, degradation evidence, feature importance를 함께 확인한다. 따라서 RAG Copilot은 모델 설계 의도, 데이터 품질 기준, 예측 결과 해석 기준을 검색 가능한 운영 문서로 제공해야 한다.

운영 관점에서는 예측값이 잘 맞는지보다, 왜 그렇게 예측했는지와 어떤 조건에서 예측 불확실성이 커지는지를 함께 확인해야 한다. 따라서 RAG Copilot은 데이터셋 구성 이유, 실험 조건 차이, feature 선택 근거, live reinference와 precomputed 결과의 차이, uncertainty band 해석 기준을 검색 가능한 지식으로 제공한다.
