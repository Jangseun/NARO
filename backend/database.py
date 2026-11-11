# database.py
# SQLite 데이터베이스 연결과 테이블(모델) 정의를 담당하는 파일

from datetime import datetime

from sqlalchemy import create_engine, Column, Integer, String, Text, Float, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

# backend 폴더 안에 naro.db 파일이 만들어진다
DATABASE_URL = "sqlite:///./naro.db"

# check_same_thread=False: FastAPI는 여러 스레드에서 DB를 사용하므로 SQLite 제한을 풀어 준다
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False)
Base = declarative_base()


class User(Base):
    """로그인 사용자 (NARO는 개인용이라 1명만 사용)"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)  # 비밀번호 원문이 아닌 해시값만 저장
    salt = Column(String, nullable=False)


class Material(Base):
    """면접 준비 자료 (자기소개서, 기업 정보 등)"""
    __tablename__ = "materials"

    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    type = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.now)


class Interview(Base):
    """모의면접 1회"""
    __tablename__ = "interviews"

    id = Column(Integer, primary_key=True)
    company = Column(String, nullable=False)
    position = Column(String, nullable=False)
    interview_type = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    completed_at = Column(DateTime, nullable=True)
    status = Column(String, default="in_progress")  # in_progress 또는 completed
    average_score = Column(Float, nullable=True)
    overall_feedback = Column(Text, nullable=True)
    vision_summary = Column(Text, nullable=True)    # 면접 전체 영상 분석 요약 (JSON 문자열)
    vision_feedback = Column(Text, nullable=True)   # 영상 분석 결과로 만든 태도 피드백
    is_demo = Column(Boolean, default=False)        # True면 실제 AI가 아닌 데모 모드로 만든 결과

    # 면접 1개에 질문/답변 여러 개가 연결된다
    answers = relationship("InterviewAnswer", back_populates="interview",
                           cascade="all, delete-orphan", order_by="InterviewAnswer.order")


class InterviewAnswer(Base):
    """면접 질문 1개와 그에 대한 답변·피드백"""
    __tablename__ = "interview_answers"

    id = Column(Integer, primary_key=True)
    interview_id = Column(Integer, ForeignKey("interviews.id"), nullable=False)
    order = Column(Integer, nullable=False)          # 질문 순서 (1, 2, 3 ...)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=True)
    feedback = Column(Text, nullable=True)           # AI 피드백 (JSON 문자열)
    score = Column(Float, nullable=True)
    vision_stats = Column(Text, nullable=True)       # 이 질문에 답하는 동안의 영상 분석 결과 (JSON 문자열)

    interview = relationship("Interview", back_populates="answers")


def get_db():
    """API 요청마다 DB 세션을 열고, 요청이 끝나면 닫는다"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
