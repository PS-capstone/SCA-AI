from config import *
import numpy as np
import json
from typing import Dict, Any, Optional, Tuple

class MockStorage:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.data_store: Dict[str, Dict[str, Any]] = {}

    def _get_filename(self, student_id: str) -> str:
        return os.path.join(self.db_path, f"{student_id}_factors.json")

    def load_json(self, student_id: str) -> Optional[Dict[str, Any]]:
        file_path = self._get_filename(student_id)
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None

    def save_json(self, student_id: str, data: Dict[str, Any]) -> None:
        file_path = self._get_filename(student_id)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
        print(f"✅ Data for student {student_id} saved to {file_path}")

# ----------------------------------------------------------------------
# StudentFactorManager class
# ----------------------------------------------------------------------
class StudentFactorManager:
    def __init__(self, db_path: str):
        self.storage = MockStorage(db_path)
        print("⚙️ Factor Manager (Stateless) initialized.")

    # 학생 데이터 로드
    def _load_state(self, student_id: str) -> Tuple[float, Dict[str, float]]:
        loaded_data = self.storage.load_json(student_id)

        if loaded_data is None:
            # 데이터가 없으면 기본값 반환
            return 1.0, {}
        else:
            # 데이터가 있으면 해당 값 반환
            global_factor = loaded_data.get("global_factor", 1.0)
            quest_factors = loaded_data.get("quest_factors", {})
            return global_factor, quest_factors

    # 학생 데이터 저장
    def _save_state(self, student_id: str, global_factor: float, quest_factors: Dict[str, float]):
        data_to_save = {
            "global_factor": global_factor,
            "quest_factors": quest_factors
        }
        self.storage.save_json(student_id, data_to_save)

    # 학생 보정계수 get
    def get_factor(self, student_id: str, difficulty: str = None) -> float:
        global_factor, quest_factors = self._load_state(student_id)

        if difficulty is None:
            return global_factor

        quest_factor = quest_factors.get(difficulty)
        if quest_factor is None:
            return global_factor

        return DIFFICULTY_WEIGHT * quest_factor + GLOBAL_WEIGHT * global_factor

    # 기본 보상 계산
    @staticmethod
    def calculate_base_reward(cognitive_score: int, effort_score: int) -> Dict[str, int]:
        exploration_data = (cognitive_score ** 2) * EXPLORATION_COGNITIVE_WEIGHT + effort_score * EXPLORATION_EFFORT_WEIGHT
        coral = effort_score * CORAL_EFFORT_WEIGHT + cognitive_score * CORAL_COGNITIVE_WEIGHT

        return {"exploration_data": exploration_data, "coral": coral}

    # 개인화 보상 계산
    def calculate_personalized_reward(self, student_id: str, cognitive_score: int, effort_score: int, difficulty: str) -> Dict[str, Any]:
        # 1. 기본 보상 계산 (Static 메서드 호출)
        base_reward = self.calculate_base_reward(cognitive_score, effort_score)

        # 2. Factor 계산
        factor = self.get_factor(student_id, difficulty)

        personalized_exploration = round(base_reward["exploration_data"] * factor)
        personalized_coral = round(base_reward["coral"] * factor)

        return {
            "exploration_data": personalized_exploration,
            "coral": personalized_coral,
            "factor": factor
        }

    # factor 초기화
    def initialize_factor(self, student_id: str, student_score: int) -> None:
        initial_factor = 1.0 + (BASELINE_SCORE - student_score) / 100
        limited_factor = np.clip(initial_factor, INITIAL_FACTOR_MIN, INITIAL_FACTOR_MAX)

        new_global_factor = float(limited_factor)
        new_quest_factors = {}

        print(f"🚀 Global Factor for {student_id} initialized to {new_global_factor:.3f} (Score: {student_score})")

        self._save_state(student_id, new_global_factor, new_quest_factors)

    # factor 업데이트
    def update_factor(self, student_id: str, difficulty: str, new_global: float, new_quest: float) -> None:
        # 현재 quest_factors 로드 (다른 difficulty 보존)
        _current_global, current_quest_factors = self._load_state(student_id)

        # 새 값으로 업데이트
        current_quest_factors[difficulty] = new_quest

        print(f"🔄 Factor updated for {student_id}: Global={new_global:.3f}, {difficulty}={new_quest:.3f}")

        self._save_state(student_id, new_global, current_quest_factors)