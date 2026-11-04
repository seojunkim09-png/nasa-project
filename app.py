import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# 페이지 기본 설정
st.set_page_config(page_title="NASA 근지구 소행성 대시보드", page_icon="☄️", layout="wide")

# NASA API 설정 (DEMO_KEY 사용)
API_KEY = "DEMO_KEY"
NEO_URL = "https://api.nasa.gov/neo/rest/v1/feed"

@st.cache_data(ttl=3600) # 1시간 동안 데이터 캐싱 (API 호출 제한 방지)
def get_neo_data(start_date, end_date):
    params = {
        "start_date": start_date,
        "end_date": end_date,
        "api_key": API_KEY
    }
    response = requests.get(NEO_URL, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        st.error("NASA API에서 데이터를 불러오는 데 실패했습니다.")
        return None

def process_data(data):
    neo_list = []
    neos = data.get("near_earth_objects", {})
    
    for date, asteroids in neos.items():
        for asteroid in asteroids:
            name = asteroid.get("name", "Unknown")
            # 최대 지름 (미터)
            diameter = asteroid["estimated_diameter"]["meters"]["estimated_diameter_max"]
            # 위험 소행성 여부
            is_hazardous = asteroid.get("is_potentially_hazardous_asteroid", False)
            
            # 접근 정보 추출
            close_approach = asteroid["close_approach_data"][0]
            velocity = float(close_approach["relative_velocity"]["kilometers_per_second"])
            miss_distance = float(close_approach["miss_distance"]["kilometers"])
            
            neo_list.append({
                "접근 날짜": date,
                "소행성 이름": name,
                "최대 지름(m)": round(diameter, 2),
                "상대 속도(km/s)": round(velocity, 2),
                "지구 최단거리(km)": round(miss_distance, 2),
                "충돌 위험도": "위험 🚨" if is_hazardous else "안전 🟢"
            })
            
    return pd.DataFrame(neo_list)

# --- UI 레이아웃 시작 ---
st.title("🛰️ NASA 근지구 소행성(NEO) 실시간 모니터링")
st.markdown("""
이 대시보드는 NASA의 오픈 API를 활용하여 지구 주변을 스쳐 지나가는 소행성들의 크기, 속도, 지구와의 거리를 분석합니다. 
**지구과학 I/II의 '태양계 탐사' 및 '우주 환경' 단원**과 연계된 프로젝트입니다.
""")

# 날짜 선택 (오늘부터 최대 7일)
today = datetime.today()
start_date = st.date_input("시작 날짜", today)
end_date = start_date + timedelta(days=2) # 기본 3일치 검색

if (end_date - start_date).days > 7:
    st.warning("NASA API 제한으로 최대 7일까지만 검색 가능합니다. 날짜를 조정해주세요.")
else:
    with st.spinner("NASA 데이터를 분석하는 중입니다..."):
        raw_data = get_neo_data(start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))
        
        if raw_data:
            df = process_data(raw_data)
            
            # 1. 요약 메트릭
            st.subheader("📊 소행성 접근 요약")
            col1, col2, col3 = st.columns(3)
            col1.metric("총 접근 소행성 수", f"{len(df)} 개")
            col2.metric("위험 소행성 수", f"{len(df[df['충돌 위험도'] == '위험 🚨'])} 개")
            col3.metric("가장 큰 소행성 지름", f"{df['최대 지름(m)'].max()} m")
            
            st.divider()
            
            # 2. 데이터 시각화 (Plotly)
            st.subheader("📈 소행성 거리 및 속도 분석도")
            fig = px.scatter(
                df, 
                x="지구 최단거리(km)", 
                y="상대 속도(km/s)", 
                size="최대 지름(m)", 
                color="충돌 위험도",
                hover_name="소행성 이름",
                color_discrete_map={"위험 🚨": "red", "안전 🟢": "green"},
                log_x=True, # 거리가 넓으므로 로그 스케일 적용
                title="지구와의 거리 vs 상대 속도 (원의 크기 = 소행성 지름)"
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # 3. 원본 데이터 표
            st.subheader("📋 상세 관측 데이터")
            st.dataframe(df.sort_values(by="지구 최단거리(km)"), use_container_width=True)
