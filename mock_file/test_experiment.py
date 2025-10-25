
from mock_experiment import storage
from experiment import run_factor_convergence_experiment, run_quest_type_experiment, run_cold_start_experiment

if __name__ == "__main__":
    
    print("\n" + "="*70)
    print(">>> [실험 1] Factor 수렴 테스트 (student_B)")
    print("="*70)
    storage.reset_database() 
    
    quest_list = ["블랙라벨 1단원 10문제"] * 5 
    teacher_answers = [(130, 55)] * 5         
    
    df_convergence = run_factor_convergence_experiment(
        student_id="student_B", 
        quest_sequence=quest_list,
        teacher_modifications=teacher_answers
    )
    print("\n[실험 1 결과]")
    print(df_convergence[['iteration', 'quest_type', 'ai_exploration', 'teacher_exploration', 'updated_global_factor', 'updated_quest_factor']].to_string())

    
    print("\n" + "="*70)
    print(">>> [실험 2] 퀘스트 타입별 독립 학습 테스트 (student_A)")
    print("="*70)
    storage.reset_database() #
    
    scenarios = {
        'blacklabel': ("블랙라벨 10문제", (130, 55)), 
        'rpm': ("RPM 20문제", (70, 30))             
    }
    
    df_quest_type = run_quest_type_experiment(
        student_id="student_A", 
        quest_scenarios=scenarios,
        iterations_per_type=3 
    )
    print("\n[실험 2 결과]")
    print(df_quest_type[['test_type', 'iteration', 'ai_exploration', 'teacher_exploration', 'updated_global_factor', 'updated_quest_factor']].to_string())


    print("\n" + "="*70)
    print(">>> [실험 3] 콜드 스타트 (초기 성적별) 테스트")
    print("="*70)
    storage.reset_database() # DB 초기화

    df_cold_start = run_cold_start_experiment(
        initial_scores=[100, 75, 50], 
        quest_count=3, 
        fixed_quest_text="블랙라벨 10문제",
        fixed_teacher_answer=(130, 55) 
    )
    print("\n[실험 3 결과]")
    print(df_cold_start[['initial_score', 'iteration', 'ai_exploration', 'teacher_exploration', 'factor_used_in_calc', 'updated_global_factor']].to_string())

    print("\n" + "="*70)
    print(">>> 모든 실험 완료. 최종 DB 상태:")
    print("="*70)
    storage.inspect_database()