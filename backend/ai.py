# ai.py
# OpenAI API를 호출해서 면접 질문을 만들고, 답변을 평가하는 파일
#
# OPENAI_API_KEY가 설정되지 않은 경우에는 '데모 모드'로 동작한다.
# 데모 모드의 질문과 피드백은 미리 정해 둔 규칙으로 만든 것이며 실제 AI 결과가 아니다.
# (화면과 DB에 is_demo 값으로 구분해서 표시한다)

import json
import os

from openai import OpenAI


def is_demo_mode():
    """API 키가 없으면 데모 모드"""
    return not os.getenv("OPENAI_API_KEY")


def ask_ai_for_json(system_prompt, user_prompt):
    """OpenAI에 질문을 보내고, JSON 형식의 답을 파이썬 딕셔너리로 돌려받는다"""
    # 환경변수 OPENAI_API_KEY를 읽는다.
    # OPENAI_BASE_URL을 적으면 OpenAI 대신 같은 형식을 지원하는 다른 AI(예: 무료 Gemini)에 연결된다.
    client = OpenAI(base_url=os.getenv("OPENAI_BASE_URL") or None)
    response = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},  # 반드시 JSON으로 답하도록 요청
        temperature=0.7,
    )
    text = response.choices[0].message.content.strip()
    # 일부 AI는 JSON을 ```json ... ``` 으로 감싸서 보내므로 감싼 부분을 떼어 낸다
    if text.startswith("```"):
        text = text.strip("`").removeprefix("json").strip()
    return json.loads(text)


# ---------------------------------------------------------------------------
# 1. 면접 질문 생성
# ---------------------------------------------------------------------------

def generate_questions(company, position, interview_type, count, materials):
    """지원 정보와 등록 자료를 바탕으로 면접 질문 목록을 만든다"""
    if is_demo_mode():
        return make_demo_questions(company, position, interview_type, count, materials)

    # 등록 자료를 하나의 글로 합쳐서 AI에게 전달한다 (너무 길면 잘라서 비용을 줄인다)
    material_text = ""
    for material in materials:
        material_text += f"\n[{material.type}] {material.title}\n{material.content[:3000]}\n"
    if not material_text:
        material_text = "(등록된 자료 없음)"

    system_prompt = (
        "너는 한국 기업의 면접관이다. 지원자의 자료를 꼼꼼히 읽고, "
        "그 사람만을 위한 구체적인 면접 질문을 만든다. 반드시 JSON으로만 답한다."
    )
    user_prompt = f"""
지원 기업: {company}
지원 직무: {position}
면접 유형: {interview_type}
질문 개수: {count}

지원자 자료:
{material_text}

규칙:
- 면접 유형에 맞는 질문을 만든다. (인성 면접: 가치관·경험·협업, 직무 면접: 직무 역량·지식, 종합 면접: 둘 다)
- 자료에 나온 구체적인 경험, 표현, 기업 정보를 질문에 직접 활용한다.
- 한 질문에는 하나만 묻는다. 고등학생도 이해할 수 있는 자연스러운 한국어로 쓴다.

출력 형식: {{"questions": ["질문1", "질문2", ...]}}
"""
    data = ask_ai_for_json(system_prompt, user_prompt)
    questions = data.get("questions", [])
    if not questions:
        raise ValueError("AI가 질문을 만들지 못했습니다.")
    return questions[:count]


def make_demo_questions(company, position, interview_type, count, materials):
    """데모 모드: 미리 만든 질문 틀에 기업명·직무명·자료 제목을 넣어서 질문을 만든다"""
    personality = [
        f"{company}에 지원하게 된 동기를 말씀해 주세요.",
        "본인의 장점과 단점을 한 가지씩 말씀해 주세요.",
        "팀으로 일하다가 갈등이 생겼을 때 어떻게 해결했는지 경험을 말씀해 주세요.",
        "가장 힘들었던 경험과 그것을 극복한 과정을 말씀해 주세요.",
        "5년 뒤 자신의 모습을 어떻게 그리고 있나요?",
    ]
    job = [
        f"{position} 직무를 수행하는 데 가장 중요한 역량은 무엇이라고 생각하나요?",
        f"{position} 직무와 관련해 준비해 온 경험을 구체적으로 말씀해 주세요.",
        f"{company}의 서비스나 제품 중 개선하고 싶은 점이 있다면 무엇인가요?",
        "최근 관심 있게 공부한 기술이나 지식이 있다면 소개해 주세요.",
        "입사 후 가장 먼저 해 보고 싶은 일은 무엇인가요?",
    ]
    questions = []
    # 자기소개서를 선택했다면 자기소개서 제목을 활용한 질문을 먼저 넣는다
    for material in materials:
        if material.type == "자기소개서":
            questions.append(f"제출하신 '{material.title}'에서 가장 강조하고 싶은 경험을 설명해 주세요.")
            break

    if interview_type == "인성 면접":
        questions += personality
    elif interview_type == "직무 면접":
        questions += job
    else:
        # 종합 면접: 인성 질문과 직무 질문을 번갈아 넣는다
        for i in range(5):
            questions.append(personality[i])
            questions.append(job[i])
    return questions[:count]


# ---------------------------------------------------------------------------
# 2. 답변 평가 (피드백)
# ---------------------------------------------------------------------------

def evaluate_interview(interview, vision_summary):
    """면접의 모든 질문/답변을 평가한다.

    돌려주는 값:
    {
      "answers": [{"score": 75, "relevance": 4, "specificity": 3, "logic": 4,
                   "good_points": "...", "improvements": "...", "better_answer": "..."}, ...],
      "overall": "면접 전체에 대한 종합 피드백"
    }
    """
    if is_demo_mode():
        return make_demo_feedback(interview)

    qa_text = ""
    for item in interview.answers:
        qa_text += f"\n질문 {item.order}: {item.question}\n답변 {item.order}: {item.answer or '(답변 없음)'}\n"

    vision_text = "카메라 분석 데이터 없음"
    if vision_summary and vision_summary.get("front_ratio") is not None:
        vision_text = (
            f"정면 응시 비율 {vision_summary['front_ratio']:.0%}, "
            f"고개 숙임 비율 {vision_summary['down_ratio']:.0%}, "
            f"고개 기울어짐 비율 {vision_summary['tilt_ratio']:.0%}, "
            f"머리 움직임 지수 {vision_summary['movement']} (0.2 미만 안정, 0.5 초과 많음), "
            f"자세 점수 {vision_summary['posture_score']}점"
        )

    system_prompt = (
        "너는 친절하지만 정확한 면접 코치다. 지원자의 답변을 평가하고 개선 방법을 알려 준다. "
        "반드시 JSON으로만 답한다."
    )
    user_prompt = f"""
지원 기업: {interview.company}
지원 직무: {interview.position}
면접 유형: {interview.interview_type}

질문과 답변:
{qa_text}

카메라 영상 분석 결과(라즈베리파이 카메라로 측정한 고개 방향/자세):
{vision_text}

각 답변을 다음 기준으로 평가한다.
- relevance: 질문 의도에 맞게 답했는가 (1~5)
- specificity: 구체적인 경험과 근거가 있는가 (1~5)
- logic: 논리적인 흐름으로 설명했는가 (1~5)
- score: 종합 점수 (0~100). 답변이 없거나 매우 짧으면 낮게 준다.
- good_points: 잘한 점 (1~2문장)
- improvements: 개선할 점 (1~2문장)
- better_answer: 지원자의 내용을 살린 개선된 답변 예시 (3~4문장)

overall에는 답변 내용과 카메라 자세 분석 결과를 함께 고려한 종합 피드백을 3~4문장으로 쓴다.

출력 형식:
{{"answers": [{{"score": 0, "relevance": 0, "specificity": 0, "logic": 0, "good_points": "", "improvements": "", "better_answer": ""}}], "overall": ""}}
answers 배열은 질문 순서대로 {len(interview.answers)}개여야 한다.
"""
    data = ask_ai_for_json(system_prompt, user_prompt)
    if len(data.get("answers", [])) != len(interview.answers):
        raise ValueError("AI 평가 결과의 개수가 질문 개수와 다릅니다.")
    return data


def make_demo_feedback(interview):
    """데모 모드: 답변 길이와 숫자 포함 여부만 보고 간단히 점수를 매긴다 (실제 AI 평가 아님)"""
    results = []
    for item in interview.answers:
        answer = (item.answer or "").strip()
        length = len(answer)
        has_number = any(ch.isdigit() for ch in answer)  # 숫자가 있으면 구체적인 근거가 있다고 본다

        if length == 0:
            score = 0
        else:
            score = min(90, 40 + length // 5 + (10 if has_number else 0))

        results.append({
            "score": score,
            "relevance": 3 if length > 30 else 1,
            "specificity": 4 if has_number else 2,
            "logic": 3 if length > 80 else 2,
            "good_points": "답변을 끝까지 작성했습니다." if length > 0 else "답변이 없습니다.",
            "improvements": "경험을 '상황-행동-결과' 순서로 정리하고, 숫자나 구체적인 사례를 넣어 보세요.",
            "better_answer": "(데모 모드에서는 개선 답변 예시를 제공하지 않습니다. OPENAI_API_KEY를 설정하면 AI가 작성합니다.)",
        })
    return {
        "answers": results,
        "overall": "데모 모드 피드백입니다. 답변 길이와 숫자 포함 여부만으로 계산한 연습용 점수이며, 실제 AI 평가가 아닙니다.",
    }
