# SCA - 통합 학습 관리 시스템
![Python](https://img.shields.io/badge/Python-3.9+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![OpenAI](https://img.shields.io/badge/OpenAI_API-412991?style=for-the-badge&logo=openai&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)
![Pandas](https://img.shields.io/badge/Pandas-150458?style=for-the-badge&logo=pandas&logoColor=white)
![NumPy](https://img.shields.io/badge/NumPy-013243?style=for-the-badge&logo=numpy&logoColor=white)
![ChromaDB](https://img.shields.io/badge/ChromaDB-FK5113?style=for-the-badge&logo=chroma&logoColor=white)

SCA(Smart Community Academy)의 **지능형 분석 엔진**입니다.
학생의 성취도에 따른 **개인화 보상 계수(Factor)**를 계산하고, **OpenAI API**를 활용하여 퀘스트의 난이도와 교육적 가치를 자동 분석합니다.

## 주요 기능

### 1. 퀘스트 분석 (Quest Analyzer)
* **LLM 기반 분석**: OpenAI GPT 모델을 사용하여 퀘스트 텍스트를 분석합니다.
* **블룸 분류법(Bloom's Taxonomy)**: 퀘스트가 요구하는 인지 과정을 1~6점 척도로 평가합니다.
* **노력 점수(Effort Score)**: 과제 수행에 필요한 예상 시간을 예측합니다.
* **자동 난이도 검증**: 선생님이 설정한 난이도와 AI 분석 결과를 비교합니다.

### 2. 적응형 학습 엔진 (Learning Engine)
* **개인화 계수(Factor) 관리**: 학생별/난이도별 보상 가중치를 동적으로 관리합니다.
* **피드백 루프**: 교사의 실제 보상(Teacher Reward)과 AI 추천 보상(AI Reward)의 차이를 분석하여, 다음 보상 추천 시 오차를 줄이도록 계수를 자동 보정합니다.
* **ChromaDB 로깅**: 모든 학습 및 보정 이력을 벡터 DB에 저장하여 추적합니다.

### 3. 실험 및 시뮬레이션 (Experiment)
* **수렴성 테스트**: `experiment.py`를 통해 반복적인 학습 과정에서 Factor가 목표값에 수렴하는지 검증합니다.
* **데이터 분석**: **Pandas**와 **NumPy**를 활용하여 시뮬레이션 데이터를 구조화하고 분석합니다.
* **시각화**: **Streamlit**을 통해 실험 결과와 학습 곡선을 대시보드 형태로 시각화합니다.

## 기술 스택

| 분류 | 기술 | 설명 |
| :--- | :--- | :--- |
| **LLM** | **OpenAI API** | 퀘스트 내용 분석 및 메타데이터 추출 |
| **Core Logic** | **Python** | 분석 엔진 및 학습 알고리즘 구현 |
| **Data Analysis** | **Pandas, NumPy** | 학습 로그 데이터 처리 및 수치 연산 |
| **Vector DB** | **ChromaDB** | 학습 로그 및 학생 데이터 저장소 |
| **Visualization** | **Streamlit** | AI 분석 결과 및 실험 데이터 시각화 웹앱 |

## 폴더 구조
```
SCA-AI/
├── app.py                   # Streamlit 대시보드 진입점
├── config.py                # 환경 변수 및 설정 관리
├── learning_engine.py       # 핵심 학습 알고리즘 (Factor Update Logic)
├── quest_analyzer.py        # OpenAI API 연동 퀘스트 분석기
├── experiment.py            # 알고리즘 검증 및 시뮬레이션 스크립트
├── student_factor_manage.py # 학생별 Factor CRUD 관리
├── storage.py               # ChromaDB 데이터 저장 로직
├── build_db.py              # DB 초기화 및 설정
└── requirements.txt         # Python 패키지 목록
```
