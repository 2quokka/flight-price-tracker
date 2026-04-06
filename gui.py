#!/usr/bin/env python3
"""✈️ 항공권 최저가 검색기 — Streamlit GUI v2"""
import re
from datetime import date, datetime, timedelta

import pandas as pd
import streamlit as st

from flight_tracker.models import FlightResult, RoundTripCombo
from flight_tracker.providers import PROVIDERS
from flight_tracker.providers.base import FlightProvider
from flight_tracker import aggregator

# ── 공항 데이터 (한국어 검색 + 자동완성) ──
AIRPORTS = {
    "GMP": "서울 (김포공항)",
    "ICN": "서울 (인천공항)",
    "CJU": "제주 (제주공항)",
    "PUS": "부산 (김해공항)",
    "TAE": "대구 (대구공항)",
    "CJJ": "청주 (청주공항)",
    "KWJ": "광주 (광주공항)",
    "RSU": "여수 (여수공항)",
    "USN": "울산 (울산공항)",
    "MWX": "무안 (무안공항)",
    "HIN": "사천 (사천공항)",
    "WJU": "원주 (원주공항)",
    "KUV": "군산 (군산공항)",
    "NRT": "도쿄 (나리타)",
    "HND": "도쿄 (하네다)",
    "KIX": "오사카 (간사이)",
    "FUK": "후쿠오카",
    "OKA": "오키나와 (나하)",
    "CTS": "삿포로 (신치토세)",
    "NGO": "나고야 (추부)",
    "PEK": "베이징 (수도)",
    "PKX": "베이징 (다싱)",
    "PVG": "상하이 (푸동)",
    "SHA": "상하이 (홍차오)",
    "HKG": "홍콩",
    "TPE": "타이베이 (타오위안)",
    "BKK": "방콕 (수완나품)",
    "DMK": "방콕 (돈므앙)",
    "HKT": "푸켓",
    "CNX": "치앙마이",
    "SGN": "호치민 (떤선녓)",
    "HAN": "하노이 (노이바이)",
    "DAD": "다낭",
    "PQC": "푸꾸옥",
    "CEB": "세부 (막탄)",
    "MNL": "마닐라 (니노이아키노)",
    "CRK": "클라크",
    "SIN": "싱가포르 (창이)",
    "KUL": "쿠알라룸푸르",
    "DPS": "발리 (응우라라이)",
    "REP": "시엠립",
    "PNH": "프놈펜",
    "RGN": "양곤",
    "VTE": "비엔티안",
    "DEL": "뉴델리 (인디라간디)",
    "SYD": "시드니",
    "LAX": "로스앤젤레스",
    "JFK": "뉴욕 (JFK)",
    "SFO": "샌프란시스코",
    "CDG": "파리 (샤를드골)",
    "LHR": "런던 (히드로)",
    "FCO": "로마 (피우미치노)",
    "BCN": "바르셀로나",
    "GUM": "괌",
    "SPN": "사이판",
}

AIRPORT_OPTIONS = {f"{name} ({code})": code for code, name in AIRPORTS.items()}
AIRPORT_LABELS = list(AIRPORT_OPTIONS.keys())


def find_airports(query: str) -> list[str]:
    """검색어로 공항 필터링 (한글/영문/코드 모두 지원)"""
    q = query.lower()
    return [label for label in AIRPORT_LABELS
            if q in label.lower() or q in AIRPORT_OPTIONS[label].lower()]


def get_code(label: str) -> str:
    return AIRPORT_OPTIONS.get(label, "")


def get_providers(selected: list[str]) -> list[FlightProvider]:
    return [PROVIDERS[n]() for n in selected]


def parse_hour(time_str: str) -> float | None:
    m = re.match(r"(\d+):(\d+)\s*(AM|PM)", time_str)
    if not m:
        return None
    h, mi, ap = int(m.group(1)), int(m.group(2)), m.group(3)
    if ap == "PM" and h != 12: h += 12
    if ap == "AM" and h == 12: h = 0
    return h + mi / 60.0


def format_price(val):
    return f"₩{int(val):,}"


def flight_url(from_code: str, to_code: str, date_str: str, oneway: bool = False) -> str:
    """출처별 항공권 검색 URL 생성"""
    base = f"https://www.google.com/travel/flights?q={from_code}+to+{to_code}+on+{date_str}&hl=ko&curr=KRW"
    return base + "&tt=oneway" if oneway else base


# ── 페이지 설정 ──
st.set_page_config(page_title="✈️ 항공권 최저가 검색기", page_icon="✈️", layout="wide")

# ── 커스텀 CSS ──
st.markdown("""
<style>
    /* 헤더 영역 */
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem 2rem 1.5rem;
        border-radius: 16px;
        margin-bottom: 1.5rem;
        color: white;
        text-align: center;
    }
    .main-header h1 { color: white !important; font-size: 2rem; margin: 0; }
    .main-header p { color: rgba(255,255,255,0.85); margin: 0.3rem 0 0; font-size: 1rem; }

    /* 검색 카드 */
    .search-card {
        background: white;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.08);
    }

    /* 결과 하이라이트 */
    .best-price {
        background: linear-gradient(135deg, #f6d365 0%, #fda085 100%);
        padding: 1rem 1.5rem;
        border-radius: 12px;
        text-align: center;
        margin: 1rem 0;
    }
    .best-price h2 { margin: 0; font-size: 1.5rem; }
    .best-price p { margin: 0.2rem 0 0; opacity: 0.8; }

    /* 탭 스타일 */
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px 8px 0 0;
        padding: 8px 20px;
    }

    /* 데이터프레임 */
    .stDataFrame { border-radius: 8px; overflow: hidden; }

    /* selectbox 높이 */
    div[data-baseweb="select"] { min-height: 45px; }

    /* 버튼 */
    .stButton > button[kind="primary"] {
        width: 100%;
        padding: 0.6rem 1rem;
        font-size: 1.1rem;
        border-radius: 10px;
    }
</style>
""", unsafe_allow_html=True)

# ── 헤더 ──
st.markdown("""
<div class="main-header">
    <h1>✈️ 항공권 최저가 검색기</h1>
    <p>Google Flights · Trip.com · Fli — 멀티 플랫폼 실시간 비교</p>
</div>
""", unsafe_allow_html=True)

# ── 탭 ──
tab_oneway, tab_roundtrip, tab_daytrip, tab_history = st.tabs([
    "✈️ 편도", "🔄 왕복", "☀️ 당일치기", "🕘 최근 검색결과"
])

# ── 세션 상태: 최근 검색결과 ──
if "search_history" not in st.session_state:
    st.session_state.search_history = []

# ── 사이드바: 프로바이더 설정 ──
with st.sidebar:
    st.markdown("### ⚙️ 검색 설정")
    provider_names = list(PROVIDERS.keys())
    selected_providers = st.multiselect(
        "검색 엔진", provider_names, default=provider_names,
        format_func=lambda x: {"google": "🔍 Google Flights", "fli": "🛫 Fli", "tripcom": "🌐 Trip.com"}.get(x, x)
    )
    st.divider()
    st.markdown("### 💡 사용 팁")
    st.markdown("""
    - 공항 입력 시 **한글**로 검색 가능
    - 여러 프로바이더를 선택하면 최저가 비교
    - 당일치기는 시간 필터로 편리하게
    """)

# ══════════════════════════════════════
# 편도 탭
# ══════════════════════════════════════
with tab_oneway:
    col_from, col_swap, col_to = st.columns([5, 1, 5])
    with col_from:
        from_label = st.selectbox("출발지", AIRPORT_LABELS,
                                   index=AIRPORT_LABELS.index("서울 (김포공항) (GMP)"),
                                   key="ow_from", placeholder="도시 또는 공항 검색...")
    with col_swap:
        st.markdown("<div style='text-align:center; padding-top:1.7rem; font-size:1.5rem;'>⇄</div>", unsafe_allow_html=True)
    with col_to:
        to_label = st.selectbox("도착지", AIRPORT_LABELS,
                                 index=AIRPORT_LABELS.index("제주 (제주공항) (CJU)"),
                                 key="ow_to", placeholder="도시 또는 공항 검색...")

    col_d1, col_d2, col_top = st.columns([3, 3, 2])
    start = col_d1.date_input("출발일", date.today() + timedelta(days=7), key="ow_start")
    end = col_d2.date_input("종료일", date.today() + timedelta(days=14), key="ow_end")
    top_n = col_top.number_input("결과 수", 5, 50, 10, key="ow_top")

    if st.button("🔍 최저가 검색", type="primary", key="ow_btn", use_container_width=True):
        from_code, to_code = get_code(from_label), get_code(to_label)
        if not selected_providers:
            st.error("검색 엔진을 1개 이상 선택하세요.")
        elif from_code == to_code:
            st.error("출발지와 도착지가 같습니다.")
        else:
            provs = get_providers(selected_providers)
            with st.spinner(f"🔍 {from_label} → {to_label} 검색 중..."):
                results = aggregator.search_date_range(provs, from_code, to_code, start, end)
            if results:
                best = results[0]
                st.markdown(f"""
                <div class="best-price">
                    <h2>🏆 {format_price(best.price)}</h2>
                    <p>{best.date} · {best.airline} · {best.departure}</p>
                </div>
                """, unsafe_allow_html=True)

                df = pd.DataFrame([
                    {"날짜": f.date, "항공사": f.airline, "출발": f.departure, "도착": f.arrival,
                     "소요시간": f.duration, "가격": f.price,
                     "출처": flight_url(from_code, to_code, f.date, oneway=True)}
                    for f in results[:top_n]
                ])
                st.dataframe(
                    df.style.format({"가격": "₩{:,.0f}"}).background_gradient(subset=["가격"], cmap="YlOrRd_r"),
                    column_config={"출처": st.column_config.LinkColumn("출처", display_text="🔗 검색")},
                    use_container_width=True, hide_index=True
                )

                st.subheader("📊 날짜별 가격 추이")
                chart_df = df[["날짜", "가격"]].set_index("날짜")
                st.bar_chart(chart_df)

                st.session_state.search_history.insert(0, {
                    "type": "편도", "route": f"{from_label} → {to_label}",
                    "best": format_price(best.price), "count": len(results), "df": df,
                })
            else:
                st.warning("검색 결과가 없습니다. 날짜나 공항을 확인해주세요.")

# ══════════════════════════════════════
# 왕복 탭
# ══════════════════════════════════════
with tab_roundtrip:
    col_from, col_swap, col_to = st.columns([5, 1, 5])
    with col_from:
        rt_from = st.selectbox("출발지", AIRPORT_LABELS,
                                index=AIRPORT_LABELS.index("서울 (김포공항) (GMP)"),
                                key="rt_from", placeholder="도시 또는 공항 검색...")
    with col_swap:
        st.markdown("<div style='text-align:center; padding-top:1.7rem; font-size:1.5rem;'>⇄</div>", unsafe_allow_html=True)
    with col_to:
        rt_to = st.selectbox("도착지", AIRPORT_LABELS,
                              index=AIRPORT_LABELS.index("제주 (제주공항) (CJU)"),
                              key="rt_to", placeholder="도시 또는 공항 검색...")

    st.markdown("##### 📅 여행 일정")
    col1, col2, col3, col4 = st.columns(4)
    dep_start = col1.date_input("가는날 (시작)", date.today() + timedelta(days=7), key="rt_ds")
    dep_end = col2.date_input("가는날 (종료)", date.today() + timedelta(days=10), key="rt_de")
    ret_start = col3.date_input("오는날 (시작)", date.today() + timedelta(days=10), key="rt_rs")
    ret_end = col4.date_input("오는날 (종료)", date.today() + timedelta(days=14), key="rt_re")

    top_n_rt = st.number_input("결과 수", 5, 50, 10, key="rt_top")

    if st.button("🔍 왕복 최저가 검색", type="primary", key="rt_btn", use_container_width=True):
        from_code, to_code = get_code(rt_from), get_code(rt_to)
        if not selected_providers:
            st.error("검색 엔진을 1개 이상 선택하세요.")
        else:
            provs = get_providers(selected_providers)
            with st.spinner("가는편 검색 중..."):
                outbound = aggregator.search_date_range(provs, from_code, to_code, dep_start, dep_end)
            with st.spinner("오는편 검색 중..."):
                inbound = aggregator.search_date_range(provs, to_code, from_code, ret_start, ret_end)

            combos = sorted(
                [RoundTripCombo(o, i) for o in outbound for i in inbound if i.date > o.date],
                key=lambda c: c.total_price
            )

            if combos:
                best = combos[0]
                st.markdown(f"""
                <div class="best-price">
                    <h2>🏆 왕복 {format_price(best.total_price)}</h2>
                    <p>가는편 {best.outbound.date} {best.outbound.airline} · 오는편 {best.inbound.date} {best.inbound.airline}</p>
                </div>
                """, unsafe_allow_html=True)

                df = pd.DataFrame([
                    {"가는날": c.outbound.date, "가는편": c.outbound.airline,
                     "가는편 가격": c.outbound.price, "오는날": c.inbound.date,
                     "오는편": c.inbound.airline, "오는편 가격": c.inbound.price,
                     "합계": c.total_price,
                     "가는편 검색": flight_url(from_code, to_code, c.outbound.date),
                     "오는편 검색": flight_url(to_code, from_code, c.inbound.date)}
                    for c in combos[:top_n_rt]
                ])
                st.dataframe(
                    df.style.format({"가는편 가격": "₩{:,.0f}", "오는편 가격": "₩{:,.0f}", "합계": "₩{:,.0f}"})
                    .background_gradient(subset=["합계"], cmap="YlOrRd_r"),
                    column_config={
                        "가는편 검색": st.column_config.LinkColumn("가는편 검색", display_text="🔗"),
                        "오는편 검색": st.column_config.LinkColumn("오는편 검색", display_text="🔗"),
                    },
                    use_container_width=True, hide_index=True
                )

                st.session_state.search_history.insert(0, {
                    "type": "왕복", "route": f"{rt_from} ↔ {rt_to}",
                    "best": format_price(best.total_price), "count": len(combos), "df": df,
                })
            else:
                st.warning("왕복 조합 결과가 없습니다.")

# ══════════════════════════════════════
# 당일치기 탭
# ══════════════════════════════════════
with tab_daytrip:
    col_from, col_swap, col_to = st.columns([5, 1, 5])
    with col_from:
        dt_from = st.selectbox("출발지", AIRPORT_LABELS,
                                index=AIRPORT_LABELS.index("서울 (김포공항) (GMP)"),
                                key="dt_from", placeholder="도시 또는 공항 검색...")
    with col_swap:
        st.markdown("<div style='text-align:center; padding-top:1.7rem; font-size:1.5rem;'>⇄</div>", unsafe_allow_html=True)
    with col_to:
        dt_to = st.selectbox("도착지", AIRPORT_LABELS,
                              index=AIRPORT_LABELS.index("제주 (제주공항) (CJU)"),
                              key="dt_to", placeholder="도시 또는 공항 검색...")

    col_d1, col_d2 = st.columns(2)
    dt_start = col_d1.date_input("시작일", date.today() + timedelta(days=7), key="dt_start")
    dt_end = col_d2.date_input("종료일", date.today() + timedelta(days=14), key="dt_end")

    st.markdown("##### ⏰ 시간 필터")
    c1, c2, c3, c4 = st.columns(4)
    dep_after = c1.time_input("가는편 출발 이후", datetime.strptime("08:00", "%H:%M").time(), key="dt_da")
    dep_before = c2.time_input("가는편 출발 이전", datetime.strptime("10:00", "%H:%M").time(), key="dt_db")
    ret_after = c3.time_input("오는편 출발 이후", datetime.strptime("17:00", "%H:%M").time(), key="dt_ra")
    arrive_by = c4.time_input("오는편 도착 이전", datetime.strptime("21:30", "%H:%M").time(), key="dt_ab")

    top_n_dt = st.number_input("결과 수", 5, 50, 10, key="dt_topn")

    if st.button("🔍 당일치기 검색", type="primary", key="dt_btn", use_container_width=True):
        from_code, to_code = get_code(dt_from), get_code(dt_to)
        if not selected_providers:
            st.error("검색 엔진을 1개 이상 선택하세요.")
        else:
            provs = get_providers(selected_providers)
            da = dep_after.hour + dep_after.minute / 60.0
            db = dep_before.hour + dep_before.minute / 60.0
            ra = ret_after.hour + ret_after.minute / 60.0
            ab = arrive_by.hour + arrive_by.minute / 60.0

            dates = []
            d = dt_start
            while d <= dt_end:
                dates.append(d)
                d += timedelta(days=1)

            combos = []
            progress = st.progress(0, text="검색 준비 중...")
            for idx, d in enumerate(dates):
                ds = d.strftime("%Y-%m-%d")
                progress.progress((idx + 1) / len(dates), text=f"📅 {ds} 검색 중... ({idx+1}/{len(dates)})")
                out_flights = aggregator.search_one_day(provs, from_code, to_code, ds)
                best_out = next((f for f in out_flights if (h := parse_hour(f.departure)) is not None and da <= h <= db), None)
                if best_out:
                    ret_flights = aggregator.search_one_day(provs, to_code, from_code, ds)
                    best_ret = next((f for f in ret_flights if (dh := parse_hour(f.departure)) is not None and (ah := parse_hour(f.arrival)) is not None and dh >= ra and ah <= ab), None)
                    if best_ret:
                        combos.append(RoundTripCombo(outbound=best_out, inbound=best_ret))
            progress.empty()

            combos.sort(key=lambda c: c.total_price)
            if combos:
                best = combos[0]
                st.markdown(f"""
                <div class="best-price">
                    <h2>🏆 당일치기 {format_price(best.total_price)}</h2>
                    <p>{best.outbound.date} · 가는편 {best.outbound.airline} {best.outbound.departure} · 오는편 {best.inbound.airline} {best.inbound.departure}</p>
                </div>
                """, unsafe_allow_html=True)

                df = pd.DataFrame([
                    {"순위": i+1, "날짜": c.outbound.date, "가는편": c.outbound.airline,
                     "출발→도착": f"{c.outbound.departure} → {c.outbound.arrival}",
                     "가는편 가격": c.outbound.price, "오는편": c.inbound.airline,
                     "출발→도착 ": f"{c.inbound.departure} → {c.inbound.arrival}",
                     "오는편 가격": c.inbound.price, "합계": c.total_price,
                     "검색": flight_url(from_code, to_code, c.outbound.date)}
                    for i, c in enumerate(combos[:top_n_dt])
                ])
                st.dataframe(
                    df.style.format({"가는편 가격": "₩{:,.0f}", "오는편 가격": "₩{:,.0f}", "합계": "₩{:,.0f}"})
                    .background_gradient(subset=["합계"], cmap="YlOrRd_r"),
                    column_config={"검색": st.column_config.LinkColumn("검색", display_text="🔗")},
                    use_container_width=True, hide_index=True
                )

                st.session_state.search_history.insert(0, {
                    "type": "당일치기", "route": f"{dt_from} ↔ {dt_to}",
                    "best": format_price(best.total_price), "count": len(combos), "df": df,
                })
            else:
                st.warning("조건에 맞는 당일치기 항공편이 없습니다.")

# ══════════════════════════════════════
# 저장된 결과 탭
# ══════════════════════════════════════
with tab_history:
    history = st.session_state.search_history
    if history:
        if st.button("🗑️ 기록 초기화", key="clear_history"):
            st.session_state.search_history = []
            st.rerun()

        for i, h in enumerate(history[:10]):
            with st.expander(f"{'🔄' if h['type'] == '왕복' else '☀️' if h['type'] == '당일치기' else '✈️'} [{h['type']}] {h['route']} — 최저가 {h['best']} ({h['count']}건)", expanded=(i == 0)):
                st.dataframe(h["df"], use_container_width=True, hide_index=True)
    else:
        st.info("검색 결과가 없습니다. 편도/왕복/당일치기 탭에서 검색해보세요.")

# ── 푸터 ──
st.divider()
st.markdown(
    "<div style='text-align:center; color:#94a3b8; font-size:0.85rem;'>"
    "✈️ flight-price-tracker v2 · Google Flights · Trip.com · Fli"
    "</div>",
    unsafe_allow_html=True
)
