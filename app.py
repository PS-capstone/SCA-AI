import streamlit as st
import pandas as pd
import numpy as np
import os
import json
import matplotlib.pyplot as plt
import seaborn as sns
import shutil
import datetime
import plotly.graph_objects as go

# --- [로컬 모듈 임포트] ---
# 보내주신 파일들이 같은 폴더에 있어야 합니다.
from student_factor_manage import StudentFactorManager
from learning_engine import LearningEngine
from quest_analyzer import quest_analyzer
from config import TEST_STUDENT_FACTOR_PATH, TEST_CHROMA_PATH

# --------------------------------------------------------------------------
# 1. 초기 설정 및 환경 구성
# --------------------------------------------------------------------------
st.set_page_config(page_title="AI 보상 시스템 정성 테스트", layout="wide")

# 한글 폰트 설정 (그래프 깨짐 방지)
import platform
from matplotlib import font_manager, rc
plt.rcParams['axes.unicode_minus'] = False
if platform.system() == 'Darwin':
    rc('font', family='AppleGothic')
elif platform.system() == 'Windows':
    try:
        font_path = "c:/Windows/Fonts/malgun.ttf"
        font_name = font_manager.FontProperties(fname=font_path).get_name()
        rc('font', family=font_name)
    except:
        pass # 폰트 없으면 기본값

# 테스트용 DB 초기화 (세션 시작 시)
if 'init_done' not in st.session_state:
    # 폴더가 없으면 생성
    os.makedirs(os.path.dirname(TEST_STUDENT_FACTOR_PATH), exist_ok=True)
    # CSV 저장 폴더 생성
    test_results_path = os.path.join("data", "test_results")
    os.makedirs(test_results_path, exist_ok=True)

    st.session_state['init_done'] = True
    st.session_state['history'] = []  # 그래프 그리기용 기록 저장소
    # 세션 ID 생성 (초기화할 때마다 새로운 ID)
    st.session_state['session_id'] = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')

# --------------------------------------------------------------------------
# 2. 퀘스트 분석 옵션 설정
# --------------------------------------------------------------------------
USE_MOCK_ANALYZER = st.sidebar.checkbox("Mock Analyzer 사용 (API 절약)", value=False)

def mock_quest_analyzer(text, difficulty_input):
    """
    텍스트 키워드를 분석하여 고정된 점수를 반환합니다.
    실제 API를 쓰지 않으므로 비용이 0원이며, 결과가 항상 일정하여 로직 검증에 유리합니다.
    """
    text_lower = text.lower()

    # Type A: 심화/사고력 (블랙라벨, 모의고사 등) -> 인지점수 높음
    if any(x in text_lower for x in ['블랙라벨', '심화', '증명', '모의고사', '킬러', 'step3']):
        quest_type = "HARD"
    # Type B: 성실성/노가다 (쎈, RPM, 100문제 등) -> 노력점수 높음
    elif any(x in text_lower for x in ['쎈', 'rpm', '100문제', '50문제', '오답노트', '전체']):
        quest_type = "MEDIUM"
    # Type C: 기본/개념 (교과서, 예제) -> 둘 다 낮음
    else:
        quest_type = "EASY"

    return {
        "cognitive_process_score": 5 if quest_type == "HARD" else (2 if quest_type == "EASY" else 3),
        "effort_score": 6 if quest_type == "HARD" else (9 if quest_type == "MEDIUM" else 3),
        "difficulty": difficulty_input,
        "quest_type": quest_type,
        "analysis_reason": f"Mock 분석: {quest_type} 난이도로 분류되었습니다."
    }

# --------------------------------------------------------------------------
# 3. 사이드바: 교무수첩 (학생 페르소나 설정)
# --------------------------------------------------------------------------
# 학생 데이터 로드 함수
@st.cache_data
def load_students():
    """students.json 파일에서 학생 데이터를 로드합니다."""
    students_path = os.path.join(os.path.dirname(__file__), "students.json")
    with open(students_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data['students']

with st.sidebar:
    st.header("📒 교무 수첩 (학생 설정)")
    st.markdown("테스트할 학생을 선택하면 초기 성향(Cold Start)이 세팅됩니다.")

    # 학생 데이터 로드
    students = load_students()

    # 학생 선택 옵션 생성
    student_options = [f"{s['name']} ({s['group']})" for s in students]
    student_type = st.radio("학생 선택:", student_options)

    # 선택된 학생 찾기
    selected_idx = student_options.index(student_type)
    curr_std = students[selected_idx]
    st.info(f"**이름:** {curr_std['id']}\n\n**직전 성적:** {curr_std['score']}점\n\n**특징:** {curr_std['desc']}")

    # 초기화 버튼
    if st.button("🔄 이 학생 데이터 초기화 (Reset)", type="primary"):
        manager = StudentFactorManager(db_path=TEST_STUDENT_FACTOR_PATH)
        manager.initialize_factor(curr_std['id'], curr_std['score'])

        # 현재 학생의 기록만 날리기 위해 history 필터링은 복잡하니 그냥 전체 초기화 권장
        st.session_state['history'] = []
        if 'analysis' in st.session_state: del st.session_state['analysis']
        if 'rewards' in st.session_state: del st.session_state['rewards']

        # 새로운 세션 ID 생성 (초기화할 때마다 새로운 파일 생성)
        st.session_state['session_id'] = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')

        st.toast(f"{curr_std['id']} 학생 데이터가 초기화되었습니다!", icon="✅")

    # 현재 Factor 실시간 조회
    manager = StudentFactorManager(db_path=TEST_STUDENT_FACTOR_PATH)

    # 학생 factor 파일이 없으면 자동 초기화
    factor_file = os.path.join(TEST_STUDENT_FACTOR_PATH, f"{curr_std['id']}_factors.json")
    if not os.path.exists(factor_file):
        manager.initialize_factor(curr_std['id'], curr_std['score'])
        st.info(f"🆕 {curr_std['id']} 학생이 처음 선택되어 초기 보정계수({1.0 + (75 - curr_std['score']) / 100:.3f})로 자동 설정되었습니다.")

    current_factor = manager.get_factor(curr_std['id'])

    st.divider()
    st.metric(label="현재 적용 보정계수 (Factor)", value=f"x {current_factor:.3f}")
    
    if current_factor >= 1.1:
        st.success("👉 보상 성향: **매우 후함 (동기부여 중)**")
    elif current_factor <= 0.9:
        st.warning("👉 보상 성향: **엄격함 (상위권)**")
    else:
        st.info("👉 보상 성향: **표준**")

# --------------------------------------------------------------------------
# 4. 메인 화면: 퀘스트 입력 및 AI 추천
# --------------------------------------------------------------------------
st.title("AI 보상 추천 시스템 (정성 테스트)")
st.markdown(f"현재 선택된 학생: **{curr_std['id']}** (성적: {curr_std['score']}점)")

col_left, col_right = st.columns([1, 1.2])

with col_left:
    st.subheader("1. 과제 부여하기")
    
    # 시나리오 퀵 버튼
    st.markdown("👇 **테스트할 시나리오를 클릭하세요**")
    sc_cols = st.columns(3)
    if sc_cols[0].button("🔥 심화 과제\n(블랙라벨)"):
        st.session_state['q_text'] = "블랙라벨 2단원 step3 5문제 풀고 증명 서술하기"
        st.session_state['diff'] = "HARD"
    if sc_cols[1].button("💦 성실 과제\n(쎈 50문제)"):
        st.session_state['q_text'] = "쎈수학 B단계 1번부터 50번까지 풀기 (오답노트 포함)"
        st.session_state['diff'] = "MEDIUM"
    if sc_cols[2].button("🌱 기본 과제\n(교과서)"):
        st.session_state['q_text'] = "교과서 30p 예제 문제 읽고 풀기"
        st.session_state['diff'] = "EASY"

    # 텍스트 입력창 (수정 가능)
    quest_text = st.text_area("과제 내용 입력", value=st.session_state.get('q_text', ""), height=100)
    difficulty = st.selectbox("선생님 지정 난이도", ["EASY", "BASIC", "MEDIUM", "HARD", "VERY_HARD"], 
                              index=["EASY", "BASIC", "MEDIUM", "HARD", "VERY_HARD"].index(st.session_state.get('diff', "MEDIUM")))

    # 분석 버튼
    if st.button("✨ AI 분석 및 보상 산출", use_container_width=True):
        if not quest_text:
            st.error("과제 내용을 입력해주세요.")
        else:
            # 1. 퀘스트 분석 실행 (Mock 또는 실제 API)
            with st.spinner("퀘스트 분석 중..."):
                if USE_MOCK_ANALYZER:
                    analysis = mock_quest_analyzer(quest_text, difficulty)
                else:
                    analysis = quest_analyzer(quest_text, difficulty)

            # 에러 체크
            if "error" in analysis:
                st.error(f"분석 실패: {analysis['error']}")
            else:
                st.session_state['analysis'] = analysis
                # 분석 ID 생성 (입력 필드 초기화를 위해)
                st.session_state['analysis_id'] = datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')

                # 2. 보상 계산 (StudentFactorManager 사용)
                # (1) 기본 보상 (누구나 똑같은 값)
                base_rewards = manager.calculate_base_reward(
                    analysis['cognitive_process_score'],
                    analysis['effort_score']
                )
                # (2) 개인화 보상 (이 학생만을 위한 값)
                # quest_type은 분석 결과의 difficulty를 사용
                personalized = manager.calculate_personalized_reward(
                    curr_std['id'],
                    analysis['cognitive_process_score'],
                    analysis['effort_score'],
                    analysis.get('difficulty', difficulty)
                )

                st.session_state['rewards'] = {
                    "base": base_rewards,
                    "ai": personalized
                }

# --------------------------------------------------------------------------
# 5. 결과 확인 및 피드백 (Feedback Loop)
# --------------------------------------------------------------------------
with col_right:
    if 'rewards' in st.session_state and 'analysis' in st.session_state:
        st.subheader("2. AI 추천 보상")
        
        ai_data = st.session_state['rewards']['ai']
        base_data = st.session_state['rewards']['base']
        an_data = st.session_state['analysis']

        # 분석 결과 요약 카드
        with st.expander("🔍 AI는 이 과제를 어떻게 분석했을까요?", expanded=True):
            st.markdown(f"**판단 근거:** {an_data['analysis_reason']}")
            e_col1, e_col2 = st.columns(2)
            e_col1.write(f"- 인지 점수: **{an_data['cognitive_process_score']}점**")
            e_col2.write(f"- 노력 점수: **{an_data['effort_score']}점**")

        # 보상 추천 (Big Metrics)
        st.markdown("#### 🎁 추천 포인트")
        m1, m2 = st.columns(2)
        
        # 개인화 효과(Delta) 계산
        diff_exp = ai_data['exploration_data'] - base_data['exploration_data']
        diff_coral = ai_data['coral'] - base_data['coral']
        
        m1.metric("💎 탐사 데이터", ai_data['exploration_data'], 
                  delta=f"{diff_exp} (개인화 보정)", delta_color="normal")
        m2.metric("🪸 코랄", ai_data['coral'], 
                  delta=f"{diff_coral} (개인화 보정)", delta_color="normal")
        
        st.divider()
        
        # 선생님 피드백 (수정)
        st.subheader("3. 선생님의 피드백 (학습)")
        st.caption("보상이 적절하지 않다면 값을 조정해주세요. AI가 즉시 배웁니다.")

        # 숫자 입력 필드로 변경
        # 분석 ID를 key로 사용하여 새 분석마다 입력 필드가 AI 추천값으로 초기화됨
        analysis_id = st.session_state.get('analysis_id', 'default')
        col_input1, col_input2 = st.columns(2)
        with col_input1:
            adj_exp = st.number_input("💎 탐사 데이터 수정", min_value=0, max_value=int(ai_data['exploration_data']*2.5)+50, value=ai_data['exploration_data'], step=1, key=f"exp_{analysis_id}")
        with col_input2:
            adj_coral = st.number_input("🪸 코랄 수정", min_value=0, max_value=int(ai_data['coral']*2.5)+50, value=ai_data['coral'], step=1, key=f"coral_{analysis_id}")
        
        # 확정 버튼
        if st.button("💾 확정 및 AI 학습시키기 (Click)", type="primary", use_container_width=True):
            # 학습 엔진 호출
            engine = LearningEngine(student_factor_db_path=TEST_STUDENT_FACTOR_PATH)

            # quest_id 생성 (타임스탬프 기반)
            quest_id = f"Q_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_{curr_std['id']}"

            # 학습 데이터 구성 (필수 파라미터 추가)
            feedback_event = {
                "teacher_id": "TEST_TEACHER",
                "class_id": "TEST_CLASS",
                "student_id": curr_std['id'],
                "quest_id": quest_id,
                "quest_type": an_data.get('difficulty', an_data.get('quest_type', 'MEDIUM')),
                "ai_reward": {"exploration_data": ai_data['exploration_data'], "coral": ai_data['coral']},
                "teacher_reward": {"exploration_data": adj_exp, "coral": adj_coral},
                "base_rewards": base_data,
                "analysis": an_data
            }

            # Run Learning Logic
            result = engine.run_learning_cycle(feedback_event)

            # 엔진 정리
            engine.cleanup()
            
            # 기록 저장 (그래프용)
            # 탐사 데이터와 코랄의 오차율을 각각 계산하고 평균 내기
            error_exp = abs(adj_exp - ai_data['exploration_data']) / (ai_data['exploration_data'] + 0.001) * 100
            error_coral = abs(adj_coral - ai_data['coral']) / (ai_data['coral'] + 0.001) * 100
            avg_error_rate = (error_exp + error_coral) / 2

            # 기록 데이터 구성
            record = {
                "iter": len(st.session_state['history']) + 1,
                "student": curr_std['id'],
                "ai_exp": ai_data['exploration_data'],
                "teacher_exp": adj_exp,
                "ai_coral": ai_data['coral'],
                "teacher_coral": adj_coral,
                "factor": result['new_global'],
                "error_rate": avg_error_rate,
                "error_exp": error_exp,
                "error_coral": error_coral,
                "timestamp": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }

            st.session_state['history'].append(record)

            # CSV 파일로 저장 (학생별, 세션별)
            csv_filename = f"{curr_std['id']}_{st.session_state['session_id']}.csv"
            csv_path = os.path.join("data", "test_results", csv_filename)

            # DataFrame으로 변환하여 CSV 저장
            df_save = pd.DataFrame(st.session_state['history'])
            # 현재 학생 데이터만 필터링
            df_save_student = df_save[df_save['student'] == curr_std['id']]
            df_save_student.to_csv(csv_path, index=False, encoding='utf-8-sig')

            st.toast(f"학습 완료! 오차율이 {result['modification_type']} 범위로 반영되었습니다.", icon="🎉")
            st.rerun()

# --------------------------------------------------------------------------
# 6. 하단: 실시간 학습 현황 리포트 (검증용)
# --------------------------------------------------------------------------
st.divider()
st.subheader("📈 실시간 학습 결과 리포트")

if len(st.session_state['history']) > 0:
    # 데이터프레임 변환
    df_hist = pd.DataFrame(st.session_state['history'])
    
    # 현재 학생의 데이터만 필터링 (그래프 혼선 방지)
    df_curr = df_hist[df_hist['student'] == curr_std['id']].reset_index(drop=True)
    df_curr['step'] = df_curr.index + 1
    
    if len(df_curr) > 0:
        tab1, tab2 = st.tabs(["📊 학습 곡선 (보상)", "📉 오차율 & 계수 변화"])

        with tab1:
            st.markdown("**AI 추천값이 선생님의 선택을 따라가는지 확인하세요.**")

            # 탐사 데이터 그래프
            st.markdown("##### 💎 탐사 데이터")
            fig_exp = go.Figure()
            fig_exp.add_trace(go.Scatter(x=df_curr['step'], y=df_curr['ai_exp'],
                                        mode='lines+markers', name='AI 추천 보상',
                                        line=dict(dash='dash', color='blue')))
            fig_exp.add_trace(go.Scatter(x=df_curr['step'], y=df_curr['teacher_exp'],
                                        mode='lines+markers', name='선생님 확정 보상',
                                        line=dict(color='red')))
            fig_exp.update_layout(xaxis_title="학습 횟수", yaxis_title="탐사 데이터 양",
                                 height=300, margin=dict(l=0, r=0, t=0, b=0))
            st.plotly_chart(fig_exp, use_container_width=True)

            # 코랄 그래프
            st.markdown("##### 🪸 코랄")
            fig_coral = go.Figure()
            fig_coral.add_trace(go.Scatter(x=df_curr['step'], y=df_curr['ai_coral'],
                                          mode='lines+markers', name='AI 추천 보상',
                                          line=dict(dash='dash', color='blue')))
            fig_coral.add_trace(go.Scatter(x=df_curr['step'], y=df_curr['teacher_coral'],
                                          mode='lines+markers', name='선생님 확정 보상',
                                          line=dict(color='red')))
            fig_coral.update_layout(xaxis_title="학습 횟수", yaxis_title="코랄 양",
                                   height=300, margin=dict(l=0, r=0, t=0, b=0))
            st.plotly_chart(fig_coral, use_container_width=True)

        with tab2:
            col_g1, col_g2 = st.columns(2)
            with col_g1:
                st.markdown("**오차율 감소 추이 (0%에 가까울수록 좋음)**")
                fig_err = go.Figure()
                fig_err.add_trace(go.Scatter(x=df_curr['step'], y=df_curr['error_rate'],
                                            mode='lines+markers', name='오차율',
                                            line=dict(color='red')))
                # 목표선 추가
                fig_err.add_hline(y=5.0, line_dash="dash", line_color="green",
                                 annotation_text="목표 (5%)", annotation_position="right")
                fig_err.update_layout(xaxis_title="학습 횟수", yaxis_title="오차율 (%)",
                                     height=300, margin=dict(l=0, r=0, t=20, b=0),
                                     showlegend=False)
                st.plotly_chart(fig_err, use_container_width=True)
            with col_g2:
                st.markdown("**개인 계수(Factor) 변화**")
                fig_factor = go.Figure()
                fig_factor.add_trace(go.Scatter(x=df_curr['step'], y=df_curr['factor'],
                                               mode='lines+markers', name='보정 계수',
                                               line=dict(color='green')))
                # y축 범위를 데이터에 맞춰 조정
                y_min = df_curr['factor'].min()
                y_max = df_curr['factor'].max()
                y_range = y_max - y_min
                if y_range > 0:
                    fig_factor.update_yaxes(range=[y_min - y_range * 0.1, y_max + y_range * 0.1])
                fig_factor.update_layout(xaxis_title="학습 횟수", yaxis_title="보정 계수",
                                        height=300, margin=dict(l=0, r=0, t=20, b=0),
                                        showlegend=False)
                st.plotly_chart(fig_factor, use_container_width=True)

        # 최종 요약 통계 (자동 계산)
        st.markdown("### 📋 최종 성적표 (캡처용)")
        
        avg_error = df_curr['error_rate'].mean()
        last_error = df_curr.iloc[-1]['error_rate']
        pass_count = len(df_curr[df_curr['error_rate'] < 5.0])
        
        kpi1, kpi2, kpi3 = st.columns(3)
        kpi1.metric("평균 오차율", f"{avg_error:.1f}%", delta="낮을수록 좋음", delta_color="inverse")
        kpi2.metric("최종 오차율 (마지막)", f"{last_error:.1f}%", delta="수렴 상태 확인", delta_color="inverse")
        kpi3.metric("무수정 통과 횟수", f"{pass_count}회 / {len(df_curr)}회", "신뢰도 지표")

    else:
        st.info(f"아직 {curr_std['id']} 학생에 대한 학습 기록이 없습니다.")
else:
    st.info("위에서 퀘스트를 부여하고 피드백을 주시면 학습 그래프가 나타납니다.")