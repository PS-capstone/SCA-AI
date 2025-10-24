import json
from mock_learning_engine import storage
from learning_engine import LearningEngine

def simulate_teacher_feedback():
    """
    [Mock] LearningEngine.run_learning_cycle을 1회 실행하는 테스트 함수.
    "student_B" 케이스를 시뮬레이션합니다.
    """
    print("\n" + "="*50)
    print(">>> 시뮬레이션 1: [student_B] 학습 사이클 실행")
    print("="*50)
   
    engine = LearningEngine()

    feedback_event = {
        "student_id": "student_B",
        "quest_id": "Q_2025_001_mock",
        "quest_type": "blacklabel",
        "ai_reward": 110,       
        "teacher_reward": 130  
    }
    
    print("--- [1] 실행 전 DB 상태 ---")
    storage.inspect_database()
    
    print("\n--- [2] 학습 사이클 실행 중 ---")
    result = engine.run_learning_cycle(feedback_event)
    
    print("\n--- [3] 실행 결과 (반환값) ---")
    print(json.dumps(result, indent=2))
    
    print("\n--- [4] 실행 후 DB 상태 (업데이트 확인) ---")
    storage.inspect_database()
    
    print("="*50)
    print(">>> 학습 엔진 시뮬레이션 완료")
    print("="*50)

if __name__ == "__main__":
    choice=input("=== 원하는 시뮬레이션 번호를 고르시오 ===\n")
    if choice.strip() == "1":
        simulate_teacher_feedback()
    if choice.strip() == "2":
        storage.reset_database()