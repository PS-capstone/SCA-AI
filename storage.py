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
# 2. 운영 및 조회 함수(addData, buildVectordb, appendLog, loadLogs, getStudentData)
# ----------------------------------------------------------------------

# 로그 추가
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
def loadLogs(client: chromadb.Client) -> List[Dict[str, Any]]:
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

# 학생 데이터 조회
def getDataByStudentId(client: chromadb.Client, student_id: str) -> List[Dict[str, Any]]:
    try:
        collection = client.get_collection(name=COLLECTION_NAME)
    except Exception:
        print("Error: Collection을 찾을 수 없습니다.")
        return []
    
    results = collection.get(
        where={"student_id": student_id},
        include=['metadatas', 'documents']
    )
    
    logs = []
    for doc, meta in zip(results['documents'], results['metadatas']):
        logs.append({"metadata": meta, "document": doc})
        
    print(f"학생 ID '{student_id}'에 대한 총 {len(logs)}개의 로그를 불러왔습니다.")
    return logs

def deleteLogsByStudentId(client: chromadb.Client, student_id: str):
    print(f"🗑️ 학생 ID '{student_id}'의 로그 삭제 시작...")
    
    try:
        collection = client.get_collection(name=COLLECTION_NAME)
    except Exception:
        print(f"Error: Collection '{COLLECTION_NAME}'을 찾을 수 없습니다.")
        return

    results = collection.get(
        where={"student_id": student_id},
        include=[]
    )
    
    ids_to_delete = results.get('ids', [])
    
    if not ids_to_delete:
        print(f"⚠️ 학생 ID '{student_id}'에 해당하는 로그가 없습니다. 삭제할 항목 없음.")
        return
        
    collection.delete(ids=ids_to_delete)
    
    print(f"✅ 학생 ID '{student_id}'의 로그 {len(ids_to_delete)}개를 성공적으로 삭제했습니다.")
