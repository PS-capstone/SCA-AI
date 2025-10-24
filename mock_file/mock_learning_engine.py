import json
import copy

STUDENT_FACTOR_DB_PATH = "data/student_factors.json"
LEARNING_LOG_PATH = "data/learning_logs.json"

def get_weeks_since_semester_start() -> int:
    return 4
    

_mock_database = {
    STUDENT_FACTOR_DB_PATH: {
        "student_A": {
            "global_factor": 0.85,
            "quest_factors": {"blacklabel": 0.90}
        },
        "student_B": {
            "global_factor": 1.05,
            "quest_factors": {"blacklabel": 1.20}
        },
        "student_C": {
            "global_factor": 0.90,
            "quest_factors": {"blacklabel": 0.95}
        }
    },
    LEARNING_LOG_PATH: []
}

class MockStorage:
    """
    storage.py의 함수들을 흉내 내는 가짜(Mock) 클래스.
    실제 파일 대신 _mock_database 딕셔너리에 데이터를 읽고 쓴다.
    """
    def load(self, filepath: str) -> dict:
        print(f"[MockStorage] LOAD: {filepath}")
        if filepath not in _mock_database:
            return {}  
        return copy.deepcopy(_mock_database.get(filepath, {}))

    def save(self, filepath: str, data: dict) -> None:
        """[Mock] 딕셔너리에 데이터를 저장."""
        _mock_database[filepath] = data 

    def append_log(self, filepath: str, log_entry: dict) -> None:
        """[Mock] 딕셔너리의 리스트에 로그를 추가."""
        current_logs = _mock_database.get(filepath, [])
        current_logs.append(copy.deepcopy(log_entry)) 
        _mock_database[filepath].append(log_entry) 
        
    def load_logs(self, filepath: str) -> list:
        """[Mock] 딕셔너리에서 로그 리스트를 로드."""
        return copy.deepcopy(_mock_database.get(filepath, []))

    def reset_database(self):
        """[Mock] 테스트 간섭을 막기 위해 DB를 초기화."""
        global _mock_database
        _mock_database = {}
        print("[MockStorage] --- DATABASE RESET ---")

    def inspect_database(self):
        """[Mock] 현재 DB 상태를 확인."""
        print("[MockStorage] --- CURRENT DB STATE ---")
        print(json.dumps(_mock_database, indent=2, ensure_ascii=False))

storage = MockStorage()

class MockStudentFactorManager:
    """
    StudentFactorManager를 흉내 내는 가짜(Mock) 클래스.
    MockStorage와 상호작용하여 데이터를 읽고 씁니다.
    """
    
    def __init__(self, student_id: str, db_path: str):
        """
        초기화 시 MockStorage에서 자신의 데이터를 로드합니다.
        """
        self.student_id = student_id
        self.db_path = db_path
        
        student_data = self._load_data()
        
        self.global_factor = student_data.get('global_factor', 1.0)
        self.quest_factors = student_data.get('quest_factors', {})

    def _load_data(self) -> dict:
        """
        MockStorage에서 전체 DB를 로드한 후, 
        자신의 student_id에 해당하는 데이터를 반환합니다.
        """
        all_data = storage.load(self.db_path)
        return all_data.get(self.student_id, {})

    def update_factor(self, quest_type: str, new_global: float, new_quest: float) -> None:
        
        all_data = storage.load(self.db_path)
        
        student_data = all_data.get(self.student_id, {})
        
        student_data['global_factor'] = new_global
        if 'quest_factors' not in student_data:
            student_data['quest_factors'] = {}
        student_data['quest_factors'][quest_type] = new_quest
        
        all_data[self.student_id] = student_data
        
        storage.save(self.db_path, all_data)
              
        self.global_factor = new_global
        self.quest_factors[quest_type] = new_quest
        
        print(f"[MockManager] {self.student_id} 업데이트 완료: G={new_global:.3f}, Q={new_quest:.3f}")

