import json
import sys
import types
from datetime import datetime
import numpy as np
import os

current_file_path = os.path.abspath(__file__)
current_dir = os.path.dirname(current_file_path)
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

import config


STUDENT_FACTOR_DB_PATH = "data/student_factors.json"
LEARNING_LOG_PATH = "data/learning_logs.json"
QUEST_DB_PATH = "data/quests.json" 


def get_initial_database():
    return {
        STUDENT_FACTOR_DB_PATH: {
            "student_A": {"global_factor": 0.85, "quest_factors": {"blacklabel": 0.90}},
            "student_B": {"global_factor": 1.05, "quest_factors": {"blacklabel": 1.20}}
        },
        LEARNING_LOG_PATH: [],
        QUEST_DB_PATH: {} 
    }

_mock_database = get_initial_database()


class MockStorage:
    def load(self, filepath: str) -> dict:
        print(f"[MockStorage] LOAD: {filepath}")
        return _mock_database.get(filepath, {}).copy()

    def save(self, filepath: str, data: dict) -> None:
        print(f"[MockStorage] SAVE: {filepath}")
        _mock_database[filepath] = data.copy()

    def append_log(self, filepath: str, log_entry: dict) -> None:
        print(f"[MockStorage] APPEND LOG: {filepath}")
        current_logs = _mock_database.get(filepath, [])
        current_logs.append(log_entry)
        _mock_database[filepath] = current_logs

    def inspect_database(self):
        print("[MockStorage] --- CURRENT DB STATE ---")
        print(json.dumps(_mock_database, indent=2, ensure_ascii=False))
    
    def reset_database(self):
        global _mock_database
        _mock_database = get_initial_database()
        print("[MockStorage] --- DATABASE RESET ---")


storage = MockStorage()


class MockQuestAnalyzer:
    def __init__(self, model: str):
        print(f"[MockAnalyzer] 초기화 (모델: {model})")
    
    def analyze(self, quest_text: str) -> dict:
        if "RPM" in quest_text:
            return {
                "cognitive_score": 3, # 적용하기
                "effort_score": 6,  # 보통
                "quest_type": "rpm",
                "reason": "Mock analysis: 'RPM'은 3점, 6점으로 고정"
            }
        elif "교과서" in quest_text:
            return {
                "cognitive_score": 2, # 이해하기
                "effort_score": 4,  # 가벼움
                "quest_type": "textbook",
                "reason": "Mock analysis: '교과서'는 2점, 4점으로 고정"
            }
        else: # 기본값 "blacklabel"
            return {
                "cognitive_score": 4, # 분석하기
                "effort_score": 8,  # 많음
                "quest_type": "blacklabel",
                "reason": "Mock analysis: 'blacklabel'은 4점, 8점으로 고정"
            }


class MockStudentFactorManager:
    def __init__(self, student_id: str, db_path: str = STUDENT_FACTOR_DB_PATH):
        self.student_id = student_id
        self.db_path = db_path
        student_data = storage.load(self.db_path).get(self.student_id, {})
        
        self.global_factor = student_data.get('global_factor', 1.0)
        self.quest_factors = student_data.get('quest_factors', {})
        print(f"[MockManager] {student_id} 로드: global={self.global_factor}")

    def get_factor(self, quest_type: str = None) -> float:
        if quest_type and quest_type in self.quest_factors:
            quest_factor = self.quest_factors[quest_type]
            factor = (quest_factor * 0.6) + (self.global_factor * 0.4)
        else:
            factor = self.global_factor
        print(f"[MockManager] {self.student_id}의 최종 factor: {factor:.3f}")
        return factor

    def calculate_base_reward(self, cognitive_score: int, effort_score: int) -> dict:
        exploration = (cognitive_score ** 2) * 5 + (effort_score * 2)
        coral = (effort_score * 5) + (cognitive_score * 2)
        return {"exploration_data": exploration, "coral": coral}

    def calculate_personalized_reward(self, cognitive_score: int, effort_score: int, quest_type: str) -> dict:
        print(f"[MockManager] {self.student_id}의 개인화 보상 계산 중...")
        
        base_reward = self.calculate_base_reward(cognitive_score, effort_score)
        factor = self.get_factor(quest_type)
        
        personalized_exploration = round(base_reward["exploration_data"] * factor)
        personalized_coral = round(base_reward["coral"] * factor)
        
        return {
            "exploration_data": personalized_exploration,
            "coral": personalized_coral,
            "factor": factor
        }

    def update_factor(self, quest_type: str, new_global: float, new_quest: float) -> None:
        all_data = storage.load(self.db_path)
        student_data = all_data.get(self.student_id, {'quest_factors': {}})
        student_data['global_factor'] = new_global
        student_data['quest_factors'][quest_type] = new_quest
        all_data[self.student_id] = student_data
        self.global_factor = new_global
        self.quest_factors[quest_type] = new_quest
        storage.save(self.db_path, all_data)
        print(f"[MockManager] {self.student_id} 업데이트 완료: G={new_global:.3f}, Q={new_quest:.3f}")
    
    def initialize_factor(self, student_score: int):
        """학생 성적 기반으로 팩터를 계산하고 Mock DB에 저장합니다."""
        print(f"[MockManager] {self.student_id} (성적: {student_score}) 팩터 초기화...")
        initial_factor = 1.0 + (config.BASELINE_SCORE - student_score) / 100
        initial_factor = np.clip(initial_factor, 
                                 config.INITIAL_FACTOR_MIN, 
                                 config.INITIAL_FACTOR_MAX)
        
        self.global_factor = initial_factor
        self.quest_factors = {}
        
        all_data = storage.load(self.db_path)
        all_data[self.student_id] = {
            'global_factor': self.global_factor,
            'quest_factors': self.quest_factors
        }
        storage.save(self.db_path, all_data)
        print(f"[MockManager] {self.student_id}의 초기 global_factor: {self.global_factor:.3f}")

def generate_quest_id() -> str:
    mock_id = f"Q_mock_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    print(f"[MockUtil] 퀘스트 ID 생성: {mock_id}")
    return mock_id

def get_weeks_since_semester_start() -> int:
    """[Mock] 학기 시작 주차 반환. (1 = Cold Start 적용, 4 = Cold Start 미적용)"""
    return 4 