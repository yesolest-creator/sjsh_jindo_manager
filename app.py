import streamlit as st
import pandas as pd
import json
from datetime import date, timedelta, datetime
import calendar
import requests

st.set_page_config(
    page_title="수업 진도 관리",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── 스타일 ──────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700&display=swap');

html, body, [class*="css"] { font-family: 'Noto Sans KR', sans-serif; }

.main-title {
    font-size: 1.6rem; font-weight: 700; color: #1a3a5c;
    border-left: 5px solid #2e7bcf; padding-left: 12px;
    margin-bottom: 0.2rem;
}
.section-title {
    font-size: 1rem; font-weight: 700; color: #2e7bcf;
    border-bottom: 2px solid #e8f0fb; padding-bottom: 4px;
    margin: 1rem 0 0.5rem 0;
}
.badge-original {
    background: #dbeafe; color: #1d4ed8;
    padding: 2px 8px; border-radius: 10px; font-size: 0.75rem; font-weight: 600;
}
.badge-cross {
    background: #fce7f3; color: #be185d;
    padding: 2px 8px; border-radius: 10px; font-size: 0.75rem; font-weight: 600;
}
.badge-fixed {
    background: #d1fae5; color: #065f46;
    padding: 2px 8px; border-radius: 10px; font-size: 0.75rem; font-weight: 600;
}

/* 진도표 테이블 */
.progress-table { width: 100%; border-collapse: collapse; font-size: 0.82rem; }
.progress-table th {
    background: #1a3a5c; color: white;
    padding: 6px 8px; text-align: center;
    position: sticky; top: 0; z-index: 2;
}
.progress-table td {
    padding: 5px 8px; text-align: center;
    border: 1px solid #e2e8f0;
}
.progress-table tr:nth-child(even) td { background: #f8fafc; }
.progress-table tr:hover td { background: #eff6ff; }
.today-row td { background: #fef9c3 !important; font-weight: 700; }
.today-row td:first-child { border-left: 3px solid #f59e0b; }
.holiday-row td { background: #fff1f2 !important; color: #9f1239; }
.absent-cell { background: #fde8e8 !important; color: #c53030; font-size: 0.7rem; }
.lesson-cell { background: #ebf8ff !important; color: #2b6cb0; font-weight: 600; }
.week-header td {
    background: #334155 !important; color: #e2e8f0 !important;
    font-weight: 600; font-size: 0.78rem;
}

/* 주차 요약 테이블 */
.summary-table { width: 100%; border-collapse: collapse; font-size: 0.8rem; }
.summary-table th {
    background: #1a3a5c; color: white;
    padding: 5px 6px; text-align: center;
}
.summary-table td {
    padding: 4px 6px; text-align: center;
    border: 1px solid #e2e8f0;
}
.summary-table tr:hover td { background: #eff6ff; }

@media print {
    .stSidebar, .stButton, [data-testid="stToolbar"] { display: none !important; }
    .main { margin: 0; padding: 0; }
}
</style>
""", unsafe_allow_html=True)

# ── 세션 상태 초기화 ────────────────────────────────────
def init_state():
    defaults = {
        "subjects": ["고급지구과학"],
        "current_subject": "고급지구과학",
        "current_semester": "1학기",
        "year": 2026,
        # 반 구성: {과목: [반 이름 목록]}
        "classes": {"고급지구과학": ["1반","2반","3반","4반","5반","6반","7반","8반"]},
        # 시간표: {과목: {반: {요일: [교시목록]}}}
        "timetable": {"고급지구과학": {}},
        # 교차시간표 설정: {과목: {"fixed":[], "original":[], "cross":[]}}
        "schedule_type": {"고급지구과학": {"fixed":[], "original":[], "cross":[]}},
        # 날짜별 원/교 설정: {과목: {날짜문자열: "original"/"cross"/"fixed"/"none"}}
        "date_schedule": {"고급지구과학": {}},
        # 단원 목록: {과목: [{차시:int, 단원:str}]}
        "units": {"고급지구과학": []},
        # 수업 기록: {과목: {날짜문자열: {반: {차시:int, 비고:str}}}}
        "records": {"고급지구과학": {}},
        # 결강 사유 목록
        "absence_reasons": ["출장(교사 부재)","학교 행사(조회 등)","체육대회","시험 기간","수행평가","보강"],
        # 학기 날짜 범위
        "semester_start": {"1학기": "2026-03-02", "2학기": "2026-09-01"},
        "semester_end":   {"1학기": "2026-07-17", "2학기": "2026-12-31"},
        # 공휴일 캐시
        "holidays": {},
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()

# ── 공휴일 불러오기 ─────────────────────────────────────
@st.cache_data(ttl=86400)
def fetch_holidays(year: int) -> dict:
    """공공데이터포털 대신 고정 공휴일 + 간단 처리 (API 키 없이도 동작)"""
    fixed = {
        f"{year}-01-01": "신정",
        f"{year}-03-01": "삼일절",
        f"{year}-05-05": "어린이날",
        f"{year}-06-06": "현충일",
        f"{year}-08-15": "광복절",
        f"{year}-10-03": "개천절",
        f"{year}-10-09": "한글날",
        f"{year}-12-25": "성탄절",
    }
    # 설날/추석은 연도별로 달라지므로 2026년 기준 하드코딩
    if year == 2026:
        fixed.update({
            "2026-02-17": "설날 연휴",
            "2026-02-18": "설날",
            "2026-02-19": "설날 연휴",
            "2026-05-05": "어린이날",
            "2026-05-25": "부처님오신날",
            "2026-10-05": "추석 연휴",
            "2026-10-06": "추석",
            "2026-10-07": "추석 연휴",
        })
    return fixed

holidays_dict = fetch_holidays(st.session_state.year)

# ── 유틸 함수 ───────────────────────────────────────────
WEEKDAYS = ["월","화","수","목","금","토","일"]

def get_semester_dates(year, semester):
    s = st.session_state.semester_start[semester]
    e = st.session_state.semester_end[semester]
    start = date.fromisoformat(s)
    end   = date.fromisoformat(e)
    dates = []
    cur = start
    while cur <= end:
        dates.append(cur)
        cur += timedelta(days=1)
    return dates

def is_holiday(d: date) -> str:
    return holidays_dict.get(d.isoformat(), "")

def is_weekend(d: date) -> bool:
    return d.weekday() >= 5

def get_week_number(d: date, start: date) -> int:
    return (d - start).days // 7 + 1

def get_schedule_for_date(subj, d: date):
    """해당 날짜의 시간표 유형 반환: 'fixed'/'original'/'cross'/'none'"""
    ds = st.session_state.date_schedule.get(subj, {})
    return ds.get(d.isoformat(), "none")

def get_classes_for_date(subj, d: date):
    """해당 날짜에 수업이 있는 반 목록 반환"""
    if is_weekend(d) or is_holiday(d):
        return []
    tt = st.session_state.timetable.get(subj, {})
    stype = st.session_state.schedule_type.get(subj, {})
    day_str = WEEKDAYS[d.weekday()]
    date_type = get_schedule_for_date(subj, d)

    result = []
    classes = st.session_state.classes.get(subj, [])
    for cls in classes:
        cls_tt = tt.get(cls, {})
        # 고정 반
        if cls in stype.get("fixed", []) and day_str in cls_tt:
            result.append(cls)
        # 원시간표 반
        elif cls in stype.get("original", []) and date_type == "original" and day_str in cls_tt:
            result.append(cls)
        # 교차시간표 반
        elif cls in stype.get("cross", []) and date_type == "cross" and day_str in cls_tt:
            result.append(cls)
    return result

def ensure_subject_keys(subj):
    for key, default in [
        ("classes", []), ("timetable", {}), ("schedule_type", {"fixed":[],"original":[],"cross":[]}),
        ("date_schedule", {}), ("units", []), ("records", {})
    ]:
        if subj not in st.session_state[key]:
            st.session_state[key][subj] = default if key != "schedule_type" else {"fixed":[],"original":[],"cross":[]}

# ── 사이드바 ────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="main-title">📚 수업 진도 관리</div>', unsafe_allow_html=True)
    st.caption("교차시간표 지원 진도 관리 시스템")
    st.divider()

    # 과목 관리
    st.markdown('<div class="section-title">📖 과목 관리</div>', unsafe_allow_html=True)
    subj_col1, subj_col2 = st.columns([3,1])
    with subj_col1:
        new_subj = st.text_input("과목 추가", placeholder="예: 지구과학I", label_visibility="collapsed")
    with subj_col2:
        if st.button("추가", use_container_width=True) and new_subj.strip():
            if new_subj.strip() not in st.session_state.subjects:
                st.session_state.subjects.append(new_subj.strip())
                ensure_subject_keys(new_subj.strip())
                st.rerun()

    selected_subj = st.selectbox("과목 선택", st.session_state.subjects,
        index=st.session_state.subjects.index(st.session_state.current_subject)
            if st.session_state.current_subject in st.session_state.subjects else 0)
    st.session_state.current_subject = selected_subj
    ensure_subject_keys(selected_subj)

    if len(st.session_state.subjects) > 1:
        if st.button(f"'{selected_subj}' 삭제", type="secondary"):
            st.session_state.subjects.remove(selected_subj)
            st.session_state.current_subject = st.session_state.subjects[0]
            st.rerun()

    # 학년도 / 학기
    st.markdown('<div class="section-title">🗓️ 학년도 / 학기</div>', unsafe_allow_html=True)
    year_col, sem_col = st.columns(2)
    with year_col:
        st.session_state.year = st.selectbox("학년도", [2025,2026,2027],
            index=[2025,2026,2027].index(st.session_state.year))
    with sem_col:
        st.session_state.current_semester = st.selectbox("학기", ["1학기","2학기"],
            index=["1학기","2학기"].index(st.session_state.current_semester))

    sem_s = st.text_input("학기 시작일", value=st.session_state.semester_start[st.session_state.current_semester])
    sem_e = st.text_input("학기 종료일", value=st.session_state.semester_end[st.session_state.current_semester])
    st.session_state.semester_start[st.session_state.current_semester] = sem_s
    st.session_state.semester_end[st.session_state.current_semester] = sem_e

    # 반 구성
    st.markdown('<div class="section-title">🏫 반 구성</div>', unsafe_allow_html=True)
    classes_str = st.text_area("반 목록 (줄바꿈으로 구분)",
        value="\n".join(st.session_state.classes.get(selected_subj, [])),
        height=100, help="한 줄에 반 이름 하나씩 입력")
    if st.button("반 구성 저장"):
        cls_list = [c.strip() for c in classes_str.strip().split("\n") if c.strip()]
        st.session_state.classes[selected_subj] = cls_list
        st.success("반 구성이 저장되었습니다.")
        st.rerun()

    # 결강 사유 관리
    st.markdown('<div class="section-title">📝 결강 사유 관리</div>', unsafe_allow_html=True)
    reasons_str = st.text_area("결강 사유 (줄바꿈으로 구분)",
        value="\n".join(st.session_state.absence_reasons),
        height=100)
    if st.button("결강 사유 저장"):
        st.session_state.absence_reasons = [r.strip() for r in reasons_str.strip().split("\n") if r.strip()]
        st.success("저장되었습니다.")

# ── 메인 화면 ───────────────────────────────────────────
subj = st.session_state.current_subject
semester = st.session_state.current_semester

st.markdown(f'<div class="main-title">📚 {subj} — {st.session_state.year}학년도 {semester} 진도 관리</div>',
    unsafe_allow_html=True)

tab1, tab2, tab3, tab4 = st.tabs(["⚙️ 시간표 설정", "📅 원/교차 설정", "📖 단원 관리", "📊 진도표"])

# ══════════════════════════════════════════════
# TAB 1: 시간표 설정
# ══════════════════════════════════════════════
with tab1:
    st.markdown('<div class="section-title">반별 시간표 유형 설정</div>', unsafe_allow_html=True)
    st.info("각 반이 **고정(매주 동일)** / **원시간표** / **교차시간표** 중 어느 유형인지 먼저 설정하세요.")

    classes = st.session_state.classes.get(subj, [])
    stype = st.session_state.schedule_type.get(subj, {"fixed":[],"original":[],"cross":[]})

    if not classes:
        st.warning("사이드바에서 반 구성을 먼저 입력해주세요.")
    else:
        type_map = {}
        cols = st.columns(min(len(classes), 4))
        for i, cls in enumerate(classes):
            with cols[i % 4]:
                cur = "고정" if cls in stype["fixed"] else ("원시간표" if cls in stype["original"] else ("교차시간표" if cls in stype["cross"] else "미설정"))
                sel = st.selectbox(cls, ["미설정","고정","원시간표","교차시간표"], index=["미설정","고정","원시간표","교차시간표"].index(cur), key=f"stype_{cls}")
                type_map[cls] = sel

        if st.button("시간표 유형 저장", type="primary"):
            new_stype = {"fixed":[],"original":[],"cross":[]}
            for cls, t in type_map.items():
                if t == "고정": new_stype["fixed"].append(cls)
                elif t == "원시간표": new_stype["original"].append(cls)
                elif t == "교차시간표": new_stype["cross"].append(cls)
            st.session_state.schedule_type[subj] = new_stype
            st.success("저장되었습니다!")
            st.rerun()

    st.divider()
    st.markdown('<div class="section-title">반별 수업 요일 및 교시 설정</div>', unsafe_allow_html=True)
    st.info("각 반의 수업 요일과 교시를 설정하세요. (요일 체크 후 교시 번호 입력)")

    tt = st.session_state.timetable.get(subj, {})

    upload_file = st.file_uploader("시간표 CSV 파일 업로드 (선택)", type=["csv"],
        help="반,요일,교시 컬럼을 가진 CSV 파일을 업로드하면 자동으로 입력됩니다.")
    if upload_file:
        try:
            df_tt = pd.read_csv(upload_file)
            new_tt = {}
            for _, row in df_tt.iterrows():
                cls = str(row["반"]).strip()
                day = str(row["요일"]).strip()
                period = str(row["교시"]).strip()
                if cls not in new_tt: new_tt[cls] = {}
                if day not in new_tt[cls]: new_tt[cls][day] = []
                new_tt[cls][day].append(period)
            st.session_state.timetable[subj] = new_tt
            st.success("시간표가 업로드되었습니다!")
            st.rerun()
        except Exception as e:
            st.error(f"파일 형식을 확인해주세요: {e}")

    st.caption("아래에서 직접 입력할 수도 있습니다.")

    if classes:
        new_tt = {cls: tt.get(cls, {}) for cls in classes}
        days = ["월","화","수","목","금"]

        # 헤더
        header_cols = st.columns([2] + [1]*5)
        header_cols[0].markdown("**반**")
        for i, d in enumerate(days):
            header_cols[i+1].markdown(f"**{d}**")

        for cls in classes:
            row_cols = st.columns([2] + [1]*5)
            row_cols[0].markdown(f"**{cls}**")
            for i, day in enumerate(days):
                cur_periods = ",".join(tt.get(cls, {}).get(day, []))
                val = row_cols[i+1].text_input(f"{cls}_{day}", value=cur_periods,
                    placeholder="교시(,구분)", label_visibility="collapsed",
                    key=f"tt_{cls}_{day}")
                if val.strip():
                    if cls not in new_tt: new_tt[cls] = {}
                    new_tt[cls][day] = [v.strip() for v in val.split(",") if v.strip()]
                elif day in new_tt.get(cls, {}):
                    new_tt[cls].pop(day)

        if st.button("시간표 저장", type="primary"):
            st.session_state.timetable[subj] = new_tt
            st.success("시간표가 저장되었습니다!")

# ══════════════════════════════════════════════
# TAB 2: 원/교차 설정
# ══════════════════════════════════════════════
with tab2:
    st.markdown('<div class="section-title">날짜별 원시간표 / 교차시간표 설정</div>', unsafe_allow_html=True)
    st.info("날짜마다 원시간표인지 교차시간표인지 설정합니다. 고정 반에는 영향을 주지 않습니다.")

    try:
        all_dates = get_semester_dates(st.session_state.year, semester)
    except:
        st.error("학기 날짜 설정을 확인해주세요.")
        st.stop()

    ds = st.session_state.date_schedule.get(subj, {})

    # 빠른 범위 설정
    st.markdown("**📌 날짜 범위 일괄 설정**")
    rc1, rc2, rc3, rc4 = st.columns(4)
    range_start = rc1.date_input("시작일", value=all_dates[0], key="rs")
    range_end   = rc2.date_input("종료일", value=all_dates[min(6,len(all_dates)-1)], key="re")
    range_type  = rc3.selectbox("유형", ["원시간표","교차시간표","none"], key="rt")
    if rc4.button("일괄 적용", use_container_width=True):
        cur = range_start
        while cur <= range_end:
            if not is_weekend(cur):
                ds[cur.isoformat()] = range_type
            cur += timedelta(days=1)
        st.session_state.date_schedule[subj] = ds
        st.success(f"{range_start} ~ {range_end} → {range_type} 적용 완료!")
        st.rerun()

    st.divider()
    st.markdown("**📅 날짜별 개별 설정** (학사 일정 기준 주차별 표시)")

    # 주차별로 묶어서 표시
    school_dates = [d for d in all_dates if not is_weekend(d)]
    if school_dates:
        start_date = all_dates[0]
        week_groups = {}
        for d in school_dates:
            wk = get_week_number(d, start_date)
            week_groups.setdefault(wk, []).append(d)

        for wk, wdates in list(week_groups.items())[:8]:  # 처음 8주만 표시 (성능)
            with st.expander(f"{wk}주차 ({wdates[0].strftime('%m/%d')} ~ {wdates[-1].strftime('%m/%d')})", expanded=(wk<=2)):
                cols = st.columns(len(wdates))
                for i, d in enumerate(wdates):
                    hol = is_holiday(d)
                    cur_type = ds.get(d.isoformat(), "none")
                    with cols[i]:
                        label = f"{d.strftime('%m/%d')}({WEEKDAYS[d.weekday()]})"
                        if hol:
                            st.markdown(f"🔴 **{label}**")
                            st.caption(hol)
                        else:
                            st.markdown(f"**{label}**")
                            sel = st.selectbox("유형", ["none","원시간표","교차시간표"],
                                index=["none","원시간표","교차시간표"].index(cur_type) if cur_type in ["none","원시간표","교차시간표"] else 0,
                                key=f"ds_{d.isoformat()}", label_visibility="collapsed")
                            ds[d.isoformat()] = sel
                st.session_state.date_schedule[subj] = ds

        if len(week_groups) > 8:
            st.info(f"나머지 {len(week_groups)-8}주는 위 '일괄 설정'으로 적용하세요.")

# ══════════════════════════════════════════════
# TAB 3: 단원 관리
# ══════════════════════════════════════════════
with tab3:
    st.markdown('<div class="section-title">차시별 단원 입력</div>', unsafe_allow_html=True)
    units = st.session_state.units.get(subj, [])

    col_add1, col_add2, col_add3 = st.columns([1,4,1])
    new_lesson_num = col_add1.number_input("차시", min_value=1, max_value=200, value=len(units)+1, key="new_ln")
    new_lesson_name = col_add2.text_input("단원명", placeholder="예: Ⅰ-2-02. 지질도와 한반도", key="new_lname", label_visibility="collapsed")
    if col_add3.button("추가", use_container_width=True) and new_lesson_name.strip():
        # 중복 차시 확인
        existing_nums = [u["차시"] for u in units]
        if new_lesson_num in existing_nums:
            st.warning(f"{new_lesson_num}차시는 이미 있습니다. 수정하려면 아래 표에서 직접 수정하세요.")
        else:
            units.append({"차시": new_lesson_num, "단원": new_lesson_name.strip()})
            units.sort(key=lambda x: x["차시"])
            st.session_state.units[subj] = units
            st.rerun()

    if units:
        st.markdown(f"**총 {len(units)}차시 등록됨**")
        df_units = pd.DataFrame(units)

        edited = st.data_editor(df_units, use_container_width=True, num_rows="dynamic",
            column_config={
                "차시": st.column_config.NumberColumn("차시", min_value=1, max_value=200),
                "단원": st.column_config.TextColumn("단원명", width="large"),
            }, key="unit_editor")

        if st.button("단원 저장", type="primary"):
            new_units = edited.dropna(subset=["차시","단원"]).to_dict("records")
            new_units = [{"차시": int(u["차시"]), "단원": str(u["단원"])} for u in new_units]
            new_units.sort(key=lambda x: x["차시"])
            st.session_state.units[subj] = new_units
            st.success("단원 목록이 저장되었습니다!")
            st.rerun()
    else:
        st.info("위에서 차시와 단원명을 입력하여 추가하세요.")

# ══════════════════════════════════════════════
# TAB 4: 진도표
# ══════════════════════════════════════════════
with tab4:
    classes = st.session_state.classes.get(subj, [])
    units   = st.session_state.units.get(subj, [])
    records = st.session_state.records.get(subj, {})

    if not classes:
        st.warning("사이드바에서 반 구성을 먼저 설정해주세요.")
        st.stop()

    # ── 진도표 상단: 빠른 수업 기록 ─────────────────────
    st.markdown('<div class="section-title">✏️ 수업 기록 입력</div>', unsafe_allow_html=True)

    rec_col1, rec_col2, rec_col3, rec_col4, rec_col5 = st.columns([2,2,2,3,1])
    rec_date = rec_col1.date_input("날짜", value=date.today(), key="rec_date")
    rec_class = rec_col2.selectbox("반", classes, key="rec_class")
    rec_lesson = rec_col3.number_input("차시", min_value=1, max_value=200, value=1, key="rec_lesson")
    rec_note_options = ["정상수업"] + st.session_state.absence_reasons
    rec_note = rec_col4.selectbox("비고", rec_note_options, key="rec_note")
    if rec_col5.button("기록", type="primary", use_container_width=True):
        date_key = rec_date.isoformat()
        if date_key not in records:
            records[date_key] = {}
        records[date_key][rec_class] = {"차시": rec_lesson, "비고": rec_note}
        st.session_state.records[subj] = records
        st.success(f"{rec_date} {rec_class} {rec_lesson}차시 기록 완료!")
        st.rerun()

    st.divider()

    # ── 진도표 메인 ──────────────────────────────────────
    try:
        all_dates = get_semester_dates(st.session_state.year, semester)
    except:
        st.error("학기 날짜를 확인하세요.")
        st.stop()

    today = date.today()
    start_date = all_dates[0]

    # 단원 번호 → 단원명 매핑
    unit_map = {u["차시"]: u["단원"] for u in units}

    # 주차별 테이블 + 날짜별 진도표 나란히
    left_col, right_col = st.columns([1, 3])

    # ── 왼쪽: 주차별 요약 ────────────────────────────────
    with left_col:
        st.markdown('<div class="section-title">📋 주차별 수업 요약</div>', unsafe_allow_html=True)

        school_dates = [d for d in all_dates if not is_weekend(d) and not is_holiday(d)]
        week_groups = {}
        for d in school_dates:
            wk = get_week_number(d, start_date)
            week_groups.setdefault(wk, []).append(d)

        summary_rows = []
        for wk, wdates in week_groups.items():
            for d in wdates:
                date_key = d.isoformat()
                day_records = records.get(date_key, {})
                for cls in classes:
                    if cls in day_records:
                        summary_rows.append({
                            "주차": wk,
                            "날짜": d.strftime("%m/%d"),
                            "반": cls,
                            "차시": day_records[cls].get("차시",""),
                            "비고": day_records[cls].get("비고","")
                        })

        if summary_rows:
            df_summary = pd.DataFrame(summary_rows)
            st.dataframe(df_summary, use_container_width=True, hide_index=True,
                height=500)
        else:
            st.info("수업 기록이 없습니다.\n위에서 수업을 기록하면 여기에 표시됩니다.")

    # ── 오른쪽: 날짜별 진도표 ───────────────────────────
    with right_col:
        st.markdown('<div class="section-title">📊 날짜별 진도표</div>', unsafe_allow_html=True)

        # 인쇄 버튼
        print_col, filter_col = st.columns([1,3])
        with print_col:
            if st.button("🖨️ 인쇄용 보기"):
                st.markdown("""
                <script>window.print();</script>
                """, unsafe_allow_html=True)

        # HTML 테이블 생성
        class_headers = "".join(f"<th>{c}</th>" for c in classes)
        table_html = f"""
        <div style="overflow-x:auto; max-height:600px; overflow-y:auto;">
        <table class="progress-table">
        <thead>
            <tr>
                <th>주차</th><th>날짜</th><th>요일</th><th>원/교</th>
                {class_headers}<th>비고</th>
            </tr>
        </thead>
        <tbody>
        """

        prev_week = None
        for d in all_dates:
            if is_weekend(d):
                continue

            wk = get_week_number(d, start_date)
            hol = is_holiday(d)
            date_key = d.isoformat()
            day_records = records.get(date_key, {})
            sched_type = get_schedule_for_date(subj, d)
            is_today = (d == today)

            # 주차 구분선
            if wk != prev_week:
                table_html += f'<tr class="week-header"><td colspan="{4+len(classes)+1}">── {wk}주차 ({d.strftime("%Y.%m.%d")} 주간) ──</td></tr>'
                prev_week = wk

            # 행 클래스
            row_class = ""
            if is_today:
                row_class = "today-row"
            elif hol:
                row_class = "holiday-row"

            week_num_cell = f"{wk}" if d.weekday() == 0 else ""  # 월요일에만 주차 표시

            # 원/교 뱃지
            if sched_type == "원시간표":
                sched_badge = '<span class="badge-original">원</span>'
            elif sched_type == "교차시간표":
                sched_badge = '<span class="badge-cross">교</span>'
            elif sched_type == "fixed":
                sched_badge = '<span class="badge-fixed">고정</span>'
            else:
                sched_badge = "-"

            today_marker = " 🔵" if is_today else ""
            date_cell = f"{d.strftime('%m/%d')}{today_marker}"

            # 반별 셀
            class_cells = ""
            note_texts = []
            for cls in classes:
                if hol:
                    class_cells += f'<td style="color:#9f1239;">{hol}</td>'
                elif cls in day_records:
                    rec = day_records[cls]
                    lesson_num = rec.get("차시","")
                    note = rec.get("비고","")
                    cell_class = "absent-cell" if note and note != "정상수업" else "lesson-cell"
                    lesson_str = f"{lesson_num}차시" if lesson_num else ""
                    note_str = f"<br><small>{note}</small>" if note and note != "정상수업" else ""
                    class_cells += f'<td class="{cell_class}">{lesson_str}{note_str}</td>'
                    if note and note != "정상수업":
                        note_texts.append(f"{cls}:{note}")
                else:
                    # 수업 예정 여부 확인
                    exp_classes = get_classes_for_date(subj, d)
                    if cls in exp_classes:
                        class_cells += '<td style="color:#94a3b8; font-size:0.7rem;">예정</td>'
                    else:
                        class_cells += '<td>-</td>'

            note_col = ", ".join(note_texts) if note_texts else (hol if hol else "")

            table_html += f"""
            <tr class="{row_class}">
                <td>{week_num_cell}</td>
                <td>{date_cell}</td>
                <td>{WEEKDAYS[d.weekday()]}</td>
                <td>{sched_badge}</td>
                {class_cells}
                <td style="font-size:0.72rem; color:#64748b;">{note_col}</td>
            </tr>
            """

        table_html += "</tbody></table></div>"
        st.markdown(table_html, unsafe_allow_html=True)

    # ── 차시별 수업일 현황 (엑셀 오른쪽 파트) ───────────
    st.divider()
    st.markdown('<div class="section-title">📅 차시별 반별 수업 날짜 현황</div>', unsafe_allow_html=True)

    if units:
        # 차시별로 각 반이 언제 수업했는지
        lesson_date_map = {}  # {차시: {반: 날짜}}
        for date_key, day_rec in records.items():
            for cls, rec in day_rec.items():
                lesson = rec.get("차시")
                if lesson:
                    if lesson not in lesson_date_map:
                        lesson_date_map[lesson] = {}
                    lesson_date_map[lesson][cls] = date_key

        rows = []
        for u in units:
            row = {"차시": u["차시"], "단원": u["단원"]}
            for cls in classes:
                row[cls] = lesson_date_map.get(u["차시"],{}).get(cls, "")
            rows.append(row)

        df_lesson = pd.DataFrame(rows)
        st.dataframe(df_lesson, use_container_width=True, hide_index=True,
            column_config={cls: st.column_config.TextColumn(cls, width="small") for cls in classes})
    else:
        st.info("단원 관리 탭에서 차시와 단원명을 먼저 입력하세요.")
