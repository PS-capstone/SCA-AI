import chromadb
from typing import List, Dict, Any
from build_db import getChromaClient, addData
import json

# ----------------------------------------------------------------------
# 1. 설정 및 초기화
# ----------------------------------------------------------------------

# 테스트 경로 "./chroma_store_test"
DB_PATH = "./chroma_store_test"
COLLECTION_NAME = "learning_logs_collection"

# ----------------------------------------------------------------------
# 2. 운영 및 조회 함수(appendLog, loadAllLogs, searchLogsByMetadata, getLogById, deleteLogsById, deleteSpecificLogForStudent)
# ----------------------------------------------------------------------

# 학습 로그 추가
def appendLog(client: chromadb.Client, new_log_data: dict):
    print(f"⏳ 신규 로그 '{new_log_data['learning_log_id']}' 추가...")
    
    try:
        collection = client.get_collection(name=COLLECTION_NAME)
    except Exception:
        print(f"Error: Collection '{COLLECTION_NAME}'을 찾을 수 없습니다. DB 초기화가 필요합니다.")
        return

    log_id = addData(collection, new_log_data)
    print(f"✅ 신규 로그 '{log_id}' 추가 완료. 현재 문서 수: {collection.count()}")

# 로그 로드
def loadAllLogs(client: chromadb.Client) -> List[Dict[str, Any]]:
    try:
        collection = client.get_collection(name=COLLECTION_NAME)
    except Exception:
        print("Error: Collection을 찾을 수 없습니다.")
        return []
        
    results = collection.get(
        include=['metadatas', 'documents']
    )
    
    logs = []
    for doc, meta in zip(results['documents'], results['metadatas']):
        logs.append({"metadata": meta, "document": doc})
        
    print(f"📚 총 {len(logs)}개의 로그를 불러왔습니다.")
    return logs

# 메타데이터로 로그 로드
def searchLogsByMetadata(client: chromadb.Client, filter_dict: Dict[str, Any], n_results: int = 10) -> List[Dict[str, Any]]:

    # filter_dict (Dict): 메타데이터 필터 조건 (예: {"student_id": "A", "class_id": "T-001-C-001"})

    try:
        collection = client.get_collection(name=COLLECTION_NAME)
    except Exception:
        print(f"Error: Collection '{COLLECTION_NAME}'을 찾을 수 없습니다.")
        return []

    print(f"🔎 메타데이터 검색 시작: 필터={filter_dict}")
    
    results = collection.get(
        where=filter_dict,
        limit=n_results, # 최대 반환 개수 제한
        include=['metadatas', 'documents']
    )
    
    logs = []
    for doc, meta in zip(results['documents'], results['metadatas']):
        logs.append({"metadata": meta, "document": doc})
        
    print(f"✅ 검색 완료. 총 {len(logs)}개의 로그를 불러왔습니다.")
    return logs

# learning_log_id로 로그 내용 조회
def getLogById(client: chromadb.Client, log_id: str):
    try:
        collection = client.get_collection(name=COLLECTION_NAME)
    except Exception:
        print(f"Error: Collection '{COLLECTION_NAME}'을 찾을 수 없습니다.")
        return None

    results = collection.get(
        ids=[log_id],
        include=['metadatas', 'documents']
    )
    
    if not results['ids']:
        print(f"❌ 로그 ID '{log_id}'에 해당하는 데이터를 찾을 수 없습니다.")
        return None

    metadata = results['metadatas'][0]
    doc_content = results['documents'][0]
    
    document = doc_content if doc_content and isinstance(doc_content, str) else "N/A (Document Content is NULL)"
    
    print(f"✅ 로그 ID '{log_id}' 조회 결과:")
    print("---------------------------------------")
    print(f"📝 메타데이터:\n{json.dumps(metadata, indent=2)}")
    print(f"📄 Document:\n {document[:500]}...") # 긴 문서일 경우 500자까지 프리뷰
    print("---------------------------------------")
    
    return {"metadata": metadata, "document": doc_content}

# learning_log_id로 로그 삭제
def deleteLogsById(client: chromadb.Client, log_ids: List[str]):
    if not log_ids:
        print("⚠️ 삭제할 로그 ID 목록이 비어 있습니다. 작업을 건너릅니다.")
        return
        
    try:
        collection = client.get_collection(name=COLLECTION_NAME)
    except Exception:
        print(f"Error: Collection '{COLLECTION_NAME}'을 찾을 수 없습니다.")
        return

    # Document ID 목록을 사용하여 삭제를 요청합니다.
    collection.delete(ids=log_ids)
    
    print(f"✅ 로그 {len(log_ids)}개를 성공적으로 삭제했습니다.")

# 학생id로 검색 후 특정 로그 삭제
def deleteSpecificLogForStudent(client, student_id, target_log_id):
    # 1. 해당 학생이 소유한 로그인지 확인
    student_logs = searchLogsByMetadata(client, {"student_id": student_id}, n_results=100)
    
    if target_log_id in [log['metadata']['learning_log_id'] for log in student_logs]:
        # 2. ID 기반 삭제 함수 호출
        deleteLogsById(client, [target_log_id])
    else:
        print(f"❌ 로그 ID '{target_log_id}'는 학생 '{student_id}'의 로그가 아니거나 존재하지 않습니다.")