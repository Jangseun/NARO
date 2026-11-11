# main.py
# FastAPI 서버의 시작점. 프론트엔드(React)가 요청하는 모든 API 주소가 여기에 있다.
#
# 실행 방법: uvicorn main:app --host 0.0.0.0 --port 8000

import asyncio
import json
from contextlib import asynccontextmanager
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()  # .env 파일의 환경변수(API 키, 비밀번호 등)를 읽는다. 다른 import보다 먼저 실행

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

import ai
import auth
from database import Base, Interview, InterviewAnswer, Material, engine, get_db
from vision import camera_manager, make_vision_feedback


@asynccontextmanager
async def lifespan(app):
    # 서버가 켜질 때: 테이블 만들기 + 기본 계정 만들기
    Base.metadata.create_all(bind=engine)
    auth.create_default_user()
    yield
    # 서버가 꺼질 때: 카메라 끄기
    camera_manager.stop()


app = FastAPI(title="NARO API", lifespan=lifespan)

# 프론트엔드(다른 주소, 예: localhost:5173)에서 이 서버로 요청할 수 있도록 허용
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# 요청 데이터 형식 (프론트엔드가 보내는 JSON의 모양)
# ---------------------------------------------------------------------------

class LoginRequest(BaseModel):
    username: str
    password: str


class MaterialRequest(BaseModel):
    title: str
    type: str
    content: str


class InterviewRequest(BaseModel):
    company: str
    position: str
    interview_type: str
    question_count: int
    material_ids: list[int] = []


class AnswerRequest(BaseModel):
    order: int
    answer: str


class CameraRequest(BaseModel):
    source: str  # "picamera" 또는 "webcam"


# ---------------------------------------------------------------------------
# DB 객체 → JSON(딕셔너리) 변환 함수
# ---------------------------------------------------------------------------

def load_json(text):
    """DB에 문자열로 저장한 JSON을 다시 파이썬 값으로 바꾼다"""
    return json.loads(text) if text else None


def material_to_dict(material):
    return {
        "id": material.id,
        "title": material.title,
        "type": material.type,
        "content": material.content,
        "created_at": material.created_at.isoformat(),
    }


def interview_to_dict(interview, include_answers=False):
    vision_summary = load_json(interview.vision_summary)
    data = {
        "id": interview.id,
        "company": interview.company,
        "position": interview.position,
        "interview_type": interview.interview_type,
        "created_at": interview.created_at.isoformat(),
        "completed_at": interview.completed_at.isoformat() if interview.completed_at else None,
        "status": interview.status,
        "average_score": interview.average_score,
        "posture_score": vision_summary["posture_score"] if vision_summary else None,
        "is_demo": interview.is_demo,
    }
    if include_answers:
        data["overall_feedback"] = interview.overall_feedback
        data["vision_summary"] = vision_summary
        data["vision_feedback"] = load_json(interview.vision_feedback)
        data["answers"] = [
            {
                "order": item.order,
                "question": item.question,
                "answer": item.answer,
                "score": item.score,
                "feedback": load_json(item.feedback),
                "vision_stats": load_json(item.vision_stats),
            }
            for item in interview.answers
        ]
    return data


def find_interview(db, interview_id):
    interview = db.get(Interview, interview_id)
    if interview is None:
        raise HTTPException(status_code=404, detail="면접 기록을 찾을 수 없습니다.")
    return interview


# ---------------------------------------------------------------------------
# 1. 로그인
# ---------------------------------------------------------------------------

@app.post("/api/login")
def login(request: LoginRequest):
    token = auth.login(request.username, request.password)
    if token is None:
        raise HTTPException(status_code=401, detail="아이디 또는 비밀번호가 올바르지 않습니다.")
    return {"token": token, "username": request.username}


@app.get("/api/me")
def me(token: str = Depends(auth.require_login)):
    """토큰이 아직 유효한지 확인할 때 사용"""
    return {"ok": True, "demo_mode": ai.is_demo_mode()}


# ---------------------------------------------------------------------------
# 2. 자료 관리 (CRUD: 생성 Create / 조회 Read / 수정 Update / 삭제 Delete)
# ---------------------------------------------------------------------------

@app.get("/api/materials")
def list_materials(db: Session = Depends(get_db), token: str = Depends(auth.require_login)):
    materials = db.query(Material).order_by(Material.created_at.desc()).all()
    return [material_to_dict(m) for m in materials]


@app.post("/api/materials")
def create_material(request: MaterialRequest, db: Session = Depends(get_db),
                    token: str = Depends(auth.require_login)):
    if not request.title.strip() or not request.content.strip():
        raise HTTPException(status_code=400, detail="제목과 내용을 모두 입력해 주세요.")
    material = Material(title=request.title.strip(), type=request.type, content=request.content.strip())
    db.add(material)
    db.commit()
    db.refresh(material)  # DB가 정한 id, created_at 값을 다시 읽어 온다
    return material_to_dict(material)


@app.put("/api/materials/{material_id}")
def update_material(material_id: int, request: MaterialRequest, db: Session = Depends(get_db),
                    token: str = Depends(auth.require_login)):
    material = db.get(Material, material_id)
    if material is None:
        raise HTTPException(status_code=404, detail="자료를 찾을 수 없습니다.")
    if not request.title.strip() or not request.content.strip():
        raise HTTPException(status_code=400, detail="제목과 내용을 모두 입력해 주세요.")
    material.title = request.title.strip()
    material.type = request.type
    material.content = request.content.strip()
    db.commit()
    return material_to_dict(material)


@app.delete("/api/materials/{material_id}")
def delete_material(material_id: int, db: Session = Depends(get_db),
                    token: str = Depends(auth.require_login)):
    material = db.get(Material, material_id)
    if material is None:
        raise HTTPException(status_code=404, detail="자료를 찾을 수 없습니다.")
    db.delete(material)
    db.commit()
    return {"ok": True}


# ---------------------------------------------------------------------------
# 3. 모의면접 (질문 생성 → 답변 저장 → 종료 및 피드백)
# ---------------------------------------------------------------------------

@app.post("/api/interviews")
def create_interview(request: InterviewRequest, db: Session = Depends(get_db),
                     token: str = Depends(auth.require_login)):
    if not request.company.strip() or not request.position.strip():
        raise HTTPException(status_code=400, detail="지원 기업과 직무를 입력해 주세요.")
    if not 1 <= request.question_count <= 10:
        raise HTTPException(status_code=400, detail="질문 개수는 1~10개로 정해 주세요.")

    # 사용자가 선택한 자료만 DB에서 가져온다
    materials = []
    if request.material_ids:
        materials = db.query(Material).filter(Material.id.in_(request.material_ids)).all()

    # AI에게 질문 생성을 요청한다
    try:
        questions = ai.generate_questions(
            request.company, request.position, request.interview_type,
            request.question_count, materials,
        )
    except Exception as error:
        raise HTTPException(status_code=502, detail=f"AI 질문 생성에 실패했습니다: {error}")

    interview = Interview(
        company=request.company.strip(),
        position=request.position.strip(),
        interview_type=request.interview_type,
        is_demo=ai.is_demo_mode(),
    )
    # 질문마다 InterviewAnswer 행을 만든다 (답변은 아직 비어 있음)
    for index, question in enumerate(questions):
        interview.answers.append(InterviewAnswer(order=index + 1, question=question))
    db.add(interview)
    db.commit()
    db.refresh(interview)

    # 면접이 시작되었으니 카메라 분석 결과를 모으기 시작한다
    camera_manager.start_collecting()
    return interview_to_dict(interview, include_answers=True)


@app.post("/api/interviews/{interview_id}/answers")
def save_answer(interview_id: int, request: AnswerRequest, db: Session = Depends(get_db),
                token: str = Depends(auth.require_login)):
    interview = find_interview(db, interview_id)
    item = db.query(InterviewAnswer).filter(
        InterviewAnswer.interview_id == interview.id,
        InterviewAnswer.order == request.order,
    ).first()
    if item is None:
        raise HTTPException(status_code=404, detail="해당 질문을 찾을 수 없습니다.")

    item.answer = request.answer.strip()
    # 이 질문에 답하는 동안 모은 카메라 분석 결과를 요약해서 함께 저장한다
    vision_stats = camera_manager.take_summary()
    if vision_stats:
        item.vision_stats = json.dumps(vision_stats)
    db.commit()
    return {"ok": True, "vision_stats": vision_stats}


@app.post("/api/interviews/{interview_id}/complete")
def complete_interview(interview_id: int, db: Session = Depends(get_db),
                       token: str = Depends(auth.require_login)):
    interview = find_interview(db, interview_id)

    # 1) 면접 전체의 카메라 분석 결과를 요약하고, 규칙 기반 태도 피드백을 만든다
    vision_summary = camera_manager.finish_collecting()
    if vision_summary is None and interview.vision_summary:
        vision_summary = load_json(interview.vision_summary)  # 다시 시도하는 경우 기존 값 사용
    interview.vision_summary = json.dumps(vision_summary) if vision_summary else None
    interview.vision_feedback = json.dumps(make_vision_feedback(vision_summary), ensure_ascii=False)
    db.commit()

    # 2) AI에게 답변 평가를 요청한다 (카메라 분석 요약도 함께 전달)
    try:
        result = ai.evaluate_interview(interview, vision_summary)
    except Exception as error:
        raise HTTPException(status_code=502, detail=f"AI 피드백 생성에 실패했습니다: {error}")

    # 3) 질문별 피드백과 점수를 저장한다
    scores = []
    for item, feedback in zip(interview.answers, result["answers"]):
        item.feedback = json.dumps(feedback, ensure_ascii=False)
        item.score = feedback.get("score", 0)
        scores.append(item.score)

    interview.average_score = round(sum(scores) / len(scores), 1) if scores else 0
    interview.overall_feedback = result.get("overall", "")
    interview.status = "completed"
    interview.completed_at = datetime.now()
    interview.is_demo = ai.is_demo_mode()
    db.commit()
    return interview_to_dict(interview, include_answers=True)


@app.get("/api/interviews")
def list_interviews(db: Session = Depends(get_db), token: str = Depends(auth.require_login)):
    interviews = db.query(Interview).order_by(Interview.created_at.desc()).all()
    return [interview_to_dict(i) for i in interviews]


@app.get("/api/interviews/{interview_id}")
def get_interview(interview_id: int, db: Session = Depends(get_db),
                  token: str = Depends(auth.require_login)):
    return interview_to_dict(find_interview(db, interview_id), include_answers=True)


@app.delete("/api/interviews/{interview_id}")
def delete_interview(interview_id: int, db: Session = Depends(get_db),
                     token: str = Depends(auth.require_login)):
    db.delete(find_interview(db, interview_id))
    db.commit()
    return {"ok": True}


# ---------------------------------------------------------------------------
# 4. 성장 분석 / 대시보드 통계
# ---------------------------------------------------------------------------

@app.get("/api/stats")
def get_stats(db: Session = Depends(get_db), token: str = Depends(auth.require_login)):
    completed = (
        db.query(Interview)
        .filter(Interview.status == "completed")
        .order_by(Interview.created_at.asc())
        .all()
    )
    history = [interview_to_dict(i) for i in completed]
    scores = [i["average_score"] for i in history if i["average_score"] is not None]
    postures = [i["posture_score"] for i in history if i["posture_score"] is not None]

    return {
        "total_interviews": len(history),
        "materials_count": db.query(Material).count(),
        "average_score": round(sum(scores) / len(scores), 1) if scores else None,
        "average_posture": round(sum(postures) / len(postures), 1) if postures else None,
        "recent": history[-1] if history else None,
        "history": history,
    }


# ---------------------------------------------------------------------------
# 5. 카메라 / 영상 분석
# ---------------------------------------------------------------------------

@app.get("/api/camera/sources")
def camera_sources(token: str = Depends(auth.require_login)):
    """사용 가능한 카메라 종류를 알려준다 (picamera2가 설치된 라즈베리파이인지 확인)"""
    try:
        import picamera2  # noqa: F401
        picamera_available = True
    except ImportError:
        picamera_available = False
    return {"picamera": picamera_available, "webcam": True}


@app.post("/api/camera/start")
def camera_start(request: CameraRequest, token: str = Depends(auth.require_login)):
    if request.source not in ("picamera", "webcam"):
        raise HTTPException(status_code=400, detail="카메라 종류가 올바르지 않습니다.")
    try:
        camera_manager.start(request.source)
    except RuntimeError as error:
        raise HTTPException(status_code=500, detail=str(error))
    return camera_manager.get_status()


@app.post("/api/camera/stop")
def camera_stop(token: str = Depends(auth.require_login)):
    camera_manager.stop()
    return camera_manager.get_status()


@app.get("/api/camera/status")
def camera_status(token: str = Depends(auth.require_login)):
    """가장 최근 프레임의 분석 결과 (프론트엔드가 0.5초마다 요청)"""
    return camera_manager.get_status()


@app.get("/api/camera/stream")
async def camera_stream(token: str = ""):
    """분석 결과가 그려진 영상을 MJPEG 방식(JPEG 사진을 연속으로 보내는 방식)으로 전송한다.
    <img> 태그는 헤더를 보낼 수 없어서 토큰을 주소(?token=...)로 받는다."""
    if token not in auth.active_tokens:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다.")

    async def generate_frames():
        while camera_manager.running:
            jpeg = camera_manager.latest_jpeg
            if jpeg is not None:
                yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + jpeg + b"\r\n"
            await asyncio.sleep(0.05)  # 초당 최대 20장

    return StreamingResponse(generate_frames(), media_type="multipart/x-mixed-replace; boundary=frame")
