from config import OPENAI_API_KEY, OPENAI_MODEL
from openai import OpenAI
import json

client = OpenAI(
  api_key=OPENAI_API_KEY, 
)

# math_books_db.json 불러오기
try:
    with open('math_books_db.json', 'r', encoding='utf-8') as f:
        MATH_BOOK_DB = json.load(f)

    SORTED_BOOK_KEYS = sorted(MATH_BOOK_DB.keys(), key=len, reverse=True)
    
    print(f"성공: math_books_db.json 로드 완료. (총 {len(SORTED_BOOK_KEYS)}권)")

except FileNotFoundError:
    print("오류: math_books_db.json 파일을 찾을 수 없습니다.")
    MATH_BOOK_DB = {}
    SORTED_BOOK_KEYS = []
except json.JSONDecodeError:
    print("오류: math_books_db.json 파일 형식이 잘못되었습니다.")
    MATH_BOOK_DB = {}
    SORTED_BOOK_KEYS = []


PROMPT_TEMPLATE = """
    당신은 11-17세(중1~고3) 학생을 위한 수학 교육 과제 분석 AI 전문가입니다.
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

    ### 3. 퀘스트 유형 분류 (quest_type)
    퀘스트의 출처나 성격을 분류합니다.
    <Context: Book Information> 섹션에 정보가 제공된 경우, 해당 정보를 **최우선으로** 사용하십시오.
    정보가 제공되지 않았거나 교재명이 없는 경우(예: '프린트물', '개념노트 정리'), 퀘스트의 내용(문제 형식, 난이도)을 기반으로 가장 적절한 유형을 추론하여 'textbook', 'problem-solving book', 'advanced book' 중 하나로 분류하고, 어디에도 속하지 않으면 'other'로 분류합니다.
    - textbook: 개념 학습 및 기본 예제 중심
    - problem-solving book: 다양한 유형의 문제 풀이 훈련 중심
    - advanced book: 높은 난이도의 심화 문제 및 경시 유형 중심
    - other: 위 세 가지로 분류하기 어려운 경우

    ## <Context: Book Information>
    {BOOK_INFO}
    
    ## <Quest Content>
    {QUEST_CONTENT}

    ## <Output Format>
    반드시 다음 JSON 구조를 따라야 하며, 그 외의 설명은 포함하지 마십시오.
    {{
    "cognitive_process_score": <1에서 6까지의 정수>,
    "effort_score": <1에서 10까지의 정수>,
    "quest_type": "<textbook | problem-solving book | advanced book | other 중 하나>",
    "analysis_reason": "cognitive_process_score, effort_score, quest_type 각각에 대한 구체적인 판단 근거를 1~2문장으로 요약하여 작성."
    }}
"""

# quest_text -> 보상 추출
def questAnalyzer(quest_text: str) -> dict:

    book_info_str = "제공된 교재 정보 없음. 퀘스트 내용을 바탕으로 추론하세요."
    found_book_type = None

    for book_name in SORTED_BOOK_KEYS:
        if book_name in quest_text:
            found_book_data = MATH_BOOK_DB[book_name]
            found_book_type = found_book_data.get("type", "unknown") # DB에 'type'이 없을 경우 대비
            found_book_target = found_book_data.get("target", "알 수 없음")

            book_info_str = (
                            f"퀘스트 출처 교재는 '{book_name}'(으)로 확인됩니다. "
                            f"이 교재는 '{found_book_target}' 학생을 대상으로 하는 "
                            f"'{found_book_type}' 유형으로 사전 분류되었습니다."
                        )
            break

    prompt = PROMPT_TEMPLATE.format(
        BOOK_INFO=book_info_str,
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
    
    
# 기본 보상 계산
def baseRewardCalculator(analysis: dict):
    cognitive=analysis['cognitive_process_score']
    effort=analysis['effort_score']

    exploration_data = (cognitive ** 2) * 5 + effort * 2
    coral=effort * 5 + cognitive * 2

    return exploration_data, coral