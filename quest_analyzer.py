from config import OPENAI_API_KEY, OPENAI_MODEL
from openai import OpenAI
import json

# ----------------------------------------------------------------------
# 1. 초기 설정
# ----------------------------------------------------------------------

client = OpenAI(
  api_key=OPENAI_API_KEY, 
)

# ----------------------------------------------------------------------
# 2. llm 호출 및 Quest Analyze
# ----------------------------------------------------------------------

PROMPT_TEMPLATE = """
    당신은 한국 중/고등학생을 위한 수학 교육 과제 분석 AI 전문가입니다.
    주어진 <Quest Content>를 아래의 <Scoring Criteria>에 따라 정밀하게 분석하세요.
    모든 분석 결과는 반드시 <Output Format>에 맞는 JSON 형식으로만 응답해야 합니다.

    ## <Scoring Criteria>

    ### 1. 블룸 분류 기준 (cognitive_process_score)
    퀘스트가 요구하는 주된 인지 과정을 1~6점 척도로 평가합니다.
    - 1점 (기억): 단순 정보 회상 (예: 공식 암기, 용어 정의)
    - 2점 (이해): 개념을 자신의 말로 설명, 번역, 예시 들기 (예: 개념 설명, 그래프 해석)
    - 3점 (적용): 배운 공식, 개념, 절차를 *새로운* 문제 상황에 사용 (예: 일반적인 유형 문제 풀이)
    - 4점 (분석): 문제를 여러 구성요소로 분해, 요소 간의 관계나 숨겨진 패턴 파악 (예: 복합 문제의 조건 분석, 증명 문제의 구조 파악)
    - 5점 (평가): 여러 해결책이나 주장의 논리적 타당성을 검증, 비판, 대안 비교 (예: 풀이 과정의 오류 찾기, 두 가지 풀이법 비교)
    - 6점 (창안): 새로운 문제 생성, 독창적인 해결 전략 설계, 여러 개념을 융합하여 새로운 산출물 제작 (예: 연계 문제 만들기)

    ### 2. 예상 노력 점수 (effort_score)
    해당 학년의 평균적인 학생이 퀘스트를 완료하는 데 필요한 예상 시간을 1~10점 척도로 평가합니다.
    - 1점: ~5분 (단순 확인 문제)
    - 2점: ~10분
    - 3점: ~15분
    - 4점: ~20분
    - 5점: ~30분 (표준적인 문제 세트)
    - 6점: ~45분
    - 7점: ~1시간 (다소 복잡하거나 문항 수가 많음)
    - 8점: ~1시간 30분
    - 9점: ~2시간
    - 10점: 2시간 초과 (매우 어렵거나 분량이 많은 프로젝트형 과제)

    ### 3. 퀘스트 난이도
    아래의 <difficulty_score>는 학생의 담당 선생님이 다음 기준에 따라 결정한 과제의 난이도입니다.
    - 1점 (쉬움/개념 확인): 수업이나 교재에서 배운 핵심 개념이나 공식을 그대로 기억해서 풀 수 있는 문제(예: 일반적인 문제집의 '개념 체크', '보기' 문제)
    - 2점 (기본/유형 적용): 배운 개념을 직접적으로 적용하는 가장 대표적인 유형의 문제(예: 쎈 B스텝 - 하)
    - 3점 (보통/복합 응용): 두 가지 이상의 개념이 함께 사용되거나, 문제의 조건을 한 번 더 생각해야 하는 응용 문제(예: 쎈 B스텝 - 중/상)
    - 4점 (어려움/심화 분석): 문제의 구조를 분석하고 숨겨진 조건을 찾아야 하는 본격적인 심화 문제(예: 쎈 C스텝)
    - 5점 (매우 어려움/창의적 해결): 기존 풀이법을 넘어서는 창의적인 아이디어가 필요하거나, 여러 단계를 거쳐 논리적으로 증명/추론해야 하는 최고난도 문제(예: 모의고사 킬러문항)

    ## <difficulty_score>
    {DIFFICULTY_SCORE}
    
    ## <Quest Content>
    {QUEST_CONTENT}

    ## <Output Format>
    반드시 다음 JSON 구조를 따라야 하며, 그 외의 설명은 포함하지 마십시오.
    {{
    "cognitive_process_score": <1에서 6까지의 정수>,
    "effort_score": <1에서 10까지의 정수>,
    "analysis_reason": "cognitive_process_score, effort_score, quest_type 각각에 대한 구체적인 판단 근거를 1~2문장으로 요약하여 작성."
    }}
"""

# quest_text -> 보상 추출
def quest_analyzer(quest_text: str) -> dict:

    ### 선생님 난이도 input 들어오면 여기에 할당
    ### 선생님이 볼 수 있는 난이도 설명은 프론트에서
    difficulty_score = None

    prompt = PROMPT_TEMPLATE.format(
        DIFFICULTY_SCORE=difficulty_score,
        QUEST_CONTENT=quest_text
    )

    message = {"role": "system", "content": prompt}

    # llm 호출
    try:
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[message],
            temperature = 0.3,
            top_p = 0.9
        )
        try:
            result_dict = json.loads(response.choices[0].message.content)
            return result_dict
        except json.JSONDecodeError:
            print(f"오류: JSON으로 파싱 실패. 응답: {response}")
            return {"error": "Failed to parse LLM response", "raw_response": response}
    except Exception as e:
        print(f"Error: {e}")
        return {"error": f"{e}"}