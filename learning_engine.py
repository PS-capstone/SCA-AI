import numpy as np
from student_factor_manage import StudentFactorManager
import storage
from datetime import datetime
from config import *
from build_db import get_chroma_client

def get_weeks_since_semester_start():
    return 4

class LearningEngine:
    """
    학습 엔진 클래스: 피드백 이벤트를 처리하고 학생의 보정계수를 업데이트.
    """
    def __init__(self, student_factor_db_path: str = "./student_factor"):
        self.student_factor_db_path = student_factor_db_path
        self.chroma_client = get_chroma_client()
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


    def calculate_new_factors(self, manager: StudentFactorManager, quest_type:str, ai_reward: int, teacher_reward:int)->dict:
        old_global = manager.global_factor
        old_quest = manager.quest_factors.get(quest_type, manager.global_factor)

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

        return {
            "new_global": new_global,
            "new_quest": new_quest,
            "explanation": explanation
        }

    def run_learning_cycle(self, feedback_event: dict) -> dict:
            """
            피드백 이벤트를 받아 계수 계산, DB 업데이트, 로깅을 수행.
            """
            teacher_id=feedback_event["teacher_id"]
            class_id=feedback_event["class_id"]
            student_id = feedback_event["student_id"]
            quest_id = feedback_event["quest_id"]
            quest_type = feedback_event["quest_type"]
            ai_reward = feedback_event["ai_reward"]
            teacher_reward = feedback_event["teacher_reward"]
            analysis=feedback_event["analysis"]

            # StudentFactorManager 인스턴스 생성 (한 번만!)
            manager = StudentFactorManager(student_id, db_path=self.student_factor_db_path)

            # 계수 업데이트 전 기존 값 저장
            old_global = manager.global_factor
            old_quest = manager.quest_factors.get(quest_type, manager.global_factor)

            # 새로운 계수 계산 (manager 인스턴스를 인자로 전달)
            update_results = self.calculate_new_factors(
                manager=manager,
                quest_type=quest_type,
                ai_reward=ai_reward,
                teacher_reward=teacher_reward
            )

            # 계수 업데이트
            manager.update_factor(
                quest_type=quest_type,
                new_global=update_results["new_global"],
                new_quest=update_results["new_quest"]
            )

            learning_log_id = f"L_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{student_id}_{quest_id}"

            log_entry = {
                "learning_log_id": learning_log_id,
                "teacher_id": teacher_id,
                "class_id":class_id,
                "student_id": student_id,
                "quest_id": quest_id,
                "quest_type": quest_type,
                "learning_timestamp": datetime.now().isoformat(),
                "modified": True,
                "analysis": analysis,
                "factors":{
                    "total_factor": update_results["new_global"] * update_results["new_quest"],
                    "global_factor": update_results["new_global"],
                    "quest_factors": {
                        quest_type: update_results["new_quest"]
                    }
                },
                "changes": {
                    "global_factor": {
                        "before": old_global,
                        "after": update_results["new_global"],
                        "delta": update_results["new_global"] - old_global
                    },
                    "quest_factors": {
                        quest_type: {
                            "before": old_quest,
                            "after": update_results["new_quest"],
                            "delta": update_results["new_quest"] - old_quest
                        }
                    },
                    "rewards": {
                        "exploration_data": {
                            "before": ai_reward,
                            "after": teacher_reward,
                            "delta": teacher_reward - ai_reward
                        }
                    }
                },
                "base_rewards": feedback_event.get("base_rewards", {}),
                "rewards": {
                    "exploration_data": teacher_reward
                },
                "learning_params": {
                    "ai_reward": ai_reward,
                    "teacher_reward": teacher_reward,
                    "modification_rate": abs((teacher_reward - ai_reward) / ai_reward) if ai_reward != 0 else 0,
                    "modification_type": self.classify_modification(ai_reward, teacher_reward),
                    "learning_rate": self._get_learning_rate(ai_reward, teacher_reward)
                }
            }

            # ChromaDB에 로그 저장
            storage.append_log(self.chroma_client, log_entry)

            return update_results

    def _get_learning_rate(self, ai_reward: int, teacher_reward: int) -> float:
        """수정 유형에 따른 학습률 반환"""
        modification_type = self.classify_modification(ai_reward, teacher_reward)

        if modification_type == "OVERRIDE":
            learning_rate = LEARNING_RATE_OVERRIDE
        elif modification_type == "FINE_TUNE":
            learning_rate = LEARNING_RATE_FINE_TUNE
        else:
            learning_rate = LEARNING_RATE_MINOR

        if get_weeks_since_semester_start() < COLD_START_WEEKS:
            learning_rate *= 0.5

        return learning_rate