import streamlit as st
import pandas as pd
import json, copy
from datetime import date, timedelta, datetime
import calendar

st.set_page_config(page_title="수업 진도 관리", page_icon="📚", layout="wide", initial_sidebar_state="expanded")

# ── CSS ─────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700&display=swap');
html, body, [class*="css"] { font-family: 'Noto Sans KR', sans-serif; }

.main-title {
    font-size: 1.5rem; font-weight: 700; color: #1a3a5c;
    border-left: 5px solid #2e7bcf; padding-left: 12px; margin-bottom: 0.5rem;
}
.section-title {
    font-size: 1rem; font-weight: 700; color: #2e7bcf;
    border-bottom: 2px solid #e8f0fb; padding-bottom: 4px; margin: 1rem 0 0.5rem 0;
}

/* 시간표 입력 테이블 */
.tt-table { width: 100%; border-collapse: collapse; font-size: 0.85rem; margin: 0.5rem 0; }
.tt-table th { background: #334155; color: white; padding: 6px 10px; text-align: center; }
.tt-table td { padding: 4px 6px; text-align: center; border: 1px solid #e2e8f0; }
.tt-table tr:nth-child(even) td { background: #f8fafc; }

/* 진도표 메인 테이블 - 엑셀 스타일 */
.excel-table { width: 100%; border-collapse: collapse; font-size: 0.8rem; }
.excel-table th {
    background: #1a3a5c; color: white; padding: 5px 6px;
    text-align: center; border: 1px solid #0f2540; font-weight: 500;
    position: sticky; top: 0; z-index: 2;
}
.excel-table td {
    padding: 3px 5px; text-align: center; border: 1px solid #cbd5e1;
    min-width: 40px; font-size: 0.78rem;
}
.excel-table tr:hover td { background: #eff6ff; }
.week-sep td { background: #e2e8f0 !important; font-weight: 600; color: #334155; font-size: 0.75rem; }
.today-row td { background: #fef3c7 !important; }
.today-row td:nth-child(2) { font-weight: 700; color: #b45309; }
.holiday-row td { background: #ffe4e6 !important; color: #be123c; font-size: 0.75rem; }
.lesson-cell { background: #dbeafe !important; color: #1e40af; font-weight: 600; }
.cancel-cell { background: #fde8e8 !important; color: #991b1b; font-size: 0.7rem; }

/* 원/교 뱃지 */
.b-orig { background: #dbeafe; color: #1d4ed8; padding: 1px 6px; border-radius: 8px; font-size: 0.7rem; font-weight: 600; }
.b-cross { background: #fce7f3; color: #be185d; padding: 1px 6px; border-radius: 8px; font-size: 0.7rem; font-weight: 600; }

/* 달력 스타일 */
.cal-table { border-collapse: collapse; font-size: 0.78rem; width: 100%; }
.cal-table th { background: #f1f5f9; padding: 4px; text-align: center; font-weight: 600; }
.cal-table td { padding: 3px; text-align: center; border: 1px solid #e2e8f0; min-width: 30px; }
.cal-orig { background: #dbeafe; }
.cal-cross { background: #fce7f3; }
.cal-holiday { background: #ffe4e6; color: #be123c; }
.cal-cancel { background: #fef3c7; }

@media print {
    .stSidebar, .stButton, .stTabs, [data-testid="stToolbar"],
    [data-testid="stHeader"] { display: none !important; }
    .main { margin: 0 !important; padding: 0 !important; }
    .excel-table th { background: #333 !important; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
}
</style>
""", unsafe_allow_html=True)

# ── 공휴일 ─────────────────────────────────────────────
@st.cache_data
def get_holidays(year):
    h = {
        f"{year}-01-01":"신정", f"{year}-03-01":"삼일절",
        f"{year}-05-05":"어린이날", f"{year}-06-06":"현충일",
        f"{year}-08-15":"광복절", f"{year}-10-03":"개천절",
        f"{year}-10-09":"한글날", f"{year}-12-25":"성탄절",
    }
    if year == 2026:
        h.update({
            "2026-02-17":"설날 연휴","2026-02-18":"설날","2026-02-19":"설날 연휴",
            "2026-05-01":"대체휴일","2026-05-24":"부처님오신날","2026-05-25":"대체휴일",
            "2026-06-03":"지방선거","2026-10-05":"추석 연휴","2026-10-06":"추석",
            "2026-10-07":"추석 연휴",
        })
    return h

# ── 세션 초기화 ────────────────────────────────────────
WEEKDAYS = ["월","화","수","목","금"]

def init():
    d = {
        "subjects": ["고급지구과학"],
        "cur_subj": "고급지구과학",
        "year": 2026,
        # 반 체크박스: {과목: [bool]*8}
        "class_checks": {"고급지구과학": [True]*8},
        # 시간표: {과목: {"original": {(요일,교시): [반목록]}, "cross": {(요일,교시): [반목록]}, "fixed": {(요일,교시): [반목록]}}}
        # JSON 저장을 위해 키를 "요일_교시" 문자열로
        "tt_original": {"고급지구과학": {}},
        "tt_cross": {"고급지구과학": {}},
        # 날짜별 원/교차: {과목: {날짜str: "원"/"교"}}
        "date_type": {"고급지구과학": {}},
        # 결강일: {과목: {날짜str: 메모}}
        "cancel_dates": {"고급지구과학": {}},
        # 시험 날짜: {과목: {"중간": 날짜str, "기말": 날짜str}}
        "exam_dates": {"고급지구과학": {"중간":"2026-04-23","기말":"2026-07-01"}},
        # 학기 범위
        "sem_start": {"1학기":"2026-03-02","2학기":"2026-09-01"},
        "sem_end": {"1학기":"2026-07-17","2학기":"2026-12-31"},
        "cur_sem": "1학기",
        # 단원: {과목: [{차시:int, 단원:str}]}
        "units": {"고급지구과학": []},
        # 수업 기록: {과목: {날짜str: {반str: 차시int}}}
        "records": {"고급지구과학": {}},
    }
    for k, v in d.items():
        if k not in st.session_state:
            st.session_state[k] = v

init()

def ensure_subj(s):
    for key, default in [
        ("class_checks",[False]*8),("tt_original",{}),("tt_cross",{}),
        ("date_type",{}),("cancel_dates",{}),
        ("exam_dates",{"중간":"","기말":""}),("units",[]),("records",{})
    ]:
        if s not in st.session_state[key]:
            st.session_state[key][s] = copy.deepcopy(default)

def get_classes(subj):
    checks = st.session_state.class_checks.get(subj, [False]*8)
    return [f"{i+1}반" for i in range(8) if i < len(checks) and checks[i]]

def get_dates(sem):
    s = date.fromisoformat(st.session_state.sem_start[sem])
    e = date.fromisoformat(st.session_state.sem_end[sem])
    dates = []
    c = s
    while c <= e:
        dates.append(c)
        c += timedelta(days=1)
    return dates

holidays = get_holidays(st.session_state.year)

def is_hol(d):
    return holidays.get(d.isoformat(), "")

def get_weeknum(d, start):
    return (d - start).days // 7 + 1

def get_classes_for_date(subj, d):
    """해당 날짜에 수업이 있는 반과 교시 반환: [(반, 교시)]"""
    if d.weekday() >= 5 or is_hol(d):
        return []
    day_str = WEEKDAYS[d.weekday()]
    dt = st.session_state.date_type.get(subj, {}).get(d.isoformat(), "")
    tt_orig = st.session_state.tt_original.get(subj, {})
    tt_cross = st.session_state.tt_cross.get(subj, {})
    results = []

    for period in range(1, 8):
        key = f"{day_str}_{period}"
        # 원시간표 셀
        orig_classes = tt_orig.get(key, [])
        cross_classes = tt_cross.get(key, [])

        for cls in orig_classes:
            if dt == "원":  # 원시간표 날이면 원시간표 반 수업
                results.append((cls, period))
            elif dt != "교":  # 원/교 미설정이면 원시간표 기본
                results.append((cls, period))

        for cls in cross_classes:
            if dt == "교":  # 교차시간표 날이면 교차 반 수업
                results.append((cls, period))

    # 원/교차 공통(고정): 양쪽 다 있는 경우 = 고정
    # 실제로는 같은 셀에 원/교 동시에 넣지 않으므로 위 로직으로 충분
    return results

# ── 사이드바 ────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="main-title">📚 수업 진도 관리</div>', unsafe_allow_html=True)
    st.caption("교차시간표 지원 진도 관리 시스템")
    st.divider()

    # 과목
    st.markdown('<div class="section-title">📖 과목 관리</div>', unsafe_allow_html=True)
    sc1, sc2 = st.columns([3,1])
    new_s = sc1.text_input("과목추가", placeholder="새 과목명", label_visibility="collapsed")
    if sc2.button("추가", key="add_subj") and new_s.strip():
        if new_s.strip() not in st.session_state.subjects:
            st.session_state.subjects.append(new_s.strip())
            ensure_subj(new_s.strip())
            st.rerun()

    subj = st.selectbox("과목 선택", st.session_state.subjects, key="subj_sel")
    st.session_state.cur_subj = subj
    ensure_subj(subj)

    if len(st.session_state.subjects) > 1:
        if st.button(f"'{subj}' 삭제"):
            st.session_state.subjects.remove(subj)
            st.session_state.cur_subj = st.session_state.subjects[0]
            st.rerun()

    st.divider()

    # 학년도 / 학기
    st.markdown('<div class="section-title">🗓️ 학년도 / 학기</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    st.session_state.year = c1.selectbox("학년도", [2025,2026,2027], index=1, key="yr")
    st.session_state.cur_sem = c2.selectbox("학기", ["1학기","2학기"], key="sem")
    sem = st.session_state.cur_sem

    st.session_state.sem_start[sem] = st.text_input("학기 시작일", st.session_state.sem_start[sem], key="ss")
    st.session_state.sem_end[sem] = st.text_input("학기 종료일", st.session_state.sem_end[sem], key="se")

    st.divider()

    # 시험 날짜
    st.markdown('<div class="section-title">📝 시험 날짜</div>', unsafe_allow_html=True)
    ex = st.session_state.exam_dates.get(subj, {"중간":"","기말":""})
    ex["중간"] = st.text_input("중간고사 시작일", ex.get("중간",""), key="mid_ex", placeholder="2026-04-23")
    ex["기말"] = st.text_input("기말고사 시작일", ex.get("기말",""), key="fin_ex", placeholder="2026-07-01")
    st.session_state.exam_dates[subj] = ex

    st.divider()

    # 반 구성 (체크박스)
    st.markdown('<div class="section-title">🏫 반 구성</div>', unsafe_allow_html=True)
    checks = st.session_state.class_checks.get(subj, [False]*8)
    cols4 = st.columns(4)
    new_checks = []
    for i in range(8):
        with cols4[i % 4]:
            v = st.checkbox(f"{i+1}반", value=checks[i] if i < len(checks) else False, key=f"cls_{i}")
            new_checks.append(v)
    st.session_state.class_checks[subj] = new_checks


# ── 메인 영역 ──────────────────────────────────────────
subj = st.session_state.cur_subj
sem = st.session_state.cur_sem
classes = get_classes(subj)

st.markdown(f'<div class="main-title">📚 {subj} — {st.session_state.year}학년도 {sem} 진도 관리</div>', unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["⚙️ 시간표 설정", "📅 원/교차 · 결강 설정", "📊 진도표 · 단원 관리"])

# ══════════════════════════════════════════════
# TAB 1: 시간표 설정 (요일×교시 테이블, 이미지 형식)
# ══════════════════════════════════════════════
with tab1:
    st.markdown('<div class="section-title">원시간표 입력</div>', unsafe_allow_html=True)
    st.info("각 셀에 해당 교시에 수업하는 **반 번호**를 입력하세요. 여러 반은 쉼표로 구분 (예: `2,6`). 원시간표 시행 시 이 시간표가 적용됩니다.")

    if not classes:
        st.warning("사이드바에서 반을 먼저 선택해주세요.")
    else:
        tt_orig = st.session_state.tt_original.get(subj, {})

        # 헤더
        hcols = st.columns([1.5] + [1]*5)
        hcols[0].markdown("**교시**")
        for i, d in enumerate(WEEKDAYS):
            hcols[i+1].markdown(f"**{d}**")

        new_tt_orig = {}
        for period in range(1, 8):
            rcols = st.columns([1.5] + [1]*5)
            rcols[0].markdown(f"**{period}교시**")
            for i, day in enumerate(WEEKDAYS):
                key = f"{day}_{period}"
                cur = ",".join(tt_orig.get(key, []))
                val = rcols[i+1].text_input(f"o_{day}_{period}", value=cur,
                    label_visibility="collapsed", key=f"tto_{day}_{period}",
                    placeholder="반번호")
                if val.strip():
                    parsed = [f"{v.strip()}반" if not v.strip().endswith("반") else v.strip()
                              for v in val.split(",") if v.strip()]
                    new_tt_orig[key] = parsed

        if st.button("원시간표 저장", type="primary"):
            st.session_state.tt_original[subj] = new_tt_orig
            st.success("원시간표가 저장되었습니다!")

    st.divider()
    st.markdown('<div class="section-title">교차시간표 입력</div>', unsafe_allow_html=True)
    st.info("교차시간표 시행 시 **원시간표와 달라지는 반**만 입력하세요. 비워두면 원시간표와 동일합니다.")

    if classes:
        tt_cross = st.session_state.tt_cross.get(subj, {})

        hcols2 = st.columns([1.5] + [1]*5)
        hcols2[0].markdown("**교시**")
        for i, d in enumerate(WEEKDAYS):
            hcols2[i+1].markdown(f"**{d}**")

        new_tt_cross = {}
        for period in range(1, 8):
            rcols2 = st.columns([1.5] + [1]*5)
            rcols2[0].markdown(f"**{period}교시**")
            for i, day in enumerate(WEEKDAYS):
                key = f"{day}_{period}"
                cur = ",".join(tt_cross.get(key, []))
                val = rcols2[i+1].text_input(f"c_{day}_{period}", value=cur,
                    label_visibility="collapsed", key=f"ttc_{day}_{period}",
                    placeholder="반번호")
                if val.strip():
                    parsed = [f"{v.strip()}반" if not v.strip().endswith("반") else v.strip()
                              for v in val.split(",") if v.strip()]
                    new_tt_cross[key] = parsed

        if st.button("교차시간표 저장", type="primary"):
            st.session_state.tt_cross[subj] = new_tt_cross
            st.success("교차시간표가 저장되었습니다!")

    # CSV 업로드
    st.divider()
    st.markdown('<div class="section-title">📂 시간표 파일 업로드 (선택)</div>', unsafe_allow_html=True)
    st.caption("CSV 형식: `유형,요일,교시,반` (유형: 원/교차)")
    upload = st.file_uploader("CSV 업로드", type=["csv"], key="tt_upload")
    if upload:
        try:
            df = pd.read_csv(upload)
            new_o, new_c = {}, {}
            for _, row in df.iterrows():
                typ = str(row["유형"]).strip()
                day = str(row["요일"]).strip()
                per = int(row["교시"])
                cls = str(row["반"]).strip()
                if not cls.endswith("반"): cls += "반"
                key = f"{day}_{per}"
                if "원" in typ:
                    new_o.setdefault(key, []).append(cls)
                else:
                    new_c.setdefault(key, []).append(cls)
            st.session_state.tt_original[subj] = new_o
            st.session_state.tt_cross[subj] = new_c
            st.success("시간표가 업로드되었습니다!")
            st.rerun()
        except Exception as e:
            st.error(f"파일 형식 오류: {e}")


# ══════════════════════════════════════════════
# TAB 2: 원/교차 · 결강 설정 (달력형)
# ══════════════════════════════════════════════
with tab2:
    try:
        all_dates = get_dates(sem)
    except:
        st.error("학기 날짜를 확인해주세요.")
        st.stop()

    dt_map = st.session_state.date_type.get(subj, {})
    cancel_map = st.session_state.cancel_dates.get(subj, {})

    # ── 일괄 설정 ───────────────────────────────────
    st.markdown('<div class="section-title">📌 날짜 범위 일괄 설정</div>', unsafe_allow_html=True)

    bc1, bc2, bc3, bc4 = st.columns(4)
    b_start = bc1.date_input("시작일", value=all_dates[0], key="bs")
    b_end = bc2.date_input("종료일", value=all_dates[min(6, len(all_dates)-1)], key="be")
    b_type = bc3.selectbox("유형", ["원시간표","교차시간표"], key="bt")
    if bc4.button("일괄 적용", use_container_width=True):
        c = b_start
        while c <= b_end:
            if c.weekday() < 5 and not is_hol(c):
                dt_map[c.isoformat()] = "원" if "원" in b_type else "교"
            c += timedelta(days=1)
        st.session_state.date_type[subj] = dt_map
        st.success("적용 완료!")
        st.rerun()

    st.divider()

    # ── 달력 표시 (월별) ────────────────────────────
    st.markdown('<div class="section-title">📅 원/교차 시간표 달력</div>', unsafe_allow_html=True)
    st.caption("🟦 원시간표  🟪 교차시간표  🟥 공휴일  🟨 결강")

    # 학기 범위의 월 목록
    start_d = all_dates[0]
    end_d = all_dates[-1]
    months = []
    cur_m = date(start_d.year, start_d.month, 1)
    while cur_m <= end_d:
        months.append(cur_m)
        if cur_m.month == 12:
            cur_m = date(cur_m.year+1, 1, 1)
        else:
            cur_m = date(cur_m.year, cur_m.month+1, 1)

    # 2열씩 달력
    for mi in range(0, len(months), 2):
        mcols = st.columns(2)
        for col_idx in range(2):
            if mi + col_idx >= len(months):
                break
            m = months[mi + col_idx]
            with mcols[col_idx]:
                st.markdown(f"**{m.year}년 {m.month}월**")
                _, days_in = calendar.monthrange(m.year, m.month)

                with st.expander("날짜별 설정", expanded=True):
                    # 주별로 나눠서 표시
                    week_dates = []
                    for day_num in range(1, days_in+1):
                        d = date(m.year, m.month, day_num)
                        if d < start_d or d > end_d:
                            continue
                        if d.weekday() >= 5:
                            continue
                        week_dates.append(d)

                    for d in week_dates:
                        hol = is_hol(d)
                        dk = d.isoformat()
                        cur_dt = dt_map.get(dk, "")
                        is_cancel = dk in cancel_map

                        label = f"{d.strftime('%m/%d')}({WEEKDAYS[d.weekday()]})"

                        if hol:
                            st.markdown(f"🔴 {label} — {hol}")
                        else:
                            dc1, dc2, dc3, dc4 = st.columns([2, 1.5, 1, 2])
                            dc1.markdown(f"**{label}**")
                            sel_type = dc2.selectbox("유형", ["미설정","원","교"],
                                index=["미설정","원","교"].index(cur_dt) if cur_dt in ["원","교"] else 0,
                                key=f"dt_{dk}", label_visibility="collapsed")
                            dt_map[dk] = sel_type if sel_type != "미설정" else ""

                            cancel_chk = dc3.checkbox("결강", value=is_cancel, key=f"cx_{dk}")
                            if cancel_chk:
                                memo = dc4.text_input("메모", value=cancel_map.get(dk,""),
                                    key=f"cm_{dk}", label_visibility="collapsed", placeholder="사유")
                                cancel_map[dk] = memo
                            elif dk in cancel_map:
                                del cancel_map[dk]

    st.session_state.date_type[subj] = dt_map
    st.session_state.cancel_dates[subj] = cancel_map


# ══════════════════════════════════════════════
# TAB 3: 진도표 + 단원 관리
# ══════════════════════════════════════════════
with tab3:
    if not classes:
        st.warning("사이드바에서 반을 먼저 선택해주세요.")
        st.stop()

    try:
        all_dates = get_dates(sem)
    except:
        st.error("학기 날짜 설정을 확인해주세요.")
        st.stop()

    today = date.today()
    start_d = all_dates[0]
    records = st.session_state.records.get(subj, {})
    units = st.session_state.units.get(subj, [])
    unit_map = {u["차시"]: u["단원"] for u in units}
    cancel_map = st.session_state.cancel_dates.get(subj, {})
    dt_map = st.session_state.date_type.get(subj, {})
    ex = st.session_state.exam_dates.get(subj, {"중간":"","기말":""})

    # ── 상단: 수업 기록 입력 + 단원 관리 나란히 ────────
    rec_col, unit_col = st.columns([1, 1])

    with rec_col:
        st.markdown('<div class="section-title">✏️ 수업 기록 입력</div>', unsafe_allow_html=True)
        r1, r2 = st.columns(2)
        rec_date = r1.date_input("날짜", value=today, key="rd")
        rec_cls = r2.selectbox("반", classes, key="rc")
        r3, r4, r5 = st.columns([1,2,1])
        rec_lesson = r3.number_input("차시", min_value=0, max_value=200, value=1, key="rl",
            help="0 입력 시 해당 기록 삭제")
        rec_note = r4.text_input("비고", key="rn", placeholder="수행평가, 보강 등")
        if r5.button("기록", type="primary", use_container_width=True):
            dk = rec_date.isoformat()
            if dk not in records: records[dk] = {}
            if rec_lesson == 0:
                records[dk].pop(rec_cls, None)
            else:
                records[dk][rec_cls] = {"차시": rec_lesson, "비고": rec_note}
            st.session_state.records[subj] = records
            st.rerun()

    with unit_col:
        st.markdown('<div class="section-title">📖 단원 관리</div>', unsafe_allow_html=True)
        u1, u2, u3 = st.columns([1, 3, 1])
        new_ln = u1.number_input("차시", min_value=1, max_value=200, value=len(units)+1, key="nln")
        new_lnm = u2.text_input("단원명", key="nlnm", placeholder="예: Ⅰ-2-02. 지질도와 한반도",
            label_visibility="collapsed")
        if u3.button("추가", key="add_unit", use_container_width=True) and new_lnm.strip():
            existing = [u["차시"] for u in units]
            if new_ln in existing:
                st.warning(f"{new_ln}차시 이미 존재")
            else:
                units.append({"차시": new_ln, "단원": new_lnm.strip()})
                units.sort(key=lambda x: x["차시"])
                st.session_state.units[subj] = units
                st.rerun()

        if units:
            edited = st.data_editor(pd.DataFrame(units), use_container_width=True,
                num_rows="dynamic", height=200, key="ued",
                column_config={
                    "차시": st.column_config.NumberColumn("차시", min_value=1, width="small"),
                    "단원": st.column_config.TextColumn("단원명", width="large"),
                })
            if st.button("단원 저장", key="save_units"):
                nu = edited.dropna(subset=["차시","단원"]).to_dict("records")
                nu = [{"차시":int(u["차시"]),"단원":str(u["단원"])} for u in nu]
                nu.sort(key=lambda x: x["차시"])
                st.session_state.units[subj] = nu
                st.success("저장 완료!")
                st.rerun()

    st.divider()

    # ── 인쇄 버튼 ──────────────────────────────────
    pc1, pc2, pc3 = st.columns([1,1,4])
    if pc1.button("🖨️ 인쇄용 보기"):
        st.markdown("<script>window.print();</script>", unsafe_allow_html=True)
    view_mode = pc2.selectbox("보기", ["중간고사 전","기말고사 전","전체"], key="vm", label_visibility="collapsed")

    # 날짜 필터
    school_dates = [d for d in all_dates if d.weekday() < 5]
    if view_mode == "중간고사 전" and ex.get("중간"):
        try:
            mid_d = date.fromisoformat(ex["중간"])
            school_dates = [d for d in school_dates if d < mid_d]
        except: pass
    elif view_mode == "기말고사 전" and ex.get("기말"):
        try:
            fin_d = date.fromisoformat(ex["기말"])
            mid_d = date.fromisoformat(ex["중간"]) if ex.get("중간") else start_d
            school_dates = [d for d in school_dates if d >= mid_d and d < fin_d]
        except: pass

    # ── 진도표: 왼쪽(주차별 날짜표) + 오른쪽(차시별 날짜표) ──
    left_col, right_col = st.columns([3, 2])

    # ── 왼쪽: 엑셀 좌측 파트 (날짜별 × 반별) ──────
    with left_col:
        st.markdown('<div class="section-title">📋 날짜별 진도 현황</div>', unsafe_allow_html=True)

        # 테이블 HTML 생성
        cls_th = "".join(f"<th>{c}</th>" for c in classes)
        html = f"""<div style="overflow-x:auto; max-height:650px; overflow-y:auto;">
        <table class="excel-table">
        <thead><tr>
            <th>주차</th><th>날짜</th><th>요일</th><th>원/교</th>
            {cls_th}<th>비고</th>
        </tr></thead><tbody>"""

        prev_wk = None
        for d in school_dates:
            hol = is_hol(d)
            dk = d.isoformat()
            wk = get_weeknum(d, start_d)
            day_str = WEEKDAYS[d.weekday()]
            is_td = (d == today)
            is_cancel = dk in cancel_map
            day_rec = records.get(dk, {})
            d_type = dt_map.get(dk, "")

            # 주차 구분
            if wk != prev_wk:
                html += f'<tr class="week-sep"><td colspan="{4+len(classes)+1}">── {wk}주차 ──</td></tr>'
                prev_wk = wk

            row_cls = "today-row" if is_td else ("holiday-row" if hol else "")
            wk_cell = str(wk) if d.weekday() == 0 else ""
            td_marker = " ◀ 오늘" if is_td else ""
            date_str = d.strftime("%m/%d") + td_marker

            # 원/교 뱃지
            if d_type == "원":
                badge = '<span class="b-orig">원</span>'
            elif d_type == "교":
                badge = '<span class="b-cross">교</span>'
            else:
                badge = "-"

            # 반별 셀
            cells = ""
            notes = []
            for cls in classes:
                if hol:
                    cells += f'<td class="holiday-row">{hol[:2]}</td>'
                elif is_cancel:
                    cells += f'<td class="cancel-cell">결강</td>'
                elif cls in day_rec:
                    r = day_rec[cls]
                    ln = r.get("차시","")
                    nt = r.get("비고","")
                    cells += f'<td class="lesson-cell">{ln}</td>'
                    if nt: notes.append(f"{cls}:{nt}")
                else:
                    # 예정 수업 확인
                    exp = get_classes_for_date(subj, d)
                    exp_cls = [x[0] for x in exp]
                    if cls in exp_cls:
                        cells += '<td style="color:#94a3b8; font-size:0.7rem;">·</td>'
                    else:
                        cells += '<td>-</td>'

            note_txt = cancel_map.get(dk, "") if is_cancel else ", ".join(notes) if notes else (hol if hol else "")

            html += f'<tr class="{row_cls}"><td>{wk_cell}</td><td>{date_str}</td><td>{day_str}</td><td>{badge}</td>{cells}<td style="font-size:0.7rem;color:#64748b;">{note_txt}</td></tr>'

        html += "</tbody></table></div>"
        st.markdown(html, unsafe_allow_html=True)

    # ── 오른쪽: 엑셀 우측 파트 (차시별 × 반별 날짜) ──
    with right_col:
        st.markdown('<div class="section-title">📅 차시별 수업 날짜</div>', unsafe_allow_html=True)

        if not units:
            st.info("단원을 먼저 입력하세요.")
        else:
            # 차시별 날짜 매핑 구축
            lesson_dates = {}  # {차시: {반: 날짜str}}
            for dk, day_rec in records.items():
                for cls, rec in day_rec.items():
                    ln = rec.get("차시")
                    if ln:
                        lesson_dates.setdefault(ln, {})[cls] = dk

            cls_th2 = "".join(f"<th>{c}</th>" for c in classes)
            html2 = f"""<div style="overflow-x:auto; max-height:650px; overflow-y:auto;">
            <table class="excel-table">
            <thead><tr><th>차시</th>{cls_th2}<th>단원</th></tr></thead><tbody>"""

            for u in units:
                ln = u["차시"]
                unit_name = u["단원"]
                cells2 = ""
                for cls in classes:
                    d_str = lesson_dates.get(ln, {}).get(cls, "")
                    if d_str:
                        try:
                            d_obj = date.fromisoformat(d_str)
                            cells2 += f'<td class="lesson-cell">{d_obj.strftime("%m/%d")}</td>'
                        except:
                            cells2 += f'<td>{d_str}</td>'
                    else:
                        cells2 += '<td>-</td>'

                html2 += f'<tr><td>{ln}</td>{cells2}<td style="text-align:left; font-size:0.75rem;">{unit_name}</td></tr>'

            html2 += "</tbody></table></div>"
            st.markdown(html2, unsafe_allow_html=True)

    # ── 하단: 요일별/반별 수업 교시 요약 (엑셀 하단 파트) ──
    st.divider()
    st.markdown('<div class="section-title">🕐 요일별 / 반별 수업 교시</div>', unsafe_allow_html=True)

    tt_orig = st.session_state.tt_original.get(subj, {})
    tt_cross = st.session_state.tt_cross.get(subj, {})

    if tt_orig or tt_cross:
        cls_th3 = "".join(f"<th>{c}</th>" for c in classes)

        html3 = f"""<table class="excel-table">
        <thead><tr><th></th><th>요일</th>{cls_th3}</tr></thead><tbody>"""

        for label, tt_data in [("원", tt_orig), ("교", tt_cross)]:
            badge_cls = "b-orig" if label == "원" else "b-cross"
            for day in WEEKDAYS:
                cells3 = ""
                for cls in classes:
                    periods = []
                    for p in range(1, 8):
                        key = f"{day}_{p}"
                        if cls in tt_data.get(key, []):
                            periods.append(f"{p}교시")
                    cells3 += f'<td>{"<br>".join(periods) if periods else "-"}</td>'
                show_label = f'<span class="{badge_cls}">{label}</span>' if day == "월" else ""
                html3 += f'<tr><td>{show_label}</td><td>{day}</td>{cells3}</tr>'

            if label == "원":
                html3 += f'<tr class="week-sep"><td colspan="{2+len(classes)}"></td></tr>'

        html3 += "</tbody></table>"
        st.markdown(html3, unsafe_allow_html=True)
    else:
        st.info("시간표 설정 탭에서 시간표를 먼저 입력하세요.")
