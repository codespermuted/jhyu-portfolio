# C-BAL: 재현 가능한 CPU 실행 기록

[공개 C-BAL 코드](https://github.com/codespermuted/cbal)를 합성 데이터로 실행한 작은 예제입니다. 모델 비교, 앙상블 선택, 새로운 구간의 예측 과정을 확인할 수 있습니다. **아래 수치는 합성데이터 데모 결과이며 실제 전력·SMP·업무 성능을 의미하지 않습니다.**

## 실행 조건

- 소스 커밋: [`70a8139c163d000824e67c4420b43e14f42b5e3e`](https://github.com/codespermuted/cbal/tree/70a8139c163d000824e67c4420b43e14f42b5e3e)
- Python 3.12, CPU, 난수 seed 42
- 합성 시계열 3개 × 180일, 총 540행. 추세·주간 계절성·잡음을 코드에서 생성합니다.
- 시계열마다 **학습 152일 → 검증 14일 → 미사용 테스트 14일**로 나눕니다.
- 후보 6개: Naive, SeasonalNaive(주기 7), Average, Drift, AutoETS, AutoTheta
- 평가 지표: MAE. 검증에서 선택한 모델과 앙상블 가중치는 테스트 평가 전에 고정합니다.
- GPU, 유료 API, 사전학습 모델 다운로드는 사용하지 않습니다.

## 다시 실행하기

이 폴더에서 실행하세요. Git과 Python 3.12가 필요합니다. 아래는 macOS/Linux 명령입니다.

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt

git clone https://github.com/codespermuted/cbal.git cbal-source
git -C cbal-source checkout --detach 70a8139c163d000824e67c4420b43e14f42b5e3e

.venv/bin/python run_demo.py --source-dir ./cbal-source --output-dir ./run-output
```

스크립트는 커밋과 작업 트리 상태를 검사한 뒤 지정한 체크아웃의 코드를 직접 불러옵니다. 수치만 재현하려면 `--no-plot`을 추가하세요. 결과 CSV, JSON, 도표는 지정한 출력 폴더에 생성됩니다. 기본 재현 도표는 별도 글꼴 다운로드가 필요 없는 영문 표기입니다. 포트폴리오에 표시한 한글 도표와 데이터·계산 방법은 같습니다.

`requirements.txt`는 실제 실행 환경의 라이브러리 버전을 고정합니다. 실행 시간은 머신과 초기 라이브러리 로딩에 따라 달라지며 성능 주장에 사용하지 않습니다. OS·수치 라이브러리 차이로 마지막 소수점 자리에는 차이가 생길 수 있습니다.

## 저장된 결과

검증에서 선택된 모델은 `WeightedEnsemble`입니다.

| 모델 | 검증 MAE | 미사용 테스트 MAE |
| --- | ---: | ---: |
| WeightedEnsemble | 2.6101 | 2.5210 |
| AutoETS | 2.6757 | 2.5268 |
| AutoTheta | 2.7132 | **2.5173** |
| SeasonalNaive | 3.3599 | 4.0239 |
| Average | 14.3568 | 14.2854 |
| Naive | 15.6506 | 18.5409 |
| Drift | 16.1646 | 19.2344 |

앙상블 가중치는 AutoTheta 68.18%, AutoETS 21.59%, SeasonalNaive 10.23%입니다. **테스트에서는 AutoTheta 단독이 앙상블보다 근소하게 좋았습니다.** 검증에서 선택된 조합이 모든 미래 구간에서도 최선이라는 의미는 아닙니다.

## 재학습 처리

고정한 커밋의 `refit_full`은 앙상블이 선택되면 재학습을 건너뜁니다. 이 예제는 모델 선택 후 `predictor._models`의 각 기저 모델에 공개 `fit(trainval)`을 호출해 첫 166일 전체로 다시 적합합니다. 앙상블은 같은 모델 객체를 참조하며 가중치는 다시 선택하지 않습니다. 예측 캐시는 비활성화했습니다. 마지막 14일은 이 과정에 제공하지 않습니다.

이 처리는 외부 재현 스크립트에 있고 원본 저장소 코드는 변경하지 않았습니다. `_models`는 내부 속성이므로 다른 커밋에서는 인터페이스 확인이 필요합니다. 한 개 검증 창과 한 개 테스트 창만 사용했으며, 다중 구간 일반화·신경망·기반 모델 성능을 검증한 실험은 아닙니다.

## 파일

- `run_demo.py`: 데이터 생성, 모델 비교·재학습·예측, 결과 저장과 도표 생성
- `requirements.txt`: 실행에 사용한 의존성 버전
- `results.json`: 커밋, 조건, 가중치, 지표와 실행 환경
- `synthetic-data.csv`: 합성 입력 540행
- `validation-leaderboard.csv`: 검증 점수
- `prediction-*.csv`: 모델별 테스트 예측 42행(3개 시계열 × 14일)

스크립트는 후보 6개 학습 완료, 유한한 점수, 예측과 테스트의 정확한 인덱스 일치, 유한한 예측값을 검사합니다. 0.1/0.5/0.9 분위수도 원본 API 결과로 저장하지만 이 실험에서 구간 보정이나 커버리지를 검증하지는 않았습니다.

C-BAL은 AutoGluon의 설계와 기존 greedy ensemble selection 연구를 참고하며 통계 모델을 StatsForecast와 연결합니다. 이 기록은 해당 패키지 구현의 실행 예제이며 이들 알고리즘의 독창성을 주장하지 않습니다.
