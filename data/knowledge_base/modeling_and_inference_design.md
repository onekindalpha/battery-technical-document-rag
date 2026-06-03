# Modeling and Inference Design Notes

이 문서는 Battery RUL AI Inference System의 모델링과 추론 설계 판단을 정리한다. 핵심 방향은 제한된 초기 cycle 정보만으로 새 배터리에 적응하고, 예측값과 함께 불확실성을 제공하는 것이다.

## Few-shot RUL prediction

초기 cycle 기반 RUL 예측은 few-shot prediction 문제로 볼 수 있다. Support set은 초기에 관측된 cycle 구간이고, query set은 앞으로 예측해야 할 미래 cycle 구간이다. 이 구조는 실제 운영 환경에서 전체 수명 데이터를 미리 확보할 수 없다는 조건을 반영한다.

## CEEMDAN-Transformer-DNN backbone

CEEMDAN 기반 decomposition feature는 capacity degradation이나 sensor signal의 변화 패턴을 분해해 sequence representation에 반영하기 위한 구성이다. Transformer encoder는 시간에 따른 degradation pattern을 포착하고, DNN prediction head는 최종 RUL prediction을 생성한다.

CEEMDAN-Transformer-DNN 구조는 용량 시계열의 국소 변동 성분과 장기 열화 추세를 나누어 보는 접근이 유용하다고 판단해 참고했다. 단순히 모델명을 가져오기보다, noisy battery degradation signal을 분해하고 sequence model로 학습하는 설계 방향을 Battery RUL 프로젝트의 backbone으로 활용했다.

## Research references as design inputs

참고 연구는 논문 원문을 재현하기 위한 것이 아니라, 프로젝트의 문제 정의와 설계 방향을 정하는 데 사용했다. Stanford와 Michigan 계열 battery aging 연구에서는 capacity 감소만이 아니라 temperature, impedance, DCR, stress, usage pattern 같은 물리·전기화학적 feature가 RUL 예측에 중요하다는 관점을 참고했다. 이 관점은 DCR growth, impedance growth, C-rate, IR drop, temperature statistics 같은 feature를 별도로 검토하게 만든 배경이 되었다.

Few-shot meta-learning 연구는 새 배터리의 전체 수명 데이터를 알 수 없는 운영 조건을 반영하기 위해 참고했다. 실제 BMS 환경에서는 초기 cycle만 관측되는 경우가 많으므로, support/query 구조를 통해 초기 관측 구간에서 미래 RUL trajectory를 추정하는 방식이 필요하다고 판단했다.

## BMAML-SVGD-style adaptation

BMAML-SVGD-style adaptation은 제한된 support data에서 battery별 특성에 적응하고, 여러 prediction particle을 통해 uncertainty-aware RUL prediction을 만들기 위한 설계다. 단일 point estimate만 제공하면 사용자가 예측 위험을 판단하기 어렵기 때문에, uncertainty band를 함께 제공한다.

BMAML-SVGD-style adaptation을 붙인 이유는 배터리별 특성과 열화 패턴이 다르고, 새 배터리에 대해 전체 수명 데이터를 미리 알 수 없다는 문제 때문이다. 초기 cycle 일부만 support data로 사용해 새로운 battery task에 빠르게 적응하고, Bayesian 관점의 uncertainty estimation을 통해 예측 위험을 함께 보여주는 방향으로 설계했다.

이 구조는 모든 배터리 종류를 완전히 일반화했다는 의미가 아니다. 목표는 NASA B0005~B0056 리튬이온 배터리군에서 관찰한 도메인 차이를 고려하면서, 처음 보는 배터리에 대해서도 최소한의 초기 관측 데이터로 장기 RUL trajectory를 예측할 수 있는지 검토하는 것이었다.

## Inference flow

대시보드에는 두 가지 추론 흐름이 존재한다. 빠른 초기 응답을 위해 precomputed prediction payload를 로드하고, 사용자가 더 깊은 분석을 원할 때 live reinference를 실행한다. Live reinference 결과는 prediction curve, uncertainty, confidence metric, dashboard state를 함께 갱신해야 한다.

공개 데모에서는 로딩 시간을 줄이기 위해 기본적으로 precomputed result를 먼저 표시한다. 사용자가 live reinference 버튼을 누르면 현재 선택한 battery와 observation ratio 기준으로 재추론을 수행한다. Meta-learning 기반 few-shot 설정에서는 초기 구간에서 support sample이 선택되므로, 고정된 단일 예측만 보여주는 방식보다 재추론 결과의 변동성과 uncertainty를 함께 확인하는 것이 중요하다.

## Evaluation note

대표 실험 설정에서는 r_ratio 0.20 조건을 사용한다. 이 설정은 초기 관측 비율을 명시하고, support/query 구성과 battery-level split을 함께 기록해야 재현 가능한 평가가 된다. 성능 수치는 state-of-the-art claim이 아니라 구현된 inference pipeline의 고정 실험 조건 결과로 해석한다.

모델 실험 과정에서는 200 epoch 학습 시간이 길고, RMSE가 특정 수준에서 수렴하는 문제가 있었다. 단시간에 여러 가중치와 설정을 비교하기 위해 Ray Tune과 ASHA 방식의 early stopping을 활용해 성능이 낮은 trial을 조기에 중단하고, 더 유망한 설정을 빠르게 탐색하는 방향으로 개선했다. 이러한 튜닝은 최종 모델 claim을 위한 것이 아니라, 제한된 개발 시간 안에서 실험 조건을 비교하고 inference pipeline을 완성하기 위한 engineering decision이다.
