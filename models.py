from dataclasses import dataclass

@dataclass
class Quest:
    quest_id: str
    quest_text: str
    target_students: list
    deadline: str
    cognitive_score: int = None
    effort_score: int = None
    quest_type: str = None

@dataclass
class AnalysisResult:
    cognitive_score: int
    effort_score: int
    quest_type: str
    analysis_reason: str

@dataclass
class BaseReward:
    exploration_data: int
    coral: int

@dataclass
class PersonalizedReward:
    student_id: str
    factor: float
    exploration_data: int
    coral: int
    rationale: str
