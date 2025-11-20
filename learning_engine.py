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

    def cleanup(self):
        """ChromaDB 클라이언트 정리"""
        try:
            if hasattr(self, 'chroma_client') and self.chroma_client:
                # ChromaDB 클라이언트를 명시적으로 정리
                # reset() 메서드로 모든 컬렉션 정리 (파일 핸들 해제)
                try:
                    self.chroma_client.clear_system_cache()
                except:
                    pass  # clear_system_cache가 없는 버전도 있음

                del self.chroma_client
                self.chroma_client = None

                # 가비지 컬렉션 강제 실행
                import gc
                gc.collect()

                print("[LearningEngine] ChromaDB 연결 정리 완료")
        except Exception as e:
            print(f"[LearningEngine] 정리 중 오류 (무시됨): {e}")
    
    def classify_modification(self, modification_rate:float)->str:
        """classify modification"""
        if modification_rate > OVERRIDE_THRESHOLD:
            return "OVERRIDE"
        elif modification_rate > FINE_TUNE_THRESHOLD:
            return "FINE_TUNE"
        else:
            return "MINOR" 


    def calculate_new_factors(self, student_id: str, manager: StudentFactorManager, quest_type:str,
                              ai_reward: dict, teacher_reward: dict)->dict:
        """
        두 보상(exploration_data, coral)의 가중평균으로 actual_ratio를 계산하여 새 계수를 업데이트.

        Args:
            student_id: 학생 ID
            manager: StudentFactorManager 인스턴스
            quest_type: 퀘스트 타입 (예: 'blacklabel', 'rpm')
            ai_reward: {"exploration_data": int, "coral": int}
            teacher_reward: {"exploration_data": int, "coral": int}
        """

        old_global_factor, old_quest_factors = manager._load_state(student_id)
        old_global = old_global_factor
        old_quest = old_quest_factors.get(quest_type, old_global_factor)

        if ai_reward["exploration_data"]==0.0:
            ai_reward["exploration_data"]=1.0
        if ai_reward["coral"]==0.0:
            ai_reward["coral"]=1.0
        exploration_ratio=teacher_reward["exploration_data"]/ai_reward["exploration_data"]
        coral_ratio=teacher_reward["coral"]/ai_reward["coral"]
        # 두 보상의 가중평균 계산

        actual_ratio = exploration_ratio*EXPLORATION_REWARD_WEIGHT+coral_ratio*CORAL_REWARD_WEIGHT

        # modification_rate 계산 (비율의 차이)
        modification_rate = abs(actual_ratio - 1.0)
        modification_type = self.classify_modification(modification_rate)

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
                    f"Ratio: {actual_ratio:.2f} (E:{EXPLORATION_REWARD_WEIGHT}/C:{CORAL_REWARD_WEIGHT}). "
                    f"Global: {old_global:.3f} -> {new_global:.3f}, "
                    f"Quest: {old_quest:.3f} -> {new_quest:.3f}")

        return {
            "new_global": new_global,
            "new_quest": new_quest,
            "explanation": explanation,
            "actual_ratio": actual_ratio,
            "modification_rate": modification_rate,
            "modification_type": modification_type,
            "learning_rate": learning_rate,
            "exploration_ratio": exploration_ratio,
            "coral_ratio": coral_ratio
        }

    def run_learning_cycle(self, feedback_event: dict) -> dict:
            """
            피드백 이벤트를 받아 계수 계산, DB 업데이트, 로깅을 수행.
            두 보상(exploration_data, coral)의 가중평균으로 학습.
            """
            teacher_id=feedback_event["teacher_id"]
            class_id=feedback_event["class_id"]
            student_id = feedback_event["student_id"]
            quest_id = feedback_event["quest_id"]
            quest_type = feedback_event["quest_type"]

            ai_reward = feedback_event["ai_reward"]
            teacher_reward = feedback_event["teacher_reward"]
            analysis=feedback_event["analysis"]
            
            manager = StudentFactorManager(db_path=self.student_factor_db_path)

            # 계수 업데이트 전 기존 값 저장
            old_global_factor, old_quest_factors = manager._load_state(student_id)
            old_global = old_global_factor
            old_quest = old_quest_factors.get(quest_type, old_global_factor)

            # 새로운 계수 계산 (두 보상을 dict로 전달)
            update_results = self.calculate_new_factors(
                student_id=student_id,
                manager=manager,
                quest_type=quest_type,
                ai_reward=ai_reward,
                teacher_reward=teacher_reward
            )

            # 계수 업데이트
            manager.update_factor(
                student_id=student_id,
                difficulty=quest_type,
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
                            "ai": ai_reward["exploration_data"],
                            "teacher": teacher_reward["exploration_data"],
                            "delta": teacher_reward["exploration_data"] - ai_reward["exploration_data"]
                        },
                        "coral": {
                            "ai": ai_reward["coral"],
                            "teacher": teacher_reward["coral"],
                            "delta": teacher_reward["coral"] - ai_reward["coral"]
                        }
                    }
                },
                "base_rewards": feedback_event.get("base_rewards", {}),
                "rewards": {
                    "exploration_data": teacher_reward["exploration_data"],
                    "coral": teacher_reward["coral"]
                },
                "learning_params": {
                    "actual_ratio": update_results["actual_ratio"],
                    "exploration_ratio": update_results["exploration_ratio"],
                    "coral_ratio": update_results["coral_ratio"],
                    "modification_rate": update_results["modification_rate"],
                    "modification_type": update_results["modification_type"],
                    "learning_rate": update_results["learning_rate"]
                }
            }

            # ChromaDB에 로그 저장
            storage.append_log(self.chroma_client, log_entry)

            return update_results

    def _get_learning_rate(self, modification_rate: float) -> float:
        """수정 유형에 따른 학습률 반환"""
        modification_type = self.classify_modification(modification_rate)

        if modification_type == "OVERRIDE":
            learning_rate = LEARNING_RATE_OVERRIDE
        elif modification_type == "FINE_TUNE":
            learning_rate = LEARNING_RATE_FINE_TUNE
        else:
            learning_rate = LEARNING_RATE_MINOR

        if get_weeks_since_semester_start() < COLD_START_WEEKS:
            learning_rate *= 0.5

        return learning_rate