"""
test_experiment.py

experiment.py의 세 가지 실험 함수를 테스트하는 스크립트:
1. run_factor_convergence_experiment: Factor 수렴 테스트
2. run_quest_type_experiment: 퀘스트 타입별 독립 학습 테스트
3. run_cold_start_experiment: 콜드 스타트 테스트
"""

import os
import sys
import json
import shutil
import pandas as pd
from datetime import datetime
import time
import gc

# 프로젝트 루트를 경로에 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

import config
from experiment import (
    run_factor_convergence_experiment,
    run_quest_type_experiment,
    run_cold_start_experiment
)


def cleanup_test_data():
    """테스트 데이터 디렉토리 초기화"""
    test_dirs = [
        config.TEST_QUEST_DB_PATH,
        config.TEST_LEARNING_LOG_PATH,
        config.TEST_STUDENT_FACTOR_PATH,
        config.TEST_CHROMA_PATH
    ]

    print("\n[테스트 준비] 기존 테스트 데이터 정리 중...")

    # 가비지 컬렉션을 통해 열려있는 객체 정리
    gc.collect()
    time.sleep(0.5)  # ChromaDB 연결이 완전히 닫힐 시간 제공

    for test_dir in test_dirs:
        if os.path.exists(test_dir):
            # ChromaDB 디렉토리는 특별히 처리
            if "chroma" in test_dir.lower():
                max_retries = 5  # 재시도 횟수 증가
                for retry in range(max_retries):
                    try:
                        # Windows에서는 shutil.rmtree의 onerror 핸들러 사용
                        def handle_remove_readonly(func, path, exc):
                            """읽기 전용 파일 삭제 시도"""
                            import stat
                            if not os.access(path, os.W_OK):
                                os.chmod(path, stat.S_IWUSR)
                                func(path)
                            else:
                                raise

                        shutil.rmtree(test_dir, onerror=handle_remove_readonly)
                        print(f"  - 삭제: {test_dir}")
                        break
                    except (PermissionError, OSError) as e:
                        if retry < max_retries - 1:
                            print(f"  - ChromaDB 삭제 대기 중... (시도 {retry + 1}/{max_retries})")
                            gc.collect()
                            time.sleep(2)  # 대기 시간 증가
                        else:
                            # 최종 실패 시 파일별로 삭제 시도
                            print(f"  - 경고: {test_dir} 일괄 삭제 실패. 개별 파일 삭제 시도 중...")
                            try:
                                for root, dirs, files in os.walk(test_dir, topdown=False):
                                    for name in files:
                                        file_path = os.path.join(root, name)
                                        try:
                                            os.chmod(file_path, 0o777)
                                            os.remove(file_path)
                                        except:
                                            pass
                                    for name in dirs:
                                        try:
                                            os.rmdir(os.path.join(root, name))
                                        except:
                                            pass
                                try:
                                    os.rmdir(test_dir)
                                    print(f"  - 개별 삭제 성공: {test_dir}")
                                except:
                                    print(f"  - 최종 경고: {test_dir} 일부 파일이 남아있을 수 있습니다.")
                                    print(f"    오류: {e}")
                            except Exception as e2:
                                print(f"  - 최종 경고: {test_dir} 삭제 완전 실패: {e2}")
            else:
                try:
                    shutil.rmtree(test_dir)
                    print(f"  - 삭제: {test_dir}")
                except Exception as e:
                    print(f"  - 경고: {test_dir} 삭제 실패: {e}")

    for test_dir in test_dirs:
        os.makedirs(test_dir, exist_ok=True)
        print(f"  - 생성: {test_dir}")

    print("[테스트 준비] 완료\n")


def save_test_result(df: pd.DataFrame, test_name: str):
    """테스트 결과를 CSV로 저장"""
    result_dir = "./data/test_results"
    os.makedirs(result_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{test_name}_{timestamp}.csv"
    filepath = os.path.join(result_dir, filename)

    df.to_csv(filepath, index=False, encoding='utf-8-sig')
    print(f"\n[결과 저장] {filepath}")
    return filepath


def print_dataframe_summary(df: pd.DataFrame, title: str):
    """DataFrame 요약 출력"""
    print(f"\n{'='*60}")
    print(f"{title}")
    print(f"{'='*60}")
    print(f"총 행 수: {len(df)}")
    print(f"\n첫 5개 행:")
    print(df.head().to_string())
    print(f"\n마지막 5개 행:")
    print(df.tail().to_string())
    print(f"\n기본 통계:")
    print(df.describe().to_string())
    print(f"{'='*60}\n")


def test_1_factor_convergence():
    """테스트 1: Factor 수렴 테스트"""
    print("\n" + "="*80)
    print("테스트 1: Factor 수렴 테스트")
    print("="*80)

    student_id = "convergence_test_student"

    # 동일한 퀘스트를 반복하여 factor가 수렴하는지 확인
    quest_sequence = [
        ("블랙라벨 중등 수학 1-1 10문제 풀기", "HARD"),
        ("블랙라벨 중등 수학 1-1 10문제 풀기", "HARD"),
        ("블랙라벨 중등 수학 1-1 10문제 풀기", "HARD"),
        ("블랙라벨 중등 수학 1-1 10문제 풀기", "HARD"),
        ("블랙라벨 중등 수학 1-1 10문제 풀기", "HARD"),
    ]

    # 교사가 항상 동일한 보상 값으로 수정 (exploration=100, coral=50)
    teacher_modifications = [
        (100, 50),
        (100, 50),
        (100, 50),
        (100, 50),
        (100, 50),
    ]

    df = run_factor_convergence_experiment(
        student_id=student_id,
        quest_sequence=quest_sequence,
        teacher_modifications=teacher_modifications
    )

    print_dataframe_summary(df, "Factor 수렴 테스트 결과")
    filepath = save_test_result(df, "test_1_factor_convergence")

    # 핵심 지표 확인
    print("\n[핵심 지표]")
    print(f"  - 초기 Error Rate: {df.iloc[0]['error_rate']:.4f}")
    print(f"  - 최종 Error Rate: {df.iloc[-1]['error_rate']:.4f}")
    print(f"  - Error Rate 개선: {(df.iloc[0]['error_rate'] - df.iloc[-1]['error_rate']):.4f}")
    print(f"  - 초기 Global Factor: {df.iloc[0]['factor_used_in_calc']:.4f}")
    print(f"  - 최종 Global Factor: {df.iloc[-1]['updated_global_factor']:.4f}")

    return df


def test_2_quest_type_specific():
    """테스트 2: 난이도별 독립 학습 테스트"""
    print("\n" + "="*80)
    print("테스트 2: 난이도별 독립 학습 테스트")
    print("="*80)

    student_id = "difficulty_test_student"

    # 각 난이도별로 다른 퀘스트와 교사 정답 설정
    quest_scenarios = {
        "HARD": (
            "블랙라벨 중등 수학 1-1 10문제 풀기",
            "HARD",
            (120, 60)  # exploration=120, coral=60
        ),
        "BASIC": (
            "교과서 기본 개념 문제 5문제 풀기",
            "BASIC",
            (30, 20)  # exploration=30, coral=20
        ),
        "MEDIUM": (
            "쎈 수학 문제 8문제 풀기",
            "MEDIUM",
            (80, 40)  # exploration=80, coral=40
        ),
        "VERY_HARD": (
            "최상위 심화 문제 5문제 풀기",
            "VERY_HARD",
            (150, 80)  # exploration=150, coral=80
        )
    }

    iterations_per_type = 5  # 각 타입당 5회 반복

    df = run_quest_type_experiment(
        student_id=student_id,
        quest_scenarios=quest_scenarios,
        iterations_per_type=iterations_per_type
    )

    print_dataframe_summary(df, "퀘스트 타입별 독립 학습 테스트 결과")
    filepath = save_test_result(df, "test_2_quest_type_specific")

    # 타입별 핵심 지표 확인
    print("\n[타입별 핵심 지표]")
    for quest_type in quest_scenarios.keys():
        type_df = df[df['test_type'] == quest_type]
        print(f"\n  [{quest_type}]")
        print(f"    - 초기 Error Rate: {type_df.iloc[0]['error_rate']:.4f}")
        print(f"    - 최종 Error Rate: {type_df.iloc[-1]['error_rate']:.4f}")
        print(f"    - 최종 Quest Factor: {type_df.iloc[-1]['updated_quest_factor']:.4f}")

    return df


def test_3_cold_start():
    """테스트 3: 콜드 스타트 (초기 성적별) 테스트"""
    print("\n" + "="*80)
    print("테스트 3: 콜드 스타트 (초기 성적별) 테스트")
    print("="*80)

    # 다양한 초기 성적의 학생들과 각 학생에게 적절한 교사의 기대 보상
    # 성적이 낮을수록 같은 과제에 대해 더 높은 보상을 줘야 함
    student_scenarios = {
        50: {
            "quest_text": "블랙라벨 중등 수학 1-1 10문제 풀기",
            "difficulty": "HARD",
            "teacher_answer": (130, 70),  # 하위권 학생에게는 높은 보상
            "description": "하위권 - 어려운 과제이므로 높은 보상"
        },
        65: {
            "quest_text": "블랙라벨 중등 수학 1-1 10문제 풀기",
            "difficulty": "HARD",
            "teacher_answer": (115, 60),  # 중하위권
            "description": "중하위권 - 도전적인 과제"
        },
        75: {
            "quest_text": "블랙라벨 중등 수학 1-1 10문제 풀기",
            "difficulty": "HARD",
            "teacher_answer": (100, 50),  # 중위권 - 기준
            "description": "중위권 - 적절한 수준의 과제"
        },
        85: {
            "quest_text": "블랙라벨 중등 수학 1-1 10문제 풀기",
            "difficulty": "HARD",
            "teacher_answer": (85, 45),  # 중상위권
            "description": "중상위권 - 다소 쉬운 과제"
        },
        95: {
            "quest_text": "블랙라벨 중등 수학 1-1 10문제 풀기",
            "difficulty": "HARD",
            "teacher_answer": (70, 40),  # 상위권 학생에게는 낮은 보상
            "description": "상위권 - 쉬운 과제이므로 낮은 보상"
        }
    }

    quest_count = 5  # 각 학생당 5개의 퀘스트

    all_results = []

    print(f"\n[Experiment] === 콜드 스타트 (초기 성적별) 테스트 시작 ===")

    for score, scenario in student_scenarios.items():
        print(f"\n--- [Testing Score: {score}점 - {scenario['description']}] ---")

        student_id = f"cold_start_student_{score}"

        # StudentFactorManager 초기화
        from student_factor_manage import StudentFactorManager
        manager = StudentFactorManager(db_path=config.TEST_STUDENT_FACTOR_PATH)
        manager.initialize_factor(student_id=student_id, student_score=score)

        quest_sequence = [(scenario['quest_text'], scenario['difficulty'])] * quest_count
        teacher_modifications = [scenario['teacher_answer']] * quest_count

        df = run_factor_convergence_experiment(
            student_id=student_id,
            quest_sequence=quest_sequence,
            teacher_modifications=teacher_modifications
        )

        df['initial_score'] = score
        df['teacher_expectation_exploration'] = scenario['teacher_answer'][0]
        df['teacher_expectation_coral'] = scenario['teacher_answer'][1]
        all_results.append(df)

    print(f"[Experiment] === 콜드 스타트 (초기 성적별) 테스트 종료 ===")

    df = pd.concat(all_results, ignore_index=True)

    print_dataframe_summary(df, "콜드 스타트 테스트 결과")
    filepath = save_test_result(df, "test_3_cold_start")

    # 성적별 핵심 지표 확인
    print("\n[성적별 핵심 지표]")
    for score in student_scenarios.keys():
        score_df = df[df['initial_score'] == score]
        print(f"\n  [초기 성적: {score}점 - {student_scenarios[score]['description']}]")
        print(f"    - 교사 기대 보상: {student_scenarios[score]['teacher_answer'][0]} (exploration)")
        print(f"    - 초기 AI 보상: {score_df.iloc[0]['ai_exploration']}")
        print(f"    - 최종 AI 보상: {score_df.iloc[-1]['ai_exploration']}")
        print(f"    - 초기 Error Rate: {score_df.iloc[0]['error_rate']:.4f}")
        print(f"    - 최종 Error Rate: {score_df.iloc[-1]['error_rate']:.4f}")
        print(f"    - Error Rate 개선: {(score_df.iloc[0]['error_rate'] - score_df.iloc[-1]['error_rate']):.4f}")
        print(f"    - 최종 Global Factor: {score_df.iloc[-1]['updated_global_factor']:.4f}")

    return df


def run_all_tests():
    """모든 테스트 실행"""
    print("\n" + "#"*80)
    print("# experiment.py 통합 테스트 시작")
    print("#"*80)

    # 테스트 데이터 초기화
    cleanup_test_data()

    results = {}

    try:
        # 테스트 1: Factor 수렴
        results['test_1'] = test_1_factor_convergence()

        # 각 테스트 후 데이터 정리
        cleanup_test_data()

        # 테스트 2: 퀘스트 타입별 독립 학습
        results['test_2'] = test_2_quest_type_specific()

        # 각 테스트 후 데이터 정리
        cleanup_test_data()

        # 테스트 3: 콜드 스타트
        results['test_3'] = test_3_cold_start()

        print("\n" + "#"*80)
        print("# 모든 테스트 완료!")
        print("#"*80)

        print("\n[최종 요약]")
        print(f"  - 테스트 1 (Factor 수렴): {len(results['test_1'])}개 데이터 포인트")
        print(f"  - 테스트 2 (퀘스트 타입): {len(results['test_2'])}개 데이터 포인트")
        print(f"  - 테스트 3 (콜드 스타트): {len(results['test_3'])}개 데이터 포인트")
        print(f"\n  결과 저장 위치: ./test_results/")

        return results

    except Exception as e:
        print(f"\n[ERROR] 테스트 실행 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    results = run_all_tests()

    if results:
        print("\n테스트가 성공적으로 완료되었습니다.")
    else:
        print("\n테스트 실행 중 오류가 발생했습니다.")
