import os
from dotenv import load_dotenv

# 점수 범위
COGNITIVE_SCORE_MIN = 1
COGNITIVE_SCORE_MAX = 6
EFFORT_SCORE_MIN = 1
EFFORT_SCORE_MAX = 10

# 보상 계산 가중치
EXPLORATION_COGNITIVE_WEIGHT = 5
EXPLORATION_EFFORT_WEIGHT = 2
CORAL_EFFORT_WEIGHT = 5
CORAL_COGNITIVE_WEIGHT = 2

# 학습 파라미터
LEARNING_RATE_OVERRIDE = 0.3    # 20% 이상 수정
LEARNING_RATE_FINE_TUNE = 0.1   # 5-20% 수정
LEARNING_RATE_MINOR = 0.05      # 5% 이하 수정
FEEDBACK_CLASSIFICATION_THRESHOLD = 0.20

# 보정계수 범위
FACTOR_MIN = 0.5
FACTOR_MAX = 1.5
INITIAL_FACTOR_MIN = 0.75
INITIAL_FACTOR_MAX = 1.25

# 수정 유형 분류 파라미터
OVERRIDE_THRESHOLD = 0.2
FINE_TUNE_THRESHOLD = 0.05

# 초기화 파라미터
BASELINE_SCORE = 75  # 기준 성적
COLD_START_WEEKS = 3  # 학기 초 보수적 학습 기간

# 퀘스트 타입별 가중치
QUEST_TYPE_WEIGHT = 0.6
GLOBAL_WEIGHT = 0.4
### 임시 추가 난이도별 가중치
DIFFICULTY_WEIGHT = 0.6

# 두 보상(탐사 데이터, 코랄) 학습 시 가중평균 비율
EXPLORATION_REWARD_WEIGHT = 0.7  # 탐사 데이터 가중치
CORAL_REWARD_WEIGHT = 0.3        # 코랄 가중치

# 데이터 저장 경로
TEST_QUEST_DB_PATH = "./data/test_quest_factor"
TEST_LEARNING_LOG_PATH = "./data/test_learning_log"
TEST_STUDENT_FACTOR_PATH = "./data/test_student_factor"
TEST_CHROMA_PATH = "./data/test_chroma_store"

# LLM 설정
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OPENAI_MODEL='gpt-4o-mini'
GEMINI_MODEL='Gemini 2.5 Flash-Lite'

# 임베딩 모델
EMBEDDING_MODEL = "sentence-transformers/multi-qa-distilbert-cos-v1" 
COLLECTION_NAME = "learning_logs_collection"