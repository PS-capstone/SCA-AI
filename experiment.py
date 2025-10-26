from learning_engine import LearningEngine
import pandas as pd
from datetime import datetime
import numpy as np
from quest_analyzer import quest_analyzer
from student_factor_manage import StudentFactorManager
import config
import uuid
import json
import os

# experiment.py 전용 간단한 storage 함수들
def load_json_db(filepath: str) -> dict:
    """JSON 파일에서 데이터를 로드 (파일이 없으면 빈 dict 반환)"""
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_json_db(filepath: str, data: dict) -> None:
    """JSON 파일에 데이터를 저장"""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def generate_quest_id()->str:
    """uuid 4 기반 Ques Id 생성"""
    short_uuid=str(uuid.uuid4())[:8]
    return f"Quest_{short_uuid}"

def infer_quest_type(quest_text: str) -> str:
    """퀘스트 텍스트에서 quest_type을 추론"""
    quest_text_lower = quest_text.lower()

    if "블랙라벨" in quest_text or "blacklabel" in quest_text_lower or "black label" in quest_text_lower:
        return "blacklabel"
    elif "교과서" in quest_text or "textbook" in quest_text_lower:
        return "textbook"
    elif "rpm" in quest_text_lower:
        return "rpm"
    elif "쎈" in quest_text or "sen" in quest_text_lower:
        return "sen"
    elif "개념" in quest_text or "concept" in quest_text_lower:
        return "concept"
    elif "시험" in quest_text or "test" in quest_text_lower or "모의고사" in quest_text:
        return "test"
    else:
        return "general"

def process_quest_creation(quest_data:dict)->str:
    quest_id = generate_quest_id()
    print(f"[Experiment] 퀘스트 생성 처리: {quest_id}")
    analysis = quest_analyzer(quest_data['quest_text'])
    print(f"[Experiment] 퀘스트 분석 결과: {analysis}")

    # quest_type이 없으면 텍스트에서 추론
    if 'quest_type' not in analysis:
        analysis['quest_type'] = infer_quest_type(quest_data['quest_text'])
        print(f"[Experiment] Quest Type 추론: {analysis['quest_type']}")

    # Calculate base_reward using first student's manager (base reward is same for all)
    first_student_id = quest_data['target_students'][0]
    temp_manager = StudentFactorManager(student_id=first_student_id, db_path=config.TEST_STUDENT_FACTOR_PATH)
    base_reward = temp_manager.calculate_base_reward(
        cognitive_score=analysis['cognitive_process_score'],
        effort_score=analysis['effort_score']
    )

    personalized_reward_list=[]
    for student_id in quest_data['target_students']:
        studentFactorManager = StudentFactorManager(student_id=student_id, db_path=config.TEST_STUDENT_FACTOR_PATH)
        personalized_reward = studentFactorManager.calculate_personalized_reward(
            cognitive_score=analysis['cognitive_process_score'],
            effort_score=analysis['effort_score'],
            quest_type=analysis['quest_type']
        )
        personalized_reward_list.append({
            "student_id": student_id,
            **personalized_reward
        })
    result={
        "quest_id": quest_id,
        "analysis": analysis,
        "base_reward": base_reward,
        "personalized_rewards": personalized_reward_list
    }
    quest_db_file = config.TEST_QUEST_DB_PATH + "/quests.json"
    all_quests = load_json_db(quest_db_file)
    all_quests[quest_id] = result
    save_json_db(quest_db_file, all_quests)
    print(f"[Experiment] 퀘스트 {quest_id}가 DB에 저장되었습니다.")
    return result

        
def process_teacher_modification(quest_id: str, student_id: str,
                                teacher_exploration: int, teacher_coral: int,
                                teacher_id: str = "test_teacher",
                                class_id: str = "test_class") -> dict:
    quest_db_file = config.TEST_QUEST_DB_PATH + "/quests.json"
    all_quests = load_json_db(quest_db_file)
    quest_data = all_quests.get(quest_id)
    if not quest_data:
        raise ValueError(f"퀘스트 ID {quest_id}를 찾을 수 없습니다.")

    # 해당 학생의 AI 보상 정보 찾기
    ai_reward_info = None
    for reward_info in quest_data['personalized_rewards']:
        if reward_info['student_id'] == student_id:
            ai_reward_info = reward_info
            break

    if ai_reward_info is None:
        raise ValueError(f"{quest_id} 퀘스트에서 학생 ID {student_id}를 찾을 수 없습니다.")

    # learning_engine의 새로운 구조에 맞춘 feedback_event 생성
    feedback_event = {
        "teacher_id": teacher_id,
        "class_id": class_id,
        "quest_id": quest_id,
        "student_id": student_id,
        "quest_type": quest_data['analysis']['quest_type'],
        "ai_reward": {
            "exploration_data": ai_reward_info['exploration_data'],
            "coral": ai_reward_info['coral']
        },
        "teacher_reward": {
            "exploration_data": teacher_exploration,
            "coral": teacher_coral
        },
        "analysis": quest_data['analysis'],
        "base_rewards": quest_data['base_reward']
    }

    learningEngine = LearningEngine(student_factor_db_path=config.TEST_STUDENT_FACTOR_PATH)
    learning_result = learningEngine.run_learning_cycle(feedback_event)
    print(f"[Experiment] 수정 처리 완료 (학습 적용)")
    return learning_result

def run_factor_convergence_experiment(student_id: str, quest_sequence: list,
                                     teacher_modifications: list) -> pd.DataFrame:
    if len(quest_sequence) != len(teacher_modifications):
        raise ValueError("퀘스트 시퀀스와 교사 수정 리스트의 길이는 같아야 합니다.")

    manager = StudentFactorManager(student_id=student_id, db_path=config.TEST_STUDENT_FACTOR_PATH)
    current_global_factor = manager.global_factor
    print(f"\n[Experiment] === Factor 수렴 테스트 시작 (Student: {student_id}) ===")
    print(f"[Experiment] 초기 Global Factor: {current_global_factor:.4f}\n")

    results_list = []
    for i in range(len(quest_sequence)):
        quest_text = quest_sequence[i]
        teacher_exploration, teacher_coral = teacher_modifications[i]

        print(f"\n--- [Iteration {i+1} / {len(quest_sequence)}] ---")
        
        quest_data_input = {
            "quest_text": quest_text,
            "target_students": [student_id], 
        }
        
        creation_result = process_quest_creation(quest_data_input)
        
        quest_id = creation_result["quest_id"]
        quest_type = creation_result["analysis"]["quest_type"]
        
        ai_reward_info = creation_result["personalized_rewards"][0] 
        ai_exploration = ai_reward_info["exploration_data"]
        factor_used = ai_reward_info["factor"] 

        print(f"[Experiment] AI 계산 보상: {ai_exploration} (적용 Factor: {factor_used:.4f})")
        print(f"[Experiment] 교사 정답 보상: {teacher_exploration}")
        
        learning_result = process_teacher_modification(
            quest_id=quest_id,
            student_id=student_id,
            teacher_exploration=teacher_exploration,
            teacher_coral=teacher_coral
        )
        
        new_global_factor = learning_result["new_global"]
        new_quest_factor = learning_result["new_quest"]

        error_rate = (abs(teacher_exploration - ai_exploration) / teacher_exploration 
                      if teacher_exploration > 0 else 0)
        
        results_list.append({
            "iteration": i + 1,
            "quest_type": quest_type,
            "ai_exploration": ai_exploration,
            "teacher_exploration": teacher_exploration,
            "error_rate": error_rate,
            "factor_used_in_calc": factor_used, # (Quest*0.6 + Global*0.4)
            "updated_global_factor": new_global_factor,
            "updated_quest_factor": new_quest_factor
        })
        
        print(f"[Experiment] Iter {i+1}: Global Factor가 {current_global_factor:.4f} -> {new_global_factor:.4f}로 업데이트됨")
        current_global_factor = new_global_factor
        
    df = pd.DataFrame(results_list)
    print("\n[Experiment] === Factor 수렴 테스트 종료 ===")
    return df


def run_quest_type_experiment(student_id: str, 
                             quest_scenarios: dict, 
                             iterations_per_type: int) -> pd.DataFrame:
    
    all_results = []
    
    print(f"\n[Experiment] === 퀘스트 타입별 독립 학습 테스트 시작 ===")
    
    for quest_type, (quest_text, teacher_answer) in quest_scenarios.items():
        print(f"\n--- [Testing Type: {quest_type}] ---")
        
        quest_sequence = [quest_text] * iterations_per_type
        teacher_modifications = [teacher_answer] * iterations_per_type
   
        df = run_factor_convergence_experiment(
            student_id=student_id,
            quest_sequence=quest_sequence,
            teacher_modifications=teacher_modifications
        )
        
        df['test_type'] = quest_type
        all_results.append(df)

    print(f"[Experiment] === 퀘스트 타입별 독립 학습 테스트 종료 ===")
    
    return pd.concat(all_results, ignore_index=True)


def run_cold_start_experiment(initial_scores: list, 
                             quest_count: int, 
                             fixed_quest_text: str,
                             fixed_teacher_answer: tuple) -> pd.DataFrame:

    
    all_results = []
    
    print(f"\n[Experiment] === 콜드 스타트 (초기 성적별) 테스트 시작 ===")
    
    quest_sequence = [fixed_quest_text] * quest_count
    teacher_modifications = [fixed_teacher_answer] * quest_count
    
    for score in initial_scores:
        print(f"\n--- [Testing Score: {score}] ---")

        student_id = f"cold_start_student_{score}"

        manager = StudentFactorManager(student_id=student_id, db_path=config.TEST_STUDENT_FACTOR_PATH)
        manager.initialize_factor(student_score=score)
        
        df = run_factor_convergence_experiment(
            student_id=student_id,
            quest_sequence=quest_sequence,
            teacher_modifications=teacher_modifications
        )
        
        df['initial_score'] = score
        all_results.append(df)
        
    print(f"[Experiment] === 콜드 스타트 (초기 성적별) 테스트 종료 ===")
    
    return pd.concat(all_results, ignore_index=True)





    
