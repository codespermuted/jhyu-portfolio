# 유재홍 포트폴리오

Astro로 만든 정적 포트폴리오입니다. 소개, 대표 작업, 분야별 프로젝트 목록과 프로젝트 상세 페이지 13개를 제공합니다. 별도 서버나 데이터베이스가 필요하지 않습니다.

## 실행

Node.js 22.12 이상(권장 24 LTS)이 필요합니다.

```sh
npm ci
npm run dev
```

터미널에 표시되는 로컬 주소를 엽니다. 배포 파일은 다음 명령으로 만듭니다.

```sh
npm run build
npm run check:output
```

결과는 `dist/`에 생성됩니다. `npm run preview`로 빌드 결과를 확인할 수 있습니다.

## 내용 수정

| 수정할 내용 | 파일 |
| --- | --- |
| 이름, 이메일, GitHub, 학력, 경력, 작업 원칙 | `src/data/profile.json` |
| 프로젝트 설명, 기술, 결과, 이미지, 논문·코드 링크 | `src/data/projects.json` |
| 첫 화면 제목, 섹션 구성, 대표 프로젝트 선택 | `src/pages/index.astro` |
| 프로젝트 상세 페이지 공통 구성 | `src/pages/projects/[slug].astro` |
| 색, 여백, 글자 크기, 반응형 | `src/styles/global.css` |
| 이미지와 영상 | `public/media/` |

`projects.json`의 `shortTitle`은 홈의 짧은 제목, `cardSummary`는 전체 목록의 한 문장 설명입니다. `title`·`summary`는 상세 페이지와 더 자세한 소개에 사용합니다. 목록에는 문제와 접근법을 짧게 쓰고, 평가 조건과 수치의 근거는 상세 설명에 둡니다.

프로젝트 배열에 같은 필드 구조의 객체를 추가하면 상세 페이지와 목록이 생성됩니다. `slug`는 고유해야 합니다. 분야는 `forecasting`, `systems`, `research` 중 하나로 지정합니다. 분야별 필터 개수는 자동으로 계산됩니다. 빌드 검사는 데이터의 프로젝트 수와 실제 상세 페이지 수를 대조합니다. 대표 작업은 `index.astro`의 `selected` 배열에서 고릅니다.

이미지에는 실제 `width`, `height`와 설명하는 `alt`를 넣습니다. SMP 홈 비교기는 이미지 배열의 첫 3개를 사용하며 두 번째 사례를 먼저 표시합니다. 순서를 바꾸면 `src/components/SmpComparison.astro`의 초기 선택도 확인하세요. 바뀐 미디어는 새 파일명을 쓰면 캐시가 오래된 파일을 보여주는 일을 줄일 수 있습니다.

글꼴은 자체 호스팅한 Instrument Sans와 Noto Sans KR 부분 글꼴입니다. 새로 추가한 한글이 부분 글꼴에 없으면 시스템의 한글 글꼴로 표시됩니다. 외부 글꼴 서버에 연결하지 않습니다. 라이선스는 `public/fonts/OFL-*.txt`에 있습니다.

## GitHub 수정과 자동 배포

소스 저장소는 [codespermuted/jhyu-portfolio](https://github.com/codespermuted/jhyu-portfolio)이며, 기존 [Netlify 주소](https://jhyu-portfolio.netlify.app/)를 사용합니다. 연결 대상은 이 저장소 하나입니다.

`main` 브랜치에 변경을 push하면 Netlify가 Node.js 24로 의존성을 설치하고 `npm run build && npm run check:output`을 실행한 뒤 `dist/`를 배포합니다. 검사에 실패하면 새 파일이 게시되지 않습니다. 로컬 파일을 저장하는 것만으로는 배포되지 않습니다.

```sh
git pull --ff-only
# src/data/projects.json 또는 src/data/profile.json 등 수정
npm run build && npm run check:output
git add .
git commit -m "Update portfolio content"
git push origin main
```

간단한 문구 수정은 GitHub에서 파일을 열어 편집 후 `main`에 커밋해도 같은 배포 흐름을 사용합니다. 배포 진행·실패 원인은 [Netlify Deploys](https://app.netlify.com/projects/jhyu-portfolio/deploys)에서 확인합니다. 자동 배포 설정은 `netlify.toml`에 있으며, 수동 복구가 필요하면 검증된 `dist/`를 기존 사이트에 업로드할 수 있습니다.

## GitHub Pages로 옮기는 경우

현재 주소를 유지하는 것이 기본입니다. 나중에 이전할 경우 서버 기능이 없는 정적 파일이므로 같은 코드를 사용할 수 있습니다.

```sh
SITE_URL=https://codespermuted.github.io BASE_PATH=/repository-name npm run build
npm run check:output
```

사용자 루트 사이트라면 `BASE_PATH=/`로 지정합니다. 생성된 `dist/`를 GitHub Pages의 배포 대상으로 사용합니다. GitHub Pages용 Actions 워크플로는 포함하지 않았습니다. 현재 자동 배포는 Netlify의 Git 연동을 사용합니다.

## 성능을 개선한 방식

- 43,370,600바이트 HTML 안에 있던 Base64 미디어를 별도 파일로 분리했습니다.
- GIF 4개를 H.264 MP4로 변환했습니다. 포스터를 먼저 표시하고 `preload="none"`으로 재생 전 다운로드를 막습니다.
- 정적 이미지는 WebP로 바꿨고 크기를 명시했습니다. 첫 화면 외 이미지는 지연 로딩합니다.
- 상세 자료는 프로젝트별 페이지에 분산했습니다.
- 클라이언트 프레임워크를 보내지 않습니다. 작은 JS 모듈로 프로젝트 분야 필터와 SMP 사례 선택만 처리합니다. 분야 선택은 현재 브라우저 세션에서 유지하며, JS가 없어도 전체 목록·기본 차트·상세 링크를 사용할 수 있습니다.
- 실제 네트워크의 LCP·INP·CLS는 배포 후 같은 환경에서 측정해야 합니다. 파일 크기 감소를 체감 속도 배율로 표현하지 않습니다.

## 디자인과 검사 기록

[Impeccable](https://github.com/pbakaus/impeccable)과 [Taste Skill](https://github.com/leonxlnx/taste-skill)의 지침을 적용했습니다. 두 번째 개선에서는 첫 화면의 실제 예측 자료를 콘텐츠 전체 폭으로 넓히고, SMP 차트 3개를 한 번에 축소하는 대신 사례 선택기로 한 장씩 읽게 했습니다. 전체 프로젝트 바로가기와 상세 페이지의 목록 복귀 경로도 정리했습니다.

확인한 Marketplace 다운로드 경로는 아래와 같습니다. 지침·선택한 참고 문서는 작업용 복제본과 동일합니다. 등록·다운로드 확인이며 활성 플러그인 설치를 뜻하지 않습니다.

| 도구 | 버전·소스 커밋 | Marketplace 경로 |
| --- | --- | --- |
| Impeccable | skill 4.9.1, engine 0.1.24 · `1995764b4936f2bfbf4eb719cb37b384a45ceacb` | `~/.codex/.tmp/marketplaces/impeccable/.agents/skills/impeccable` |
| Taste Skill | 2.5.1 · `f6b76575f949707b4e3c37cd86cb44b0b98643e8` | `~/.codex/.tmp/marketplaces/taste-skill/skills/taste-skill` |

실제 검사는 작업용 복제본의 원본 실행기로 수행했고, 최종 소스·문구 검사는 동일 버전의 Marketplace 경로에서도 실행했습니다.

- **Impeccable**: 프로젝트에서 `context`를 실행했고, 수정 후 `detect --json src`를 실행해 종료 코드 0과 빈 결과 `[]`를 받았습니다. Astro·CSS·TS 소스에는 기본 정규식 검사만 적용되어 글자 크기·대비 같은 DOM 규칙은 검사하지 않습니다.
- **Taste**: 원본 `copy-lint.mjs`를 `--kind service --year 2026 --json`으로 빌드된 13개 HTML에 실행해 검출 항목 0개를 확인했습니다. 영문 중심 규칙이므로 한국어 문장의 정확성이나 가독성을 보증하지 않습니다.
- **빌드 검사**: `npm run check:output`으로 라우트, 내부 링크·미디어, 이미지 메타데이터와 크기 예산을 검사합니다. 최종 화면은 별도 브라우저 검토 대상입니다.

Taste의 Chrome 기반 `consistency`·`perf`와 전체 native gate는 실행하지 않았습니다. 사이트 성능과 읽기 흐름을 우선해 전체 키트·강제 화면 높이·WebGL·자동 디자인 추첨은 도입하지 않았습니다. 검사 결과 0개를 전체 디자인·접근성·실측 성능 검증 통과로 해석하지 않습니다.

원본은 사용자가 제공한 공개 Netlify 사이트에서 복원했습니다. 공개된 GitHub 코드와 논문을 함께 확인했으며, 확인이 필요한 내용은 `CONTENT-NOTES.md`에 정리했습니다.

## 연구 구성과 실행 증거

홈은 SMP·Mojo 대표 작업 다음에 CBALLM·이미지 기반 약효 평가·DDI를 **모델링과 검증**으로 묶습니다. 이 섹션의 선택과 설명은 `src/components/ResearchShowcase.astro`에서 수정합니다. DB 조회 기반 RAG 사례는 전체 목록 마지막이며, `TutorArchitecture.astro`가 실제 분기와 한계를 설명합니다.

추가된 C-BAL과 정규화 연구는 공개 코드를 직접 실행해 결과물을 만들었습니다. [C-BAL 재현 방법](evidence/cbal/README.md)과 [정규화 연구 재현 방법](evidence/norm-boundary/README.md)에 고정 커밋·환경·명령·결과를 보존했습니다. 합성데이터 실험과 기존 CSV 재집계를 구분하며, 이 기록을 실제 업무 성능이나 신규 실데이터 학습으로 표현하지 않습니다. 재현 작업은 웹 빌드와 별개여서 Netlify에서는 실행하지 않습니다.
