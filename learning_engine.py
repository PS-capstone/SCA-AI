import numpy as np
#from student_factor_manager import StudentFactorManager
#from storage import storage
from datetime import datetime
from config import (
    LEARNING_RATE_OVERRIDE, LEARNING_RATE_FINE_TUNE, LEARNING_RATE_MINOR, 
    COLD_START_WEEKS, 
    FACTOR_MIN, FACTOR_MAX, OVERRIDE_THRESHOLD, FINE_TUNE_THRESHOLD
)
#form config import STUDENT_FACTOR_DB_PATH, LEARNING_LOG_PATH
from mock_file.mock_learning_engine import (
    MockStudentFactorManager as StudentFactorManager, 
    get_weeks_since_semester_start,
    storage,  
    STUDENT_FACTOR_DB_PATH,  
    LEARNING_LOG_PATH
)

class LearningEngine:
    """
    학습 엔진 클래스: 피드백 이벤트를 처리하고 학생의 보정계수를 업데이트.
    """
    def __init__(self):
        self.student_factor_db_path = STUDENT_FACTOR_DB_PATH
        self.learning_log_path = LEARNING_LOG_PATH
        print(f"[LearningEngine] 초기화 완료. DB 경로: {self.student_factor_db_path}")
    
    def classify_modification(self, ai_reward: int, teacher_reward:int)->str:
        """classify modification"""
        modification_rate=abs((ai_reward - teacher_reward)/ai_reward)
        if modification_rate > OVERRIDE_THRESHOLD:
            return "OVERRIDE"
        elif modification_rate > FINE_TUNE_THRESHOLD:
            return "FINE_TUNE"
        else:
            return "MINOR" 


    def calculate_new_factors(self, student_id:str, quest_type:str, ai_reward: int, teacher_reward:int)->dict:
        manager = StudentFactorManager(student_id, db_path=self.student_factor_db_path) 
        old_global = manager.global_factor 
        old_quest = manager.quest_factors.get(quest_type, manager.global_factor) # [cite: 745]

        if ai_reward <= 0:
            actual_ratio = 1.0 
        else:
            actual_ratio = teacher_reward / ai_reward 
        
        modification_type = self.classify_modification(ai_reward, teacher_reward) 
        
        if modification_type == "OVERRIDE":
            learning_rate = LEARNING_RATE_OVERRIDE 
        elif modification_type == "FINE_TUNE":
            learning_rate = LEARNING_RATE_FINE_TUNE 
        else: 
            learning_rate = LEARNING_RATE_MINOR 

        if get_weeks_since_semester_start() < COLD_START_WEEKS: 
            learning_rate *= 0.5 

        new_global = (learning_rate * actual_ratio) + (1 - learning_rate) * old_global 
        new_quest = (learning_rate * actual_ratio) + (1 - learning_rate) * old_quest 

        new_global = np.clip(new_global, FACTOR_MIN, FACTOR_MAX) 
        new_quest = np.clip(new_quest, FACTOR_MIN, FACTOR_MAX)

        explanation = (f"Type: {modification_type} (LR: {learning_rate:.2f}), "
                    f"Ratio: {actual_ratio:.2f}. "
                    f"Global: {old_global:.3f} -> {new_global:.3f}, "
                    f"Quest: {old_quest:.3f} -> {new_quest:.3f}") 

        return manager, {
            "new_global": new_global,
            "new_quest": new_quest,
            "explanation": explanation
        }

    def run_learning_cycle(self, feedback_event: dict) -> dict:
            """
            피드백 이벤트를 받아 계수 계산, DB 업데이트, 로깅을 수행.
            """
            
            student_id = feedback_event["student_id"]
            quest_id = feedback_event["quest_id"]
            quest_type = feedback_event["quest_type"]
            ai_reward = feedback_event["ai_reward"]
            teacher_reward = feedback_event["teacher_reward"]
            
            manager, update_results = self.calculate_new_factors(
                student_id=student_id,
                quest_type=quest_type,
                ai_reward=ai_reward,
                teacher_reward=teacher_reward
            )
            
            manager.update_factor(
                quest_type=quest_type,
                new_global=update_results["new_global"],
                new_quest=update_results["new_quest"]
            )
            

            log_entry = {
                "log_timestamp": datetime.now().isoformat(),
                "student_id": student_id,
                "quest_id": quest_id,
                "quest_type": quest_type,
                "ai_reward": ai_reward,
                "teacher_reward": teacher_reward,
                "learning_details": update_results 
            }
            
            storage.append_log(self.learning_log_path, log_entry)
            
            return update_results