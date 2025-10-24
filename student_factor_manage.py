from config import *
import numpy as np
import json
from typing import Dict, Any, Optional

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
    def __init__(self, student_id: str, db_path: str):
        self.student_id = student_id
        self.storage = MockStorage(db_path) 
        
        loaded_data = self.storage.load_json(student_id)
        
        if loaded_data is None:
            self.global_factor = 1.0
            self.quest_factors: Dict[str, float] = {}
            self._save_state()
        else:
            self.global_factor = loaded_data.get("global_factor", 1.0)
            self.quest_factors = loaded_data.get("quest_factors", {})
        
        print(f"⚙️ Manager initialized for {student_id}. Global Factor: {self.global_factor:.3f}")
        return

    def _save_state(self):
        data_to_save = {
            "global_factor": self.global_factor,
            "quest_factors": self.quest_factors
        }
        self.storage.save_json(self.student_id, data_to_save)

    def getFactor(self, quest_type=None):
        if quest_type is None:
            return self.global_factor
        
        quest_factor = self.quest_factors.get(quest_type)
        if quest_factor is None:
            return self.global_factor

        return QUEST_TYPE_WEIGHT * quest_factor + GLOBAL_WEIGHT * self.global_factor


    def calculateBaseReward(self, cognitive_score: int, effort_score: int) -> Dict[str, int]:
        exploration_data = (cognitive_score ** 2) * EXPLORATION_COGNITIVE_WEIGHT + effort_score * EXPLORATION_EFFORT_WEIGHT
        coral=effort_score * CORAL_EFFORT_WEIGHT + cognitive_score * CORAL_COGNITIVE_WEIGHT

        return {"exploration_data": exploration_data, "coral": coral}

    def calculatePersonalizedReward(self, cognitive_score: int, effort_score: int, quest_type: str) -> Dict[str, Any]:
        base_reward = self.calculateBaseReward(cognitive_score, effort_score)
        factor = self.getFactor(quest_type)

        personalized_exploration = round(base_reward["exploration_data"] * factor)
        personalized_coral = round(base_reward["coral"] * factor)
        
        return {
            "exploration_data": personalized_exploration, 
            "coral": personalized_coral, 
            "factor": factor
        }

    def initializeFactor(self, student_score: int)-> None:
        initial_factor = 1.0 + (BASELINE_SCORE - student_score) / 100
        limited_factor = np.clip(initial_factor, INITIAL_FACTOR_MIN, INITIAL_FACTOR_MAX)
        self.global_factor = float(limited_factor)
        print(f"🚀 Global Factor initialized to {self.global_factor:.3f} (Score: {student_score})")
        self._save_state()

    def updateFactor(self, quest_type: str, new_global: float, new_quest: float) -> None:
        self.global_factor = new_global
        self.quest_factors[quest_type] = new_quest
        
        print(f"🔄 Factor updated: Global={new_global:.3f}, {quest_type}={new_quest:.3f}")
        
        self._save_state()