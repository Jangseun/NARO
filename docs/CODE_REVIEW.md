# NARO 코드 리뷰 설명서

이 문서는 NARO의 코드를 처음 보는 사람도 흐름을 따라갈 수 있도록 **파일별 역할**과 **핵심 함수**를 쉬운 말로 설명합니다.
발표나 코드 리뷰에서 질문을 받았을 때 이 문서를 보며 설명하면 됩니다.

---

## 0. 한눈에 보는 전체 흐름

```
[자료 등록]   MaterialsPage ──POST /api/materials──▶ main.py ──▶ DB(materials)
[카메라 켜기] CameraPanel   ──POST /api/camera/start──▶ vision.py: 카메라 스레드 시작
                                                       (프레임 읽기 → 얼굴 검출 → 각도 계산 반복)
[면접 시작]   InterviewSetupPage ──POST /api/interviews──▶ ai.generate_questions() → DB 저장
                                                            camera_manager.start_collecting()
[답변 저장]   InterviewPage ──POST /api/interviews/{id}/answers──▶ 답변 + 이 질문 동안의 영상 요약 저장
[면접 종료]   InterviewPage ──POST /api/interviews/{id}/complete──▶ 영상 전체 요약 + ai.evaluate_interview()
[결과 보기]   ResultPage ──GET /api/interviews/{id}──▶ 질문·답변·피드백·영상 분석 결과
```

**프론트엔드(React)** 는 화면을 보여 주고 사용자의 입력을 받는 역할만 합니다.
**백엔드(FastAPI)** 는 카메라 분석, AI 호출, DB 저장처럼 실제 처리를 모두 맡습니다.
둘은 **HTTP 요청과 JSON** 으로 대화합니다.

---

## 1. 영상 인식 — `backend/vision.py` (가장 중요)

### 1-1. `Camera` 클래스 — 영상 획득
- `source`가 `"picamera"`면 라즈베리파이 공식 라이브러리 **Picamera2** 로 카메라를 엽니다.
- `"webcam"`이면 **OpenCV의 `cv2.VideoCapture`** 로 USB 웹캠을 엽니다.
- `read()`는 영상 한 장(프레임)을 **numpy 배열**(가로×세로×색 3개 숫자)로 돌려줍니다.
- Picamera2의 `RGB888` 형식은 실제로 B·G·R 순서여서 OpenCV에서 바로 쓸 수 있습니다.

### 1-2. `FaceAnalyzer.analyze(frame)` — 얼굴 검출과 자세 계산
1. **YuNet 얼굴 검출 모델**(OpenCV에 들어 있는 작은 딥러닝 모델, 약 230KB)에 프레임을 넣습니다.
2. 모델은 얼굴마다 `[x, y, 너비, 높이, 오른눈, 왼눈, 코끝, 입 오른쪽, 입 왼쪽, 신뢰도]`를 돌려줍니다.
3. 얼굴이 여럿이면 **가장 큰 얼굴**을 면접자로 봅니다.
4. 특징점의 위치 관계로 다음을 계산합니다.

| 값 | 계산 방법 | 쉬운 설명 |
|---|---|---|
| **roll (기울기)** | `atan2(두 눈의 높이 차, 두 눈의 가로 거리)` | 두 눈을 이은 선이 기울어진 각도 |
| **yaw (좌우 회전)** | 코끝이 두 눈 가운데에서 옆으로 벗어난 거리 ÷ 눈 사이 거리 | 고개를 돌리면 코끝이 한쪽으로 치우쳐 보임 |
| **pitch_ratio (상하)** | (눈~코 거리) ÷ (눈~입 거리) | 고개를 숙이면 코가 입 쪽으로, 들면 눈 쪽으로 이동 |
| **offset (위치)** | 얼굴 중심 − 화면 중심 | 화면 가운데 앉았는지 |
| **face_size (거리)** | 얼굴 너비 ÷ 화면 너비 | 클수록 카메라에 가까움 |

5. 파일 위쪽의 기준값(`YAW_LIMIT = 20` 등)과 비교해 `facing_front`(정면 여부), `direction`(front/side/up/down) 등을 정합니다.

> 💡 **왜 눈 사이 거리로 나누나요?** 카메라에서 멀어지면 얼굴이 작아져 모든 거리가 줄어듭니다.
> 눈 사이 거리로 나누면 **거리와 상관없이** 비교할 수 있습니다.

> ⚠️ 이건 **고개 방향**이지 눈동자를 추적하는 **시선 추적이 아닙니다.** 각도도 대략적인 추정값입니다.

### 1-3. `draw_result()` — 결과를 영상에 그리기
얼굴 박스(정면이면 초록, 아니면 주황), 5개 특징점, 방향과 각도를 영상 위에 그립니다.
OpenCV 글꼴은 한글을 못 써서 영어로 표시합니다.

### 1-4. `CameraManager` — 백그라운드에서 계속 분석하기
- `start()`가 **스레드**(동시에 따로 돌아가는 작업)를 만들어 `_loop()`를 실행합니다.
- `_loop()`는 카메라가 켜져 있는 동안 **읽기 → 분석 → 그리기 → JPEG 저장**을 반복합니다.
- 여러 스레드가 같은 값을 동시에 바꾸지 않도록 `self.lock`으로 잠급니다.
- 면접 중(`collecting=True`)에는 매 프레임 결과를 `samples` 목록에 쌓습니다.
  - `take_summary()`: 질문 1개가 끝날 때 그 질문의 결과를 요약하고 목록을 비움
  - `finish_collecting()`: 면접이 끝날 때 전체 결과를 요약

### 1-5. `summarize_samples()` / `make_vision_feedback()` — 요약과 피드백
- **filter 개념**으로 조건에 맞는 프레임 수를 세어 비율을 구합니다.
  예) 정면 비율 = 정면이었던 프레임 수 ÷ 얼굴이 보인 프레임 수
- 움직임 지수 = 얼굴 위치의 **표준편차**(흔들린 정도) ÷ 얼굴 크기
- 자세 점수(100점) = 얼굴 인식 20 + 정면 40 + 기울지 않음 15 + 중앙 15 + 안정 10
- `make_vision_feedback()`은 `if`문으로 기준을 넘는 항목마다 조언 문장을 만듭니다. (AI 없이 동작)

---

## 2. 서버 — `backend/main.py`

**FastAPI의 역할:** 프론트엔드가 "이 주소로 이런 데이터를 보낼게"라고 요청하면,
그 주소에 연결된 파이썬 함수를 실행하고 결과를 JSON으로 돌려줍니다.

```python
@app.post("/api/materials")          # POST /api/materials 요청이 오면
def create_material(request: MaterialRequest, ...):   # 이 함수가 실행됨
```

- `MaterialRequest` 같은 `BaseModel` 클래스는 **요청 JSON의 모양**을 정합니다. 모양이 틀리면 FastAPI가 자동으로 오류를 돌려줍니다.
- `Depends(get_db)`: 요청마다 DB 연결을 열고 닫아 줍니다.
- `Depends(auth.require_login)`: 로그인 토큰이 없으면 함수 실행 전에 401 오류를 돌려줍니다.

### 주요 API
| 주소 | 하는 일 |
|---|---|
| `POST /api/login` | 아이디/비밀번호 확인 후 토큰 발급 |
| `GET/POST/PUT/DELETE /api/materials` | 자료 **CRUD** (Create·Read·Update·Delete) |
| `POST /api/interviews` | AI로 질문 생성 → 면접 저장 → 영상 수집 시작 |
| `POST /api/interviews/{id}/answers` | 답변 저장 + 그 질문 동안의 영상 분석 요약 저장 |
| `POST /api/interviews/{id}/complete` | 영상 전체 요약 + AI 평가 → 점수·피드백 저장 |
| `GET /api/interviews`, `/api/interviews/{id}` | 기록 목록 / 상세 |
| `GET /api/stats` | 대시보드·성장 분석용 통계 |
| `POST /api/camera/start`, `/stop` | 카메라 켜기/끄기 |
| `GET /api/camera/status` | 가장 최근 프레임의 분석 결과 |
| `GET /api/camera/stream` | 분석 결과가 그려진 영상 (MJPEG) |

> 💡 **MJPEG이란?** JPEG 사진을 아주 빠르게 연달아 보내는 방식입니다.
> 브라우저의 `<img>` 태그가 이를 받아 영상처럼 보여 줍니다. 그래서 별도 영상 라이브러리가 필요 없습니다.

### 면접 결과 저장 과정 (`complete_interview`)
1. `camera_manager.finish_collecting()`으로 면접 전체 영상 분석을 요약
2. `make_vision_feedback()`으로 태도 피드백 문장 생성 → DB 저장
3. `ai.evaluate_interview()`로 답변 평가 (영상 요약도 함께 AI에 전달)
4. 질문별 점수·피드백 저장, 평균 점수 계산, 상태를 `completed`로 변경

AI 호출이 실패하면 502 오류를 돌려주고, 답변은 이미 저장되어 있으므로 화면에서 **"피드백 다시 요청하기"** 로 재시도할 수 있습니다.

---

## 3. AI — `backend/ai.py`

### AI API 호출 과정 (`ask_ai_for_json`)
1. `OpenAI()`가 환경변수 `OPENAI_API_KEY`를 읽어 연결합니다. (키는 백엔드에만 있음)
2. `system` 메시지로 AI의 역할(면접관/코치)을, `user` 메시지로 실제 요청을 보냅니다.
3. `response_format={"type": "json_object"}`로 **JSON으로만 답하게** 해서 파이썬이 바로 읽을 수 있게 합니다.
4. `json.loads()`로 문자열을 딕셔너리로 바꿉니다.

### 질문 생성 (`generate_questions`)
선택한 자료의 본문을 프롬프트에 넣어 **"이 사람의 자료에 나온 경험을 질문에 활용하라"** 고 요청합니다.

### 답변 평가 (`evaluate_interview`)
모든 질문·답변과 **카메라 분석 요약**(정면 비율, 고개 숙임 비율 등)을 함께 보내,
질문별 점수와 종합 피드백을 받습니다. 그래서 종합 피드백에 자세 이야기도 들어갑니다.

### 데모 모드
API 키가 없으면 `make_demo_questions()`(정해진 질문 틀), `make_demo_feedback()`(답변 길이·숫자 포함 여부로 점수)을 사용합니다.
DB에 `is_demo=True`로 저장되고 화면에 "데모 모드"가 표시되어 **실제 AI 결과와 구분**됩니다.

---

## 4. DB — `backend/database.py`

**SQLAlchemy**는 파이썬 클래스로 테이블을 정의하게 해 주는 도구입니다. 클래스 1개 = 테이블 1개.

| 테이블 | 주요 칸 |
|---|---|
| `users` | username, password_hash, salt |
| `materials` | title, type, content, created_at |
| `interviews` | company, position, interview_type, status, average_score, overall_feedback, **vision_summary**, **vision_feedback**, is_demo |
| `interview_answers` | interview_id, order, question, answer, feedback, score, **vision_stats** |

- `relationship`으로 면접 1개 ↔ 답변 여러 개를 연결합니다. (`interview.answers`로 바로 접근)
- 피드백·영상 요약처럼 모양이 복잡한 값은 **JSON 문자열**로 바꿔 한 칸에 저장합니다. (`json.dumps` ↔ `json.loads`)

## 5. 로그인 — `backend/auth.py`
- 비밀번호는 **원문을 저장하지 않고** `hashlib.pbkdf2_hmac`으로 10만 번 해시한 값만 저장합니다.
- `salt`(무작위 문자열)를 섞어서 같은 비밀번호라도 해시값이 달라지게 합니다.
- 로그인 성공 시 `secrets.token_hex()`로 무작위 토큰을 만들어 돌려주고, 이후 요청마다 확인합니다.
- 토큰은 서버 메모리에 저장되므로 서버를 재시작하면 다시 로그인해야 합니다. (단순함을 위한 선택)

---

## 6. 프론트엔드 — `frontend/src/`

### `api.js` — 서버와 대화하는 함수
`apiRequest(path, method, body)` 하나로 모든 요청을 보냅니다.
- 요청마다 `Authorization: Bearer 토큰` 헤더를 붙입니다.
- 401(로그인 필요)이면 토큰을 지우고 로그인 페이지로 보냅니다.
- 실패하면 서버가 보낸 `detail` 메시지로 오류를 던져, 화면에서 `catch`로 보여 줍니다.

### `App.jsx` — React Router
주소와 페이지를 연결합니다. `/interview/:id`의 `:id`는 `useParams()`로 꺼내 씁니다.
`MainLayout`은 토큰이 없으면 `<Navigate to="/login" />`으로 로그인 페이지로 보냅니다.

### `components/CameraPanel.jsx` — 재사용 컴포넌트와 Props
- 영상 분석 페이지, 면접 설정, 면접 진행 **세 곳에서 같은 컴포넌트를 재사용**합니다.
- `compact` **Props**로 간단 모드/자세한 모드를 바꿉니다: `<CameraPanel compact />`
- `useEffect` + `setInterval`로 **0.5초마다** 분석 결과를 요청하고, 컴포넌트가 사라질 때 `clearInterval`로 정리합니다.
- 영상은 `<img src=".../api/camera/stream?token=...">` 한 줄로 표시합니다.

### 페이지별 핵심
| 파일 | 설명할 포인트 |
|---|---|
| `LoginPage.jsx` | `async/await`로 로그인 요청, 성공 시 `saveToken` 후 `navigate('/')` |
| `MaterialsPage.jsx` | `useState`로 입력값 관리, `editingId`로 등록/수정 구분, 삭제 후 `filter`로 목록 갱신, `map`으로 카드 출력 |
| `InterviewSetupPage.jsx` | 체크박스 선택 목록을 `includes`/`filter`로 관리, 질문 생성 중 버튼 비활성화 |
| `InterviewPage.jsx` | `currentIndex`로 현재 질문 관리, 답변 저장 후 다음 질문, 마지막이면 `complete` 호출. 크롬 `SpeechRecognition`으로 음성 입력 |
| `ResultPage.jsx` | 작은 컴포넌트 `VisionStats`에 `stats` Props 전달, 질문별 결과를 `map`으로 출력 |
| `GrowthPage.jsx` | `map`으로 그래프용 데이터 변환 후 Recharts `LineChart`로 표시 |
| `DashboardPage.jsx` | `useEffect`로 화면이 처음 나타날 때 한 번 통계 요청 (`[]` 의존성 배열) |

### `useState`와 `useEffect` 한 줄 정리
- `useState`: 화면에 보여 줄 값을 기억하고, 값이 바뀌면 화면을 다시 그립니다.
- `useEffect(() => {...}, [])`: 화면이 처음 나타날 때 한 번 실행 (서버에서 데이터 불러오기에 사용).
  배열에 값을 넣으면(`[id]`) 그 값이 바뀔 때마다 다시 실행됩니다.

---

## 7. 예상 질문과 답변

**Q. 왜 MediaPipe 대신 OpenCV YuNet을 썼나요?**
MediaPipe는 최신 버전에서 사용 방식(API)이 바뀌었고 라즈베리파이·파이썬 버전 호환 문제가 있었습니다.
OpenCV에 내장된 YuNet은 OpenCV만 설치하면 동작하고, 모델이 작아(230KB) 라즈베리파이에서도 빠르게 돌아갑니다.

**Q. 시선을 추적하나요?**
아니요. 얼굴 특징점으로 **고개가 향한 방향**을 추정합니다. 눈동자 위치를 보는 시선 추적은 구현하지 않았습니다.

**Q. 기준값(20도 등)은 어떻게 정했나요?**
테스트 이미지와 웹캠으로 정면·회전·기울임 자세를 해 보며 정한 값입니다. 사람이나 카메라 위치에 따라 조정이 필요할 수 있어 파일 맨 위에 모아 두었습니다.

**Q. API 키는 안전한가요?**
키는 백엔드의 `.env` 파일에만 있고 git에도 올라가지 않습니다(`.gitignore`). 프론트엔드는 백엔드에만 요청하므로 브라우저에 키가 노출되지 않습니다.

**Q. 라즈베리파이를 왜 썼나요?**
카메라를 직접 연결해 영상 처리를 기기 안에서 할 수 있고, 작고 저렴해서 책상 위에 면접 연습용 장치처럼 둘 수 있기 때문입니다. 영상이 외부 서버로 나가지 않는다는 장점도 있습니다.
