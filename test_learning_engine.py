"""
Learning Engine Simulation Test

이 스크립트는 learning_engine의 전체 동작을 시뮬레이션합니다:
1. 초기 학생 데이터 설정
2. 피드백 이벤트 생성
3. 학습 사이클 실행
4. 계수 변화 확인
5. ChromaDB 저장 확인
"""

import os
import shutil
from learning_engine import LearningEngine
from student_factor_manage import StudentFactorManager
from build_db import get_chroma_client, build_vectordb
import storage
import json

# 테스트용 경로 설정
TEST_STUDENT_FACTOR_PATH = "./test_student_factor"
TEST_CHROMA_PATH = "./test_chroma_store"

def cleanup_test_data():
    """테스트 데이터 초기화"""
    print("\n🧹 테스트 데이터 정리 중...")
    if os.path.exists(TEST_STUDENT_FACTOR_PATH):
        shutil.rmtree(TEST_STUDENT_FACTOR_PATH)
        print(f"  ✅ {TEST_STUDENT_FACTOR_PATH} 삭제 완료")

    if os.path.exists(TEST_CHROMA_PATH):
        shutil.rmtree(TEST_CHROMA_PATH)
        print(f"  ✅ {TEST_CHROMA_PATH} 삭제 완료")

def setup_test_environment():
    """테스트 환경 설정"""
    print("\n⚙️ 테스트 환경 설정 중...")

    # 디렉토리 생성
    os.makedirs(TEST_STUDENT_FACTOR_PATH, exist_ok=True)
    print(f"  ✅ {TEST_STUDENT_FACTOR_PATH} 생성 완료")

    # ChromaDB 클라이언트 생성 및 초기화
    import chromadb

    # build_db의 DB_PATH를 임시로 변경
    import build_db
    original_db_path = build_db.DB_PATH
    build_db.DB_PATH = TEST_CHROMA_PATH

    client = chromadb.PersistentClient(path=TEST_CHROMA_PATH)

    # build_vectordb를 빈 리스트로 호출하여 컬렉션 생성
    build_vectordb(client, [])
    print(f"  ✅ ChromaDB 초기화 완료 (경로: {TEST_CHROMA_PATH})")

    # DB_PATH는 나중에 복원 (run_simulation에서)

    return client, original_db_path

def create_test_students():
    """테스트용 학생 데이터 생성"""
    print("\n👥 테스트 학생 생성 중...")

    students = {
        "student_A": {"name": "김철수", "score": 90},
        "student_B": {"name": "이영희", "score": 70},
        "student_C": {"name": "박민수", "score": 85}
    }

    for student_id, info in students.items():
        manager = StudentFactorManager(student_id, db_path=TEST_STUDENT_FACTOR_PATH)
        manager.initialize_factor(info["score"])
        print(f"  ✅ {student_id} ({info['name']}) 초기화 완료 - 성적: {info['score']}점")

    return students

def create_feedback_events():
    """피드백 이벤트 생성"""
    print("\n📝 피드백 이벤트 생성 중...")

    events = [
        {
            "teacher_id": "T_001",
            "class_id": "C_2025_Alpha",
            "student_id": "student_A",
            "quest_id": "Q_001",
            "quest_type": "blacklabel",
            "ai_reward": 84,
            "teacher_reward": 90,
            "analysis": {
                "cognitive_process_score": 4,  # PDF 예시 값
                "effort_score": 8,             # PDF 예시 값
                "quest_type": "blacklabel",
                "analysis_reason": "블랙라벨은 복합 개념 분석 필요. 10문제+오답정리는 약 90분 소요"
            },
            "base_rewards": {
                "exploration_data": 96,
                "coral": 48
            }
        },
        {
            "teacher_id": "T_001",
            "class_id": "C_2025_Alpha",
            "student_id": "student_B",
            "quest_id": "Q_001",
            "quest_type": "blacklabel",
            "ai_reward": 110,
            "teacher_reward": 130,
            "analysis": {
                "cognitive_process_score": 4,  # PDF 예시 값
                "effort_score": 8,             # PDF 예시 값
                "quest_type": "blacklabel",
                "analysis_reason": "블랙라벨은 복합 개념 분석 필요. 10문제+오답정리는 약 90분 소요"
            },
            "base_rewards": {
                "exploration_data": 96,
                "coral": 48
            }
        },
        {
            "teacher_id": "T_001",
            "class_id": "C_2025_Alpha",
            "student_id": "student_C",
            "quest_id": "Q_001",
            "quest_type": "blacklabel",
            "ai_reward": 89,
            "teacher_reward": 85,
            "analysis": {
                "cognitive_process_score": 4,  # PDF 예시 값
                "effort_score": 8,             # PDF 예시 값
                "quest_type": "blacklabel",
                "analysis_reason": "블랙라벨은 복합 개념 분석 필요. 10문제+오답정리는 약 90분 소요"
            },
            "base_rewards": {
                "exploration_data": 96,
                "coral": 48
            }
        },
        # 두 번째 퀘스트 (RPM)
        {
            "teacher_id": "T_001",
            "class_id": "C_2025_Alpha",
            "student_id": "student_B",
            "quest_id": "Q_002",
            "quest_type": "rpm",
            "ai_reward": 120,
            "teacher_reward": 150,
            "analysis": {
                "cognitive_process_score": 3,  # 예시 값 (적용하기 수준)
                "effort_score": 9,             # 예시 값 (1시간 이상)
                "quest_type": "rpm",
                "analysis_reason": "RPM 유형 문제, 1시간 이상 소요 예상"
            },
            "base_rewards": {
                "exploration_data": 105,
                "coral": 52
            }
        },
        # 세 번째 퀘스트 (blacklabel 다시)
        {
            "teacher_id": "T_001",
            "class_id": "C_2025_Alpha",
            "student_id": "student_B",
            "quest_id": "Q_003",
            "quest_type": "blacklabel",
            "ai_reward": 115,
            "teacher_reward": 118,
            "analysis": {
                "cognitive_process_score": 4,  # 예시 값 (분석하기 수준)
                "effort_score": 8.5,           # 예시 값 (90분 이상)
                "quest_type": "blacklabel",
                "analysis_reason": "블랙라벨 심화 문제, 90분 이상 소요 예상"
            },
            "base_rewards": {
                "exploration_data": 100,
                "coral": 50
            }
        }
    ]

    print(f"  ✅ 총 {len(events)}개의 피드백 이벤트 생성 완료")
    return events

def print_student_factors(student_id: str):
    """학생의 현재 계수 출력"""
    manager = StudentFactorManager(student_id, db_path=TEST_STUDENT_FACTOR_PATH)
    print(f"\n📊 [{student_id}] 현재 계수:")
    print(f"  - Global Factor: {manager.global_factor:.4f}")
    print(f"  - Quest Factors: {manager.quest_factors}")

def run_simulation():
    """전체 시뮬레이션 실행"""
    print("\n" + "="*60)
    print("🚀 Learning Engine 시뮬레이션 시작")
    print("="*60)

    # 1. 환경 초기화
    cleanup_test_data()
    client, original_db_path = setup_test_environment()

    # 2. 학생 생성
    students = create_test_students()

    # 3. 초기 계수 확인
    print("\n" + "="*60)
    print("📊 초기 계수 상태")
    print("="*60)
    for student_id in students.keys():
        print_student_factors(student_id)

    # 4. Learning Engine 초기화 (테스트용 경로 사용)
    print("\n" + "="*60)
    print("⚙️ Learning Engine 초기화")
    print("="*60)

    engine = LearningEngine(student_factor_db_path=TEST_STUDENT_FACTOR_PATH)

    # 5. 피드백 이벤트 처리
    events = create_feedback_events()

    print("\n" + "="*60)
    print("🔄 피드백 이벤트 처리 시작")
    print("="*60)

    for i, event in enumerate(events, 1):
        print(f"\n{'─'*60}")
        print(f"📌 이벤트 #{i}: {event['student_id']} - {event['quest_type']}")
        print(f"{'─'*60}")
        print(f"  Quest ID: {event['quest_id']}")
        print(f"  AI 추천 보상: {event['ai_reward']}")
        print(f"  선생님 최종 보상: {event['teacher_reward']}")
        print(f"  수정률: {abs(event['teacher_reward'] - event['ai_reward']) / event['ai_reward'] * 100:.1f}%")

        # 학습 사이클 실행
        try:
            result = engine.run_learning_cycle(event)
            print(f"\n  ✅ 학습 완료!")
            print(f"  📈 계수 변화:")
            print(f"     - New Global: {result['new_global']:.4f}")
            print(f"     - New Quest ({event['quest_type']}): {result['new_quest']:.4f}")
            print(f"  📝 설명: {result['explanation']}")
        except Exception as e:
            print(f"\n  ❌ 오류 발생: {e}")
            import traceback
            traceback.print_exc()

    # 6. 최종 계수 확인
    print("\n" + "="*60)
    print("📊 최종 계수 상태")
    print("="*60)
    for student_id in students.keys():
        print_student_factors(student_id)

    # 7. ChromaDB 로그 확인
    print("\n" + "="*60)
    print("📚 ChromaDB 저장 로그 확인")
    print("="*60)

    try:
        all_logs = storage.load_all_logs(client)
        print(f"\n  총 {len(all_logs)}개의 로그가 저장되었습니다.")

        for i, log in enumerate(all_logs, 1):
            meta = log['metadata']
            print(f"\n  [{i}] {meta.get('learning_log_id', 'N/A')}")
            print(f"      학생: {meta.get('student_id', 'N/A')}")
            print(f"      퀘스트: {meta.get('quest_id', 'N/A')} ({meta.get('quest_type', 'N/A')})")
            print(f"      수정 여부: {meta.get('modified', False)}")
    except Exception as e:
        print(f"  ⚠️ 로그 조회 중 오류: {e}")

    # 8. 특정 학생 로그 검색 테스트
    print("\n" + "="*60)
    print("🔍 학생별 로그 검색 테스트")
    print("="*60)

    try:
        student_b_logs = storage.search_logs_by_metadata(
            client,
            {"student_id": "student_B"},
            n_results=10
        )
        print(f"\n  student_B의 로그: {len(student_b_logs)}개")
        for log in student_b_logs:
            meta = log['metadata']
            print(f"    - {meta.get('quest_id', 'N/A')} ({meta.get('quest_type', 'N/A')})")
    except Exception as e:
        print(f"  ⚠️ 검색 중 오류: {e}")

    # DB_PATH 복원
    import build_db
    build_db.DB_PATH = original_db_path

    print("\n" + "="*60)
    print("✅ 시뮬레이션 완료!")
    print("="*60)
    print(f"\n📁 생성된 파일 확인:")
    print(f"  - 학생 계수 JSON: {TEST_STUDENT_FACTOR_PATH}/")
    print(f"  - ChromaDB 로그: {TEST_CHROMA_PATH}/")
    print("\n")

if __name__ == "__main__":
    run_simulation()
