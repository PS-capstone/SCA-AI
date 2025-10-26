import chromadb
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Any

# ----------------------------------------------------------------------
# 1. 설정 및 초기화
# ----------------------------------------------------------------------

EMBEDDING_MODEL = "BAAI/bge-m3" 
# 테스트 경로 "./chroma_store_test"
DB_PATH = "./chroma_store_test"
COLLECTION_NAME = "learning_logs_collection"

# ----------------------------------------------------------------------
# 2. 헬퍼 함수 (get_chroma_client, get_nested_value, format_to_markdown, get_metadata)
# ----------------------------------------------------------------------

# ChromaDB 초기화
def get_chroma_client():
    return chromadb.PersistentClient(path=DB_PATH)

# 중첩된 딕셔너리에서 값 가져오기
def get_nested_value(data: dict, keys: list, default: Any = "NULL") -> Any:
    current = data
    for key in keys:
        if isinstance(current, dict):
            current = current.get(key)
        else:
            return default  # 경로 중간에 딕셔너리가 아닌 값이 나오면 기본값 반환
    return current if current is not None else default

# 마크다운 변환
def format_to_markdown(data: Dict[str, Any]) -> str:
    # 1. 기본 정보 추출 및 NULL 처리
    log_id = data.get('learning_log_id', 'NULL')
    student_id = data.get('student_id', 'NULL')
    quest_type = data.get('quest_type', 'NULL')
    timestamp = data.get('learning_timestamp', 'NULL')
    modified = data.get('modified', False)
    rationale = data.get('rationale', 'NULL')

    # Markdown 헤더
    md_text = f"# 학습 로그: {log_id} (학생: {student_id})\n\n"

    # 2. 기본 정보 섹션
    md_text += "## 기본 학습 정보\n"
    md_text += f"- **퀘스트 유형:** {quest_type}\n"
    md_text += f"- **처리 시각:** {timestamp}\n"
    md_text += f"- **수정 여부:** {'✅ YES' if modified else '❌ NO'}\n"
    md_text += f"- **선정 근거:** {rationale}\n\n"

    # 3. 분석 및 평가 섹션
    analysis_data = data.get('analysis', {})
    if analysis_data:
        md_text += "## 분석 및 평가\n"
        md_text += f"- **인지 과정 점수:** {get_nested_value(analysis_data, ['cognitive_process_score'])}\n"
        md_text += f"- **노력 점수:** {get_nested_value(analysis_data, ['effort_score'])}\n"
        md_text += f"- **분석 사유:** {get_nested_value(analysis_data, ['analysis_reason'], default='')}\n\n"

    # 4. 계수 정보 섹션
    factors_data = data.get('factors', {})
    if factors_data:
        md_text += "## 적용 계수 요약\n"
        md_text += f"- **최종 계수 (Total Factor):** {get_nested_value(factors_data, ['total_factor'])}\n"
        md_text += f"- **전역 계수 (Global Factor):** {get_nested_value(factors_data, ['global_factor'])}\n"
        
        # 퀘스트 계수 상세
        quest_factors = get_nested_value(factors_data, ['quest_factors'], default={})
        if quest_factors and isinstance(quest_factors, dict):
            md_text += "### 퀘스트 유형별 계수\n"
            for q_type, q_factor in quest_factors.items():
                md_text += f"- **{q_type.title()}:** {q_factor}\n"
        md_text += "\n"

    # 5. 변경 사항 섹션 (modified: true일 때만)
    changes_data = data.get('changes', {})
    if modified and changes_data:
        md_text += "## 보정 계수 변경 상세 (Modified: ✅ YES)\n"
        
        # 전역 계수 변경
        global_change = changes_data.get('global_factor', {})
        if global_change:
            md_text += f"### 전역 계수 변화\n"
            md_text += f"- **변경 전/후:** {global_change.get('before', 'NULL')} -> {global_change.get('after', 'NULL')}\n"
            md_text += f"- **변화량:** {global_change.get('delta', 'NULL')}\n"
            
        # 퀘스트 계수 변경
        quest_change = changes_data.get('quest_factors', {})
        if quest_change:
            q_type = list(quest_change.keys())[0] if quest_change else "NULL"
            q_values = quest_change.get(q_type, {})
            md_text += f"### 퀘스트 계수 변화 ({q_type})\n"
            md_text += f"- **변경 전/후:** {q_values.get('before', 'NULL')} -> {q_values.get('after', 'NULL')}\n"
            md_text += f"- **변화량:** {q_values.get('delta', 'NULL')}\n"
        
        md_text += "\n"

    # 6. 보상 정보 섹션
    md_text += "## 보상 정보\n"
    rewards_final = data.get('rewards', {})
    base_rewards = data.get('base_rewards', {})
    
    # 기본 보상 (base_rewards)
    if base_rewards:
        md_text += "### 기본 보상\n"
        for key, value in base_rewards.items():
            md_text += f"- **{key.replace('_', ' ').title()}:** {value}\n"
    
    # 최종 보상 (rewards) - modified: false일 때 사용
    if not modified and rewards_final:
        md_text += "### 최종 지급 보상\n"
        for key, value in rewards_final.items():
            md_text += f"- **{key.replace('_', ' ').title()}:** {value}\n"
        md_text += "\n"
        
    # 보상 변경 상세 (changes.rewards) - modified: true일 때 사용
    rewards_changes = changes_data.get('rewards', {})
    if modified and rewards_changes:
        md_text += "### 보상 변경 상세\n"
        for reward_key, change_data in rewards_changes.items():
            if isinstance(change_data, dict):
                md_text += f"**{reward_key.replace('_', ' ').title()}**\n"
                md_text += f"- **변경 전/후:** {change_data.get('before', 'NULL')} -> {change_data.get('after', 'NULL')}\n"
                md_text += f"- **변화량:** {change_data.get('delta', 'NULL')}\n"
        md_text += "\n"

    # 7. 학습 파라미터 섹션
    params = data.get('learning_params', {})
    if params:
        md_text += "## 학습 파라미터\n"
        for key, value in params.items():
            md_text += f"- **{key.replace('_', ' ').title()}:** {value}\n"
        md_text += "\n"

    return md_text

# 메타데이터 추출
def get_metadata(data: Dict[str, Any]) -> Dict[str, Any]:
    # 1. 기본 식별자 및 분류 필드
    metadata = {
        "learning_log_id": data.get('learning_log_id'),
        "teacher_id": data.get("teacher_id"),
        "class_id": data.get("class_id"),
        "student_id": data.get('student_id'),
        "quest_id": data.get('quest_id'),
        "learning_timestamp": data.get('learning_timestamp'),
        "modified": data.get('modified', False)
    }

    # 2. 계수 정보
    factors_data = data.get('factors', {})
    metadata["total_factor"] = get_nested_value(factors_data, ['total_factor'])
    
    # 3. 분석 데이터 (정량적 점수)
    analysis_data = data.get('analysis', {})
    metadata["cognitive_process_score"] = get_nested_value(analysis_data, ['cognitive_process_score'])
    metadata["effort_score"] = get_nested_value(analysis_data, ['effort_score'])
    metadata["quest_type"] = get_nested_value(analysis_data, ['quest_type'])

    # 4. 수정 여부 확인 및 Global/Quest Factor 처리
    is_modified = metadata["modified"]

    if is_modified:
        # Modified: True -> changes 객체에서 after 값을 추출
        changes_data = data.get('changes', {})
        metadata["global_factor_after"] = get_nested_value(changes_data, ['global_factor', 'after'])
        
        quest_factors_change = get_nested_value(changes_data, ['quest_factors'], default={})
        if quest_factors_change and isinstance(quest_factors_change, dict):
            # changes에 기록된 퀘스트 유형의 after 값을 저장
            q_type = next(iter(quest_factors_change), None)
            if q_type:
                 metadata[f"{q_type.replace(' ', '_')}_factor_after"] = get_nested_value(quest_factors_change, [q_type, 'after'])

    else:
        # Modified: False -> factors 객체에서 최종 값 추출
        metadata["global_factor_after"] = get_nested_value(factors_data, ['global_factor'])
        quest_factors_data = get_nested_value(factors_data, ['quest_factors'], default={})
        if quest_factors_data and isinstance(quest_factors_data, dict):
            # factors에 기록된 모든 퀘스트 유형의 최종 값을 저장 (필터링 용이)
            for q_type, q_factor in quest_factors_data.items():
                metadata[f"{q_type.replace(' ', '_')}_factor_final"] = q_factor
    
    return metadata

# ----------------------------------------------------------------------
# 3. 코어 데이터 처리 함수 (add_data)
# ----------------------------------------------------------------------

# 임베딩 모델 로드
print(f"Loading embedding model: {EMBEDDING_MODEL}...")
try:
    embedding_model = SentenceTransformer(EMBEDDING_MODEL)
except Exception as e:
    print(f"Error loading model: {e}")
    exit()

# 새로운 데이터 추가
def add_data(collection, new_data: dict):
    log_id = new_data['learning_log_id']
    doc_content = format_to_markdown(new_data)
    metadata = get_metadata(new_data)
    
    vector = embedding_model.encode(doc_content, normalize_embeddings=True).tolist()
    
    collection.add(
        embeddings=[vector],
        documents=[doc_content],
        metadatas=[metadata],
        ids=[log_id]
    )

    return log_id

# ----------------------------------------------------------------------
# 4. 메인 빌드 함수(build_vectordb)
# ----------------------------------------------------------------------

# vector DB 구축
def build_vectordb(client: chromadb.Client, raw_data_list: List[dict]):
    collection=client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=None
    )

    if collection.count() > 0:
        print(f"ℹ️ Collection '{COLLECTION_NAME}'이 이미 존재하며 데이터가 있습니다. 초기 구축을 건너뜁니다.")
        return # 데이터가 이미 있으면 종료

    print("⏳ DB 초기 구축 시작...")

    for data in raw_data_list:
        add_data(collection, data)

    print(f"✅ 컬렉션 생성 완료. '{COLLECTION_NAME}'에 총 {collection.count()}개 문서 저장.")
