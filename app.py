import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# 페이지 기본 설정
st.set_page_config(page_title="NASA 근지구 소행성 대시보드", page_icon="☄️", layout="wide")

# NASA API 키를 Streamlit Secrets(비밀 금고)에서 안전하게 로드
try:
    API_KEY = st.secrets["NASA_KEY"]
except KeyError:
    st.error("⚠️ Streamlit Secrets에 'NASA_KEY'가 설정되지 않았습니다. Settings -> Secrets 메뉴에서 NASA_KEY를 등록해 주세요.")
    st.stop()

NEO_URL = "https://api.nasa.gov/neo/rest/v1/feed"

@st.cache_data(ttl=1800)
def get_neo_data(start_date, end_date):
    params = {
        "start_date": start_date,
        "end_date": end_date,
        "api_key": API_KEY
    }
    try:
        response = requests.get(NEO_URL, params=params, timeout=10)
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 429:
            st.error("⚠️ API 호출 한도 초과(429): Secrets에 등록된 API 키의 일일 한도를 확인해 주세요.")
            return None
        else:
            st.error(f"⚠️ NASA API 오류 발생 (상태 코드: {response.status_code})")
            return None
    except Exception as e:
        st.error(f"⚠️ API 통신 중 연결 오류 발생: {e}")
        return None

def process_data(data):
    if not data or "near_earth_objects" not in data:
        return pd.DataFrame()
        
    neo_list = []
    neos = data.get("near_earth_objects", {})
    
    for date, asteroids in neos.items():
        for asteroid in asteroids:
            name = asteroid.get("name", "Unknown")
            diameter = asteroid["estimated_diameter"]["meters"]["estimated_diameter_max"]
            is_hazardous = asteroid.get("is_potentially_hazardous_asteroid", False)
            
            close_approach_list = asteroid.get("close_approach_data", [])
            if not close_approach_list:
                continue
            close_approach = close_approach_list[0]
            
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

# --- UI 레이아웃 ---
st.title("🛰️ NASA 근지구 소행성(NEO) 실시간 모니터링")
st.markdown("NASA의 Open API를 활용하여 지구 주변을 지나가는 소행성들의 궤도 데이터를 분석합니다.")

today = datetime.today()
start_date = st.date_input("시작 날짜", today)
end_date = start_date + timedelta(days=2)

if (end_date - start_date).days > 7:
    st.warning("NASA API 제한으로 최대 7일까지만 검색 가능합니다.")
else:
    with st.spinner("NASA 데이터를 수집 중입니다..."):
        raw_data = get_neo_data(start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))
        
        if raw_data:
            df = process_data(raw_data)
            
            if not df.empty:
                st.subheader("📊 소행성 접근 요약")
                col1, col2, col3 = st.columns(3)
                col1.metric("총 접근 소행성 수", f"{len(df)} 개")
                col2.metric("위험 소행성 수", f"{len(df[df['충돌 위험도'] == '위험 🚨'])} 개")
                col3.metric("가장 큰 소행성 지름", f"{df['최대 지름(m)'].max()} m")
                
                st.divider()
                
                st.subheader("📈 소행성 거리 및 속도 분석도")
                fig = px.scatter(
                    df, 
                    x="지구 최단거리(km)", 
                    y="상대 속도(km/s)", 
                    size="최대 지름(m)", 
                    color="충돌 위험도",
                    hover_name="소행성 이름",
                    color_discrete_map={"위험 🚨": "red", "안전 🟢": "green"},
                    log_x=True,
                    title="지구와의 거리 vs 상대 속도 (원의 크기 = 소행성 지름)"
                )
                st.plotly_chart(fig, use_container_width=True)
                
                st.subheader("📋 상세 관측 데이터")
                st.dataframe(df.sort_values(by="지구 최단거리(km)"), use_container_width=True)
            else:
                st.info("선택한 기간 동안 관측된 소행성 데이터가 없습니다.")
