# Norm Boundary 재현 기록

[공개 저장소](https://github.com/codespermuted/norm-boundary-ccai)의 고정 커밋 `33420b5a57bf720c09485a8cd5ee521954dc07e5`를 CPU에서 검증한 기록입니다. 전체 저장소·원시 데이터·모델 파일은 이 폴더에 포함하지 않습니다.

| 실제 실행 | 결과 | 의미 |
| --- | --- | --- |
| `python -m experiments.verify_paper_numbers` | **82/82 통과** | 고정 CSV와 저장된 표의 수치 일관성 |
| `python -m experiments.g7_prop1_verify` | **원본 assertion 통과** | 조건마다 200만 표본을 새로 생성한 Monte Carlo 검증 |
| `python -m pytest tests/test_theory.py -q` | **14 passed** | 이론·교차점·시뮬레이션 테스트 |

현재 코드의 검사는 82개입니다. 저장소 README의 68개 설명 이후 추가된 deployment 항목도 실행에 포함됐습니다. 전체 학습 그리드나 전체 테스트 모음을 실행했다는 뜻은 아닙니다.

## 결과를 읽는 법

- **기존 결과 재집계** — `footing-values.csv`: LinMix, GEFCom-Wind·Solar의 6개 조건, 조건·arm마다 5시드. RevIN−RAW MSE는 global `+0.025672`, floored window `−0.074810`, target-scale `−0.030290`입니다. 그림의 95% 구간은 조건을 단위로 한 bootstrap 10만 회, seed 0입니다. 실제 예측 모델을 다시 학습한 결과가 아닙니다.
- **새 합성 실험** — `synthetic-values.csv`: 가우시안 7조건 × 3식의 21비교가 원본 허용오차를 만족했습니다. 0이 아닌 이론값 대비 최대 상대오차는 **0.429%**입니다. t8 입력의 불일치는 가우시안 가정이 깨지는 사례로 함께 표시합니다. 실데이터 예측 성능으로 해석하지 않습니다.
- `summary.json`: 환경, 검사 범위, 집계 수치, 원본 CSV·포트폴리오 그림의 SHA256입니다. CSV에는 원문 그대로의 지표 이름과 수치를 담았습니다.

## 다시 실행하기

이 폴더에서 Python **3.12**와 Git을 사용합니다. 기록한 실행 환경은 Python 3.12.13입니다. `requirements.txt`에는 당시 사용한 패키지 버전을 고정했습니다. 네트워크는 공개 저장소와 패키지를 받는 단계에만 필요합니다.

```sh
git clone https://github.com/codespermuted/norm-boundary-ccai.git source
git -C source checkout --detach 33420b5a57bf720c09485a8cd5ee521954dc07e5
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python build-evidence.py --repo source --out runs
```

스크립트는 커밋과 변경되지 않은 소스를 확인한 뒤 위 세 원본 명령을 실행하고, 원본 집계·시뮬레이션 함수를 불러 그림을 만듭니다. BLAS 관련 스레드 수는 1로 고정합니다. CUDA PyTorch, 모델 가중치, 유료 API는 사용하지 않습니다. 저장소의 전체 의존성을 설치하는 `uv sync`도 필요하지 않습니다.

출력은 지정한 `runs/` 아래에만 생성합니다.

- `media/norm-boundary-footing-reproduction.svg`, `media/norm-boundary-theory-reproduction.svg`
- 그림 확인용 PNG, 세 명령의 로그, 상세 `norm-boundary-evidence.json`
- 그림에 사용한 `norm-boundary-footing-values.csv`

포트폴리오 원본 그림은 `../../public/media/`에 있습니다. 새 그림은 경로·생성 환경에 따라 파일 해시가 달라질 수 있으므로 수치와 검증 조건을 우선 비교합니다.

## 범위와 상태

원시 KMA/GEFCom 데이터와 4,202개 학습 실행을 다시 수행하지 않았습니다. 고정 결과와의 산술 일치는 원래 실험의 모든 데이터·학습 과정을 독립적으로 검증한 것이 아닙니다. 저장소의 스레드 재현성·일부 데이터 조건·사전등록 범위에 관한 한계도 유지됩니다.

공개 README는 이 자료를 **익명 워크숍 투고본**으로 소개합니다. 이 기록은 채택·게재 또는 특정 개인의 단독 기여를 주장하지 않습니다. 원본 코드의 라이선스는 저장소의 MIT 라이선스를 따릅니다.
