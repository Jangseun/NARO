# NARO (나로)

### 가장 나다운 모습으로 나아가다.

**NARO**는 **Raspberry Pi Camera 영상 인식**으로 면접자의 고개 방향과 자세를 분석하고,
**AI**로 맞춤형 면접 질문과 답변 피드백을 제공하는 개인용 모의면접 연습 플랫폼입니다.

```
Raspberry Pi Camera → 영상 인식(얼굴·특징점 검출) → 자세 분석 → 면접 피드백
```

---

## 1. 시스템 구조

```
┌──────────────── Raspberry Pi (또는 PC) ────────────────┐
│  Pi Camera / USB 웹캠                                   │
│      │ 640×480 영상                                      │
│      ▼                                                  │
│  vision.py  ── OpenCV YuNet 얼굴 검출 (5개 특징점)       │
│      │         고개 좌우 회전 / 기울기 / 상하 / 위치 / 거리 │
│      ▼                                                  │
│  main.py (FastAPI)  ── ai.py (OpenAI API)               │
│      │                └ database.py (SQLite)            │
└──────┼──────────────────────────────────────────────────┘
       │ HTTP (JSON, MJPEG 영상)
       ▼
  웹 브라우저 (React) : 실시간 영상·분석값 표시, 면접 진행, 결과 확인
```

| 폴더 | 역할 |
|---|---|
| `backend/vision.py` | 카메라 영상 획득, 얼굴 검출, 고개 방향 계산, 면접 중 분석 데이터 수집·요약 |
| `backend/ai.py` | OpenAI API로 질문 생성·답변 평가 (API 키가 없으면 데모 모드) |
| `backend/main.py` | 모든 API 주소 (로그인, 자료, 면접, 통계, 카메라) |
| `backend/database.py` | SQLite 테이블 정의 |
| `backend/auth.py` | 단일 계정 로그인 (비밀번호 해시 저장) |
| `frontend/src/` | React 화면 |

---

## 2. 실행 방법 (PC, 윈도우 기준)

### 준비물
- Python 3.10 ~ 3.12, Node.js 18 이상
- USB 웹캠 또는 노트북 내장 카메라 (PC에서 테스트할 때)

### 백엔드

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate            # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env            # macOS/Linux: cp .env.example .env
uvicorn main:app --host 0.0.0.0 --port 8000 --timeout-graceful-shutdown 3
```

- 얼굴 검출 모델 파일 `backend/models/face_detection_yunet_2023mar.onnx`가 있어야 합니다.
  없으면 [opencv_zoo](https://github.com/opencv/opencv_zoo/tree/main/models/face_detection_yunet)에서 내려받아 넣어 주세요.
- 서버를 처음 실행하면 `naro.db`와 로그인 계정이 자동으로 만들어집니다. (기본: `naro` / `naro1234`)

### 프론트엔드

```bash
cd frontend
npm install
npm run dev
```

브라우저에서 `http://localhost:5173` 접속 → 로그인

### 환경변수 (`backend/.env`)

| 이름 | 설명 |
|---|---|
| `OPENAI_API_KEY` | OpenAI API 키. **비워 두면 데모 모드** (정해진 규칙으로 질문/피드백 생성, 화면에 "데모 모드" 표시) |
| `OPENAI_BASE_URL` | 비우면 OpenAI(유료). Gemini 주소를 적으면 **무료 Gemini API** 사용 (`.env.example` 참고) |
| `OPENAI_MODEL` | 사용할 모델 (쉼표로 여러 개 적으면 실패 시 다음 모델로 자동 전환. 예: `gemini-3.1-flash-lite,gemini-3.5-flash-lite,gemini-3.5-flash`) |
| `NARO_USERNAME`, `NARO_PASSWORD` | 로그인 계정. 바꾸려면 `naro.db`를 지우고 서버 재시작 |
| `WEBCAM_INDEX` | USB 웹캠 번호 (기본 0) |
| `CAMERA_ROTATE_180` | 카메라를 거꾸로 달았으면 `1` |

API 키는 백엔드 `.env`에만 저장하며 프론트엔드에는 전달되지 않습니다.

---

## 3. Raspberry Pi에서 실행하기

> ⚠️ 이 부분은 실제 라즈베리파이 하드웨어에서 아직 테스트하지 않았습니다.
> PC(윈도우)에서는 같은 분석 코드를 USB 웹캠으로 테스트했습니다. 아래 순서대로 설치 후 `python vision.py picamera`로 먼저 확인하세요.

**권장 환경:** Raspberry Pi 4 / 5, Raspberry Pi OS (Bookworm 이후, 64bit), Camera Module (v2 / v3 / HQ)

```bash
# 1) 카메라 확인 (영상이 5초간 나오면 정상)
rpicam-hello -t 5000          # 예전 OS에서는 libcamera-hello

# 2) picamera2 설치 (apt로 설치해야 함)
sudo apt update
sudo apt install -y python3-picamera2

# 3) 가상환경: 시스템의 picamera2를 쓰기 위해 --system-site-packages 필수
cd NARO/backend
python3 -m venv --system-site-packages .venv
source .venv/bin/activate
pip install -r requirements-pi.txt

# 4) 카메라 + 얼굴 분석 단독 테스트 (30프레임 분석 후 FPS 출력)
python vision.py picamera

# 5) 서버 실행
cp .env.example .env
uvicorn main:app --host 0.0.0.0 --port 8000 --timeout-graceful-shutdown 3
```

**PC 브라우저에서 접속하기:** 라즈베리파이 IP 확인(`hostname -I`) 후 PC의 `frontend/.env` 파일에

```
VITE_API_URL=http://라즈베리파이IP:8000
```

을 적고 `npm run dev` → `http://localhost:5173` 접속 → **영상 분석** 메뉴에서 `Raspberry Pi Camera` 선택 후 카메라 켜기.

- 화면에 "Raspberry Pi Camera (감지 안 됨)"이 보이면 picamera2를 불러오지 못한 것입니다 (가상환경 옵션 확인).
- 분석이 느리면 `vision.py`의 `FRAME_WIDTH/HEIGHT`를 `320/240`으로 낮추세요.
- 예전 OS(Buster 등, legacy 카메라)에서는 Pi Camera가 `/dev/video0`로 잡히므로 `USB 웹캠`을 선택하면 OpenCV로 읽을 수 있습니다.

---

## 4. 구현 현황

### ✅ 구현 완료 (PC + USB 웹캠으로 실행 테스트함)
| 기능 | 내용 |
|---|---|
| 영상 획득 | Pi Camera(Picamera2) / USB 웹캠(OpenCV) 선택 |
| 얼굴 검출 | OpenCV YuNet 딥러닝 모델, 얼굴 박스 + 5개 특징점 |
| 자세 분석 | 고개 좌우 회전(yaw), 기울기(roll), 상하 지수(pitch), 화면 중앙 여부, 카메라 거리, 머리 움직임 |
| 실시간 표시 | 분석 결과를 그린 영상(MJPEG) + 수치를 0.5초마다 웹에 표시 (웹캠 기준 약 12~15 FPS) |
| 면접 중 수집 | 질문별로 프레임 분석 결과를 모아 정면 응시 비율 등으로 요약·저장 |
| 영상 피드백 | 규칙 기반 태도 피드백 + 자세 점수, AI 종합 피드백에도 반영 |
| 로그인 | 단일 계정, PBKDF2 비밀번호 해시, 토큰 인증, 비로그인 시 접근 차단 |
| 자료 관리 | 제목/유형/본문 등록·조회·수정·삭제 (SQLite) |
| AI 질문 생성 | 기업·직무·유형·개수·선택 자료 반영 (OpenAI) |
| 모의면접 | 질문 1개씩 표시, 텍스트 답변, 크롬 음성 입력(Web Speech API) |
| AI 피드백 | 질문별 점수, 의도/구체성/논리성, 잘한 점, 개선점, 개선 답변 예시 |
| 기록·성장 분석 | 면접 목록·상세, 통계 카드, 답변/자세 점수 그래프 |
| 데모 모드 | API 키가 없을 때 규칙 기반 질문/점수, 화면에 "데모 모드"로 구분 표시 |

### ⚠️ 코드는 있지만 실제 환경 테스트 전
- Raspberry Pi Camera 연동 (`picamera` 경로) — 실제 라즈베리파이에서 확인 필요
- 실제 OpenAI API 호출 — 테스트 시 API 키가 없어 데모 모드로만 확인함

### ❌ 미구현
- PDF/DOCX 파일 업로드 (텍스트 붙여넣기만 지원)
- Whisper 기반 음성 인식 (브라우저 음성 인식으로 대체), 추임새 등 말하기 습관 분석
- 어깨·상체 자세 분석 (현재는 얼굴 특징점 기반 분석만)
- 눈동자 시선 추적 (고개 방향만 추정)
- WebSocket 실시간 통신 (0.5초 간격 요청으로 대체)

---

## 5. 한계 및 주의사항
- 각도는 얼굴 5개 특징점으로 계산한 **대략적인 추정값**이며 시선 추적이 아닙니다.
- 점수는 연습용 참고 지표이며 실제 면접 합격 가능성을 의미하지 않습니다.
- 음성 입력은 크롬 브라우저에서 `localhost` 또는 https 주소로 접속할 때만 동작합니다.
- 동시에 한 명이 한 개의 면접만 진행하는 개인용 구조입니다.

**NARO — 가장 나다운 모습으로 나아가다.**
