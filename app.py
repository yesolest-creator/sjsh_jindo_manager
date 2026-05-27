import streamlit as st
import pandas as pd
import copy
from datetime import date, timedelta
import calendar

st.set_page_config(page_title="수업 진도 관리", page_icon="📚", layout="wide", initial_sidebar_state="expanded")

# ── CSS ─────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700&display=swap');
html, body, [class*="css"] { font-family: 'Noto Sans KR', sans-serif; }

.main-title {
    font-size: 1.4rem; font-weight: 700; color: #1a3a5c;
    border-left: 5px solid #2e7bcf; padding-left: 10px; margin-bottom: 0.4rem;
}
.section-title {
    font-size: 0.95rem; font-weight: 700; color: #2e7bcf;
    border-bottom: 2px solid #e8f0fb; padding-bottom: 3px; margin: 0.8rem 0 0.4rem 0;
}

/* ── 과목 목록 ── */
.subj-item {
    display: flex; align-items: center; justify-content: space-between;
    padding: 6px 10px; margin: 2px 0; border-radius: 6px; cursor: pointer;
}
.subj-active { background: #e3f2fd; border-left: 3px solid #1565c0; font-weight: 600; }
.subj-inactive { background: #f5f5f5; }
.subj-inactive:hover { background: #e8e8e8; }

/* ── 시간표 입력 셀 미리보기 ── */
.tt-preview { width:100%; border-collapse:collapse; font-size:0.8rem; margin-top:0.5rem; }
.tt-preview th { background:#1e3a5f; color:#fff; padding:4px 6px; text-align:center; border:1px solid #152d4a; }
.tt-preview td { padding:4px 6px; text-align:center; border:1px solid #cbd5e1; min-width:40px; }
.tt-fixed { background:#fff3e0 !important; color:#e65100; font-weight:600; }
.tt-cross { background:#e3f2fd !important; color:#1565c0; font-weight:600; }
.tt-empty { background:#f5f5f5 !important; color:#bdbdbd; }
.tt-blocked { background:#eceff1 !important; color:#78909c; font-weight:500; }

/* ── 진도 현황 테이블 ── */
.view-table { border-collapse:collapse; font-size:0.7rem; table-layout:fixed; }
.view-table th {
    background:#1e3a5f; color:#fff; padding:2px 3px; text-align:center;
    border:1px solid #152d4a; font-size:0.68rem; font-weight:500;
    position:sticky; top:0; z-index:2; overflow:hidden;
}
.view-table td {
    padding:1px 2px; text-align:center; border:1px solid #cbd5e1;
    font-size:0.68rem; line-height:1.2; overflow:hidden; white-space:nowrap;
}
.view-table tr:hover td { background:#f0f7ff; }

/* 열 너비 고정 */
.col-wk { width:24px; }
.col-date { width:38px; }
.col-day { width:28px; }
.col-oc { width:24px; }
.col-cls { width:28px; }
.col-note { width:80px; }

/* 셀 색상 — 파스텔톤 */
.c-fixed { background:#fff3e0 !important; color:#e65100; }
.c-orig  { background:#e8f5e9 !important; color:#2e7d32; }
.c-cross { background:#e3f2fd !important; color:#1565c0; }
.c-edit  { background:#fff !important; border:2px dashed #9e9e9e !important; }
.c-cancel{ background:#eeeeee !important; color:#9e9e9e; }
.c-hol   { background:#ffebee !important; color:#c62828; }
.c-exam  { background:#f3e5f5 !important; color:#6a1b9a; }

/* 첫 수업 반 강조 */
.c-first { color:#d32f2f !important; font-weight:700 !important; }

/* 날짜 색상 (인쇄 미적용) */
.d-past  { color:#bdbdbd !important; }
.d-today { background:#ffeb3b !important; color:#000 !important; font-weight:700; }

/* 뱃지 */
.b-orig  { background:#c8e6c9; color:#2e7d32; padding:1px 4px; border-radius:5px; font-size:0.6rem; font-weight:600; }
.b-cross { background:#bbdefb; color:#1565c0; padding:1px 4px; border-radius:5px; font-size:0.6rem; font-weight:600; }

/* 주차 구분 */
.wk-sep td { background:#eceff1 !important; font-weight:600; color:#455a64; font-size:0.65rem; padding:1px; }

/* ── 학사일정 버튼 ── */
.sch-btn {
    display:inline-block; padding:4px 10px; border-radius:5px;
    font-size:0.75rem; font-weight:600; cursor:pointer; text-align:center;
    border:2px solid transparent; margin:1px;
}
.btn-orig { background:#e8f5e9; color:#2e7d32; border-color:#a5d6a7; }
.btn-orig-active { background:#2e7d32; color:#fff; border-color:#2e7d32; }
.btn-cross { background:#e3f2fd; color:#1565c0; border-color:#90caf9; }
.btn-cross-active { background:#1565c0; color:#fff; border-color:#1565c0; }
.btn-cancel { background:#f5f5f5; color:#757575; border-color:#e0e0e0; }
.btn-cancel-active { background:#757575; color:#fff; border-color:#757575; }

/* ── 시수 요약 테이블 ── */
.hours-table { border-collapse:collapse; font-size:0.78rem; }
.hours-table th { background:#1e3a5f; color:#fff; padding:3px 8px; text-align:center; border:1px solid #152d4a; }
.hours-table td { padding:3px 8px; text-align:center; border:1px solid #cbd5e1; font-weight:600; }

/* ── 인쇄 ── */
@media print {
    .stSidebar, .stButton, .stTabs, [data-testid="stToolbar"],
    [data-testid="stHeader"], .no-print, .stRadio { display:none !important; }
    .main .block-container { margin:0 !important; padding:0 !important; max-width:100% !important; }
    @page { size:A4 portrait; margin:6mm; }
    .view-table { font-size:0.58rem !important; }
    .view-table th { background:#333 !important; -webkit-print-color-adjust:exact; print-color-adjust:exact; }
    .view-table td { padding:1px 1px !important; }
    .d-past { color:inherit !important; }
    .d-today { background:transparent !important; color:inherit !important; font-weight:normal; }
    .section-title { font-size:0.8rem; margin:4px 0; }
}
</style>
""", unsafe_allow_html=True)

# ── 공휴일 ──────────────────────────────────────────────
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
            "2026-02-17":"설날연휴","2026-02-18":"설날","2026-02-19":"설날연휴",
            "2026-05-01":"대체휴일","2026-05-24":"부처님오신날","2026-05-25":"대체휴일",
            "2026-06-03":"지방선거","2026-10-05":"추석연휴","2026-10-06":"추석",
            "2026-10-07":"추석연휴",
        })
    return h

WEEKDAYS = ["월","화","수","목","금"]
BLOCKED_CELLS = {("수",6), ("수",7)}

# ── 세션 초기화 ─────────────────────────────────────────
def init():
    d = {
        "subjects": ["고급지구과학"],
        "cur_subj": "고급지구과학",
        "year": 2026,
        "class_checks": {"고급지구과학": [True]*8},
        "timetable": {"고급지구과학": {}},
        "schedule": {"고급지구과학": {}},
        "exams": {"고급지구과학": {
            "mid_start": date(2026,4,23), "mid_end": date(2026,4,24),
            "fin_start": date(2026,7,1), "fin_end": date(2026,7,2),
        }},
        "sem_start": {"1학기": date(2026,3,2), "2학기": date(2026,9,1)},
        "sem_end": {"1학기": date(2026,7,17), "2학기": date(2026,12,31)},
        "cur_sem": "1학기",
        "overrides": {"고급지구과학": {}},
        # 수업내용: {과목: {"mid": {차시str: 내용}, "fin": {차시str: 내용}}}
        "lesson_contents": {"고급지구과학": {"mid":{}, "fin":{}}},
        "delete_confirm": "",
    }
    for k, v in d.items():
        if k not in st.session_state:
            st.session_state[k] = v
init()

def ensure_subj(s):
    for key, default in [
        ("class_checks",[False]*8),("timetable",{}),("schedule",{}),
        ("exams",{"mid_start":None,"mid_end":None,"fin_start":None,"fin_end":None}),
        ("overrides",{}),("lesson_contents",{"mid":{},"fin":{}})
    ]:
        if s not in st.session_state[key]:
            st.session_state[key][s] = copy.deepcopy(default)

def get_classes(subj):
    checks = st.session_state.class_checks.get(subj, [False]*8)
    return [f"{i+1}반" for i in range(8) if i < len(checks) and checks[i]]

def get_dates(start, end):
    out, c = [], start
    while c <= end:
        out.append(c)
        c += timedelta(days=1)
    return out

def get_weeknum(d, start):
    return (d - start).days // 7 + 1

def parse_tt_cell(val):
    val = str(val).strip()
    if not val or val == "nan": return None
    if not val.replace(",","").replace(" ","").isdigit():
        return {"blocked": val}
    parts = [p.strip() for p in val.split(",") if p.strip()]
    if len(parts) == 1: return {"fixed": f"{parts[0]}반"}
    elif len(parts) == 2: return {"orig": f"{parts[0]}반", "cross": f"{parts[1]}반"}
    return None

def get_effective_day(subj, d):
    sch = st.session_state.schedule.get(subj, {}).get(d.isoformat(), {})
    if not isinstance(sch, dict): sch = {}
    ov = sch.get("day_override", "")
    if ov and ov in WEEKDAYS: return ov
    return WEEKDAYS[d.weekday()] if d.weekday() < 5 else ""

def get_schedule_type(subj, d):
    sch = st.session_state.schedule.get(subj, {}).get(d.isoformat(), {})
    if not isinstance(sch, dict): return ""
    return sch.get("type", "")

def get_note(subj, d):
    sch = st.session_state.schedule.get(subj, {}).get(d.isoformat(), {})
    if not isinstance(sch, dict): return ""
    return sch.get("note", "")

def is_exam_day(subj, d):
    ex = st.session_state.exams.get(subj, {})
    for prefix, label in [("mid","중간고사"),("fin","기말고사")]:
        s, e = ex.get(f"{prefix}_start"), ex.get(f"{prefix}_end")
        if s and e and isinstance(s, date) and isinstance(e, date) and s <= d <= e:
            return label
    return ""

def get_classes_for_date(subj, d):
    hols = get_holidays(st.session_state.year)
    if d.weekday() >= 5 or d.isoformat() in hols or is_exam_day(subj, d) or get_schedule_type(subj, d) == "결강":
        return []
    eff_day = get_effective_day(subj, d)
    if not eff_day: return []
    tt = st.session_state.timetable.get(subj, {})
    stype = get_schedule_type(subj, d)
    results = []
    for period in range(1, 8):
        if (eff_day, period) in BLOCKED_CELLS: continue
        parsed = parse_tt_cell(tt.get(f"{eff_day}_{period}", ""))
        if not parsed or "blocked" in parsed: continue
        if "fixed" in parsed:
            results.append((parsed["fixed"], "fixed"))
        elif "orig" in parsed and "cross" in parsed:
            results.append((parsed["cross"] if stype == "교" else parsed["orig"],
                           "cross" if stype == "교" else "orig"))
    return results

holidays = get_holidays(st.session_state.year)

# ── 진도 계산 ───────────────────────────────────────────
def compute_progress(subj, date_start, date_end, classes, reset_counter=True):
    """진도 자동 계산. reset_counter=True면 1차시부터 시작."""
    all_dates = get_dates(date_start, date_end)
    school_dates = [d for d in all_dates if d.weekday() < 5]
    overrides = st.session_state.overrides.get(subj, {})
    class_counter = {cls: 1 for cls in classes}
    progress = {}
    total_hours = {cls: 0 for cls in classes}

    for d in school_dates:
        dk = d.isoformat()
        progress[dk] = {}
        if holidays.get(dk) or is_exam_day(subj, d) or get_schedule_type(subj, d) == "결강":
            continue
        for cls, ctype in get_classes_for_date(subj, d):
            if cls not in classes: continue
            ov = overrides.get(dk, {}).get(cls)
            if ov is not None and ov != "":
                try:
                    lesson = int(ov)
                    progress[dk][cls] = {"차시": lesson, "type": ctype, "edited": True}
                except:
                    progress[dk][cls] = {"차시": "", "type": ctype, "edited": True}
            else:
                progress[dk][cls] = {"차시": class_counter[cls], "type": ctype, "edited": False}
                class_counter[cls] += 1
            total_hours[cls] = total_hours.get(cls, 0) + 1

    return progress, total_hours

def get_first_class_per_lesson(progress, classes):
    """각 차시별로 가장 먼저 수업하는 (날짜, 반) 반환"""
    first = {}  # {차시: (날짜str, 반str)}
    for dk in sorted(progress.keys()):
        for cls in classes:
            info = progress[dk].get(cls, {})
            ln = info.get("차시")
            if ln and isinstance(ln, int) and ln not in first:
                first[ln] = (dk, cls)
    return first

def get_period_dates(subj, exam_key):
    """시험 기간에 따른 날짜 범위 반환"""
    ex = st.session_state.exams.get(subj, {})
    sem_s = st.session_state.sem_start[st.session_state.cur_sem]
    sem_e = st.session_state.sem_end[st.session_state.cur_sem]

    if exam_key == "mid":
        start = sem_s
        end = ex.get("mid_start")
        if end and isinstance(end, date):
            end = end - timedelta(days=1)
        else:
            end = sem_e
    else:  # fin
        mid_end = ex.get("mid_end")
        start = mid_end + timedelta(days=1) if mid_end and isinstance(mid_end, date) else sem_s
        fin_start = ex.get("fin_start")
        if fin_start and isinstance(fin_start, date):
            end = fin_start - timedelta(days=1)
        else:
            end = sem_e
    return start, end


# ── 사이드바 ────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="main-title">📚 수업 진도 관리</div>', unsafe_allow_html=True)
    st.caption("교차시간표 지원 · 자동 시수 계산")
    st.divider()

    # 과목 관리
    st.markdown('<div class="section-title">📖 과목</div>', unsafe_allow_html=True)
    sc1, sc2 = st.columns([3,1])
    new_s = sc1.text_input("새 과목", placeholder="과목명 입력", label_visibility="collapsed")
    if sc2.button("추가", key="as") and new_s.strip():
        if new_s.strip() not in st.session_state.subjects:
            st.session_state.subjects.append(new_s.strip())
            ensure_subj(new_s.strip())
            st.rerun()

    # 과목 목록 (클릭 선택 + 삭제)
    for s in st.session_state.subjects:
        sc_a, sc_b = st.columns([5, 1])
        with sc_a:
            is_active = (s == st.session_state.cur_subj)
            if st.button(f"{'▶ ' if is_active else '   '}{s}",
                key=f"sel_{s}", use_container_width=True,
                type="primary" if is_active else "secondary"):
                st.session_state.cur_subj = s
                st.session_state.delete_confirm = ""
                st.rerun()
        with sc_b:
            if len(st.session_state.subjects) > 1:
                if st.button("🗑️", key=f"del_{s}"):
                    st.session_state.delete_confirm = s
                    st.rerun()

    # 삭제 확인
    if st.session_state.delete_confirm:
        dc = st.session_state.delete_confirm
        st.warning(f"**'{dc}'** 과목을 삭제하시겠습니까?")
        dc1, dc2 = st.columns(2)
        if dc1.button("삭제", type="primary", key="confirm_del"):
            st.session_state.subjects.remove(dc)
            if st.session_state.cur_subj == dc:
                st.session_state.cur_subj = st.session_state.subjects[0]
            st.session_state.delete_confirm = ""
            st.rerun()
        if dc2.button("취소", key="cancel_del"):
            st.session_state.delete_confirm = ""
            st.rerun()

    subj = st.session_state.cur_subj
    ensure_subj(subj)

    st.divider()

    # 학년도/학기
    st.markdown('<div class="section-title">🗓️ 학년도·학기</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    st.session_state.year = c1.selectbox("학년도", [2025,2026,2027], index=1, key="yr")
    st.session_state.cur_sem = c2.selectbox("학기", ["1학기","2학기"], key="sm")
    sem = st.session_state.cur_sem
    st.session_state.sem_start[sem] = st.date_input("학기 시작", value=st.session_state.sem_start[sem], format="YYYY-MM-DD", key="s1")
    st.session_state.sem_end[sem] = st.date_input("학기 종료", value=st.session_state.sem_end[sem], format="YYYY-MM-DD", key="s2")

    st.divider()

    # 시험 날짜
    st.markdown('<div class="section-title">📝 시험 날짜</div>', unsafe_allow_html=True)
    ex = st.session_state.exams.get(subj, {"mid_start":None,"mid_end":None,"fin_start":None,"fin_end":None})
    mc1, mc2 = st.columns(2)
    ex["mid_start"] = mc1.date_input("중간 시작", value=ex.get("mid_start"), format="YYYY-MM-DD", key="ms")
    ex["mid_end"] = mc2.date_input("중간 종료", value=ex.get("mid_end"), format="YYYY-MM-DD", key="me")
    fc1, fc2 = st.columns(2)
    ex["fin_start"] = fc1.date_input("기말 시작", value=ex.get("fin_start"), format="YYYY-MM-DD", key="fs")
    ex["fin_end"] = fc2.date_input("기말 종료", value=ex.get("fin_end"), format="YYYY-MM-DD", key="fe")
    st.session_state.exams[subj] = ex

    st.divider()

    # 반 구성
    st.markdown('<div class="section-title">🏫 반 구성</div>', unsafe_allow_html=True)
    checks = st.session_state.class_checks.get(subj, [False]*8)
    cols4 = st.columns(4)
    new_checks = []
    for i in range(8):
        with cols4[i % 4]:
            new_checks.append(st.checkbox(f"{i+1}반", value=checks[i] if i<len(checks) else False, key=f"cl_{i}"))
    st.session_state.class_checks[subj] = new_checks


# ── 메인 ────────────────────────────────────────────────
subj = st.session_state.cur_subj
sem = st.session_state.cur_sem
classes = get_classes(subj)
sem_start = st.session_state.sem_start[sem]
sem_end = st.session_state.sem_end[sem]

st.markdown(f'<div class="main-title">📚 {subj} — {st.session_state.year}학년도 {sem}</div>', unsafe_allow_html=True)

tab1, tab2, tab3, tab4 = st.tabs(["📊 진도 현황", "⏰ 시간표 입력", "📅 학사일정 입력", "✏️ 진도 수정"])


# ══════════════════════════════════════════════════════════
# TAB 1: 진도 현황
# ══════════════════════════════════════════════════════════
with tab1:
    if not classes:
        st.warning("사이드바에서 반을 먼저 선택해주세요.")
        st.stop()

    today = date.today()
    ex = st.session_state.exams.get(subj, {})

    # 시기 자동 선택
    mid_end_d = ex.get("mid_end")
    default_view = "기말고사"
    if mid_end_d and isinstance(mid_end_d, date) and today <= mid_end_d:
        default_view = "중간고사"

    top_c1, top_c2 = st.columns([1, 5])
    with top_c1:
        st.markdown("""<button onclick="window.print()" style="
            padding:6px 16px; background:#1e3a5f; color:#fff; border:none;
            border-radius:6px; cursor:pointer; font-size:0.85rem;">🖨️ 인쇄</button>""",
            unsafe_allow_html=True)
    with top_c2:
        view_mode = st.radio("보기", ["중간고사","기말고사"],
            index=["중간고사","기말고사"].index(default_view),
            horizontal=True, label_visibility="collapsed")

    # 기간 계산
    exam_key = "mid" if view_mode == "중간고사" else "fin"
    period_start, period_end = get_period_dates(subj, exam_key)

    progress, total_hours = compute_progress(subj, period_start, period_end, classes)
    first_map = get_first_class_per_lesson(progress, classes)

    all_dates = get_dates(period_start, period_end)
    school_dates = [d for d in all_dates if d.weekday() < 5]
    start_d = all_dates[0] if all_dates else sem_start

    if not school_dates:
        st.info("해당 기간에 수업일이 없습니다.")
        st.stop()

    # 시수 요약 표
    st.markdown('<div class="section-title">📊 반별 수업 시수</div>', unsafe_allow_html=True)
    hrs_th = "".join(f"<th>{c}</th>" for c in classes)
    hrs_td = "".join(f"<td>{total_hours.get(c,0)}시간</td>" for c in classes)
    st.markdown(f"""<table class="hours-table"><thead><tr>{hrs_th}</tr></thead>
        <tbody><tr>{hrs_td}</tr></tbody></table>""", unsafe_allow_html=True)

    # ── 좌우 배치 ──
    left_col, right_col = st.columns([3, 2])

    # ── 왼쪽: 날짜별 진도 현황 ──
    with left_col:
        st.markdown('<div class="section-title">📋 날짜별 진도 현황</div>', unsafe_allow_html=True)

        cls_ths = "".join(f'<th class="col-cls">{c}</th>' for c in classes)
        html = f"""<div style="overflow-x:auto; max-height:600px; overflow-y:auto;">
        <table class="view-table">
        <thead><tr>
            <th class="col-wk">주</th><th class="col-date">날짜</th>
            <th class="col-day">요일</th><th class="col-oc">구분</th>
            {cls_ths}<th class="col-note">비고</th>
        </tr></thead><tbody>"""

        prev_wk = None
        for d in school_dates:
            dk = d.isoformat()
            hol = holidays.get(dk, "")
            exam = is_exam_day(subj, d)
            stype = get_schedule_type(subj, d)
            note = get_note(subj, d)
            eff_day = get_effective_day(subj, d)
            actual_day = WEEKDAYS[d.weekday()]
            wk = get_weeknum(d, start_d)
            is_td = (d == today)
            is_past = (d < today)
            day_prog = progress.get(dk, {})

            if wk != prev_wk:
                html += f'<tr class="wk-sep"><td colspan="{4+len(classes)+1}">{wk}주차</td></tr>'
                prev_wk = wk

            date_cls = "d-today" if is_td else ("d-past" if is_past else "")
            day_display = actual_day if eff_day == actual_day else f"{actual_day}→{eff_day}"
            wk_cell = str(wk) if d.weekday() == 0 else ""

            badge = ""
            if stype == "원": badge = '<span class="b-orig">원</span>'
            elif stype == "교": badge = '<span class="b-cross">교</span>'

            # 반별 셀 — 숫자만, 색상으로 구분
            cells = ""
            for cls in classes:
                if hol:
                    cells += f'<td class="c-hol"></td>'
                elif exam:
                    cells += f'<td class="c-exam"></td>'
                elif stype == "결강":
                    cells += f'<td class="c-cancel"></td>'
                elif cls in day_prog:
                    info = day_prog[cls]
                    ln = info.get("차시","")
                    ctype = info.get("type","")
                    edited = info.get("edited", False)

                    # 셀 색상
                    if edited: cell_cls = "c-edit"
                    elif ctype == "fixed": cell_cls = "c-fixed"
                    elif ctype == "orig": cell_cls = "c-orig"
                    elif ctype == "cross": cell_cls = "c-cross"
                    else: cell_cls = ""

                    # 첫 수업 반 강조
                    is_first = False
                    if isinstance(ln, int) and ln in first_map:
                        f_dk, f_cls = first_map[ln]
                        if f_dk == dk and f_cls == cls:
                            is_first = True

                    first_cls = " c-first" if is_first else ""
                    cells += f'<td class="{cell_cls}{first_cls}">{ln}</td>'
                else:
                    cells += '<td>-</td>'

            # 비고 — 결강 텍스트 제외, 공휴일/시험 이름만
            note_parts = []
            if hol: note_parts.append(hol)
            if exam: note_parts.append(exam)
            if note: note_parts.append(note)
            if eff_day != actual_day: note_parts.append(f"{eff_day}요일수업")
            note_text = ", ".join(note_parts)

            html += f"""<tr>
                <td>{wk_cell}</td>
                <td class="{date_cls}">{d.strftime("%-m/%d")}</td>
                <td class="{date_cls}">{day_display}</td>
                <td>{badge}</td>{cells}
                <td style="font-size:0.6rem;color:#78909c;text-align:left;">{note_text}</td>
            </tr>"""

        html += "</tbody></table></div>"
        st.markdown(html, unsafe_allow_html=True)

    # ── 오른쪽 ──
    with right_col:
        # 차시별 수업 날짜
        st.markdown('<div class="section-title">📅 차시별 수업 날짜</div>', unsafe_allow_html=True)

        lesson_dates = {}
        for dk, day_data in progress.items():
            for cls, info in day_data.items():
                ln = info.get("차시")
                if ln and isinstance(ln, int):
                    lesson_dates.setdefault(cls, {})[ln] = (dk, info.get("type",""))

        max_lesson = max(total_hours.values()) if total_hours and any(total_hours.values()) else 0
        contents = st.session_state.lesson_contents.get(subj, {}).get(exam_key, {})

        if max_lesson > 0:
            cls_ths2 = "".join(f'<th class="col-cls">{c}</th>' for c in classes)
            html2 = f"""<div style="overflow-x:auto; max-height:360px; overflow-y:auto;">
            <table class="view-table">
            <thead><tr><th style="width:28px;">차시</th>{cls_ths2}<th class="col-note">수업내용</th></tr></thead><tbody>"""

            for ln in range(1, max_lesson + 1):
                cells2 = ""
                for cls in classes:
                    data = lesson_dates.get(cls, {}).get(ln)
                    if data:
                        dk, ctype = data
                        try:
                            d_obj = date.fromisoformat(dk)
                            is_past = d_obj < today
                            is_td = d_obj == today
                            date_cls = "d-today" if is_td else ("d-past" if is_past else "")
                            type_cls = "c-fixed" if ctype=="fixed" else ("c-orig" if ctype=="orig" else ("c-cross" if ctype=="cross" else ""))

                            # 첫 수업 반 강조
                            is_first = (ln in first_map and first_map[ln] == (dk, cls))
                            first_cls = " c-first" if is_first and not is_past else ""
                            past_override = " d-past" if is_past else ""

                            cells2 += f'<td class="{type_cls}{first_cls}{past_override}">{d_obj.strftime("%-m/%d")}</td>'
                        except:
                            cells2 += f'<td>{dk}</td>'
                    else:
                        cells2 += '<td>-</td>'

                content = contents.get(str(ln), "")
                html2 += f'<tr><td>{ln}</td>{cells2}<td style="font-size:0.6rem;text-align:left;color:#546e7a;">{content}</td></tr>'

            html2 += "</tbody></table></div>"
            st.markdown(html2, unsafe_allow_html=True)
        else:
            st.info("시간표와 학사일정을 입력하면 자동 표시됩니다.")

        # 요일별/반별 수업 교시
        st.markdown('<div class="section-title">🕐 요일별/반별 수업 교시</div>', unsafe_allow_html=True)
        tt = st.session_state.timetable.get(subj, {})
        if tt:
            cls_ths3 = "".join(f'<th>{c}</th>' for c in classes)
            html3 = f"""<table class="view-table">
            <thead><tr><th></th><th>요일</th>{cls_ths3}</tr></thead><tbody>"""

            for label_name, match_key in [("원","orig"),("교","cross")]:
                badge_cls = "b-orig" if label_name == "원" else "b-cross"
                for day in WEEKDAYS:
                    cells3 = ""
                    for cls in classes:
                        periods = []
                        for p in range(1, 8):
                            if (day, p) in BLOCKED_CELLS: continue
                            parsed = parse_tt_cell(tt.get(f"{day}_{p}", ""))
                            if not parsed: continue
                            if "fixed" in parsed and parsed["fixed"] == cls:
                                periods.append(f"<span style='color:#e65100;font-weight:600;'>{p}교시</span>")
                            elif match_key in parsed and parsed[match_key] == cls:
                                color = "#2e7d32" if match_key == "orig" else "#1565c0"
                                periods.append(f"<span style='color:{color};'>{p}교시</span>")
                        cells3 += f'<td>{"<br>".join(periods) if periods else "-"}</td>'
                    show_label = f'<span class="{badge_cls}">{label_name}</span>' if day == "월" else ""
                    html3 += f'<tr><td>{show_label}</td><td>{day}</td>{cells3}</tr>'
                if label_name == "원":
                    html3 += f'<tr class="wk-sep"><td colspan="{2+len(classes)}"></td></tr>'
            html3 += "</tbody></table>"
            st.markdown(html3, unsafe_allow_html=True)
        else:
            st.info("시간표를 먼저 입력하세요.")


# ══════════════════════════════════════════════════════════
# TAB 2: 시간표 입력
# ══════════════════════════════════════════════════════════
with tab2:
    st.markdown('<div class="section-title">⏰ 시간표 입력</div>', unsafe_allow_html=True)
    st.markdown("""
    **입력 방법:** 고정 → 반번호 (예: `6`) · 교차 → 원,교차 (예: `8,4`) · 빈칸 → 수업 없음 · 🔒 = 창체
    """)

    if not classes:
        st.warning("사이드바에서 반을 먼저 선택해주세요.")
    else:
        tt = st.session_state.timetable.get(subj, {})

        hcols = st.columns([1.5]+[1]*5)
        hcols[0].markdown("**교시＼요일**")
        for i, day in enumerate(WEEKDAYS):
            hcols[i+1].markdown(f"**{day}**")

        new_tt = dict(tt)
        for period in range(1, 8):
            rcols = st.columns([1.5]+[1]*5)
            rcols[0].markdown(f"**{period}교시**")
            for i, day in enumerate(WEEKDAYS):
                key = f"{day}_{period}"
                if (day, period) in BLOCKED_CELLS:
                    rcols[i+1].markdown("🔒 창체")
                    new_tt[key] = "창체"
                else:
                    cur = tt.get(key, "")
                    val = rcols[i+1].text_input(f"{day}{period}", value=cur,
                        label_visibility="collapsed", key=f"tt_{day}_{period}", placeholder="수업반")
                    if val.strip():
                        new_tt[key] = val.strip()
                    elif key in new_tt and new_tt.get(key) != "창체":
                        new_tt.pop(key, None)

        if st.button("시간표 저장", type="primary"):
            st.session_state.timetable[subj] = new_tt
            st.success("저장 완료!")
            st.rerun()

        # 미리보기 (색상 적용)
        st.markdown('<div class="section-title">미리보기</div>', unsafe_allow_html=True)
        prev_html = """<table class="tt-preview"><thead><tr><th>교시＼요일</th>"""
        for day in WEEKDAYS:
            prev_html += f"<th>{day}</th>"
        prev_html += "</tr></thead><tbody>"
        for period in range(1, 8):
            prev_html += f"<tr><td><b>{period}교시</b></td>"
            for day in WEEKDAYS:
                key = f"{day}_{period}"
                if (day, period) in BLOCKED_CELLS:
                    prev_html += '<td class="tt-blocked">창체</td>'
                else:
                    val = new_tt.get(key, "")
                    parsed = parse_tt_cell(val)
                    if not parsed:
                        prev_html += '<td class="tt-empty">-</td>'
                    elif "fixed" in parsed:
                        prev_html += f'<td class="tt-fixed">{val}</td>'
                    elif "orig" in parsed:
                        prev_html += f'<td class="tt-cross">{val}</td>'
                    else:
                        prev_html += f'<td>{val}</td>'
            prev_html += "</tr>"
        prev_html += "</tbody></table>"
        st.markdown(prev_html, unsafe_allow_html=True)

        # CSV 업로드
        st.divider()
        st.caption("CSV 업로드 (선택): 형식 `요일,교시,수업반`")
        upload = st.file_uploader("CSV", type=["csv"], key="ttu")
        if upload:
            try:
                df = pd.read_csv(upload)
                new_tt2 = {}
                for _, row in df.iterrows():
                    day, per, val = str(row["요일"]).strip(), int(row["교시"]), str(row["수업반"]).strip()
                    if (day, per) not in BLOCKED_CELLS:
                        new_tt2[f"{day}_{per}"] = val
                for d2, p2 in BLOCKED_CELLS:
                    new_tt2[f"{d2}_{p2}"] = "창체"
                st.session_state.timetable[subj] = new_tt2
                st.success("업로드 완료!")
                st.rerun()
            except Exception as e:
                st.error(f"형식 오류: {e}")


# ══════════════════════════════════════════════════════════
# TAB 3: 학사일정 입력
# ══════════════════════════════════════════════════════════
with tab3:
    st.markdown('<div class="section-title">📅 학사일정 입력</div>', unsafe_allow_html=True)
    st.caption("🟩 원시간표  🟦 교차시간표  ⬜ 결강  🔴 공휴일  🟣 시험")

    all_dates = get_dates(sem_start, sem_end)
    if not all_dates:
        st.error("학기 날짜를 확인해주세요.")
        st.stop()

    sch = st.session_state.schedule.get(subj, {})

    # 요일 헤더
    hd_cols = st.columns(5)
    for i, day in enumerate(WEEKDAYS):
        hd_cols[i].markdown(f"**{day}**")
    st.markdown("---")

    # 연속 배치: 월~금 순서대로 채우기
    school_dates = [d for d in all_dates if d.weekday() < 5]

    # 주 단위로 묶기 (ISO week)
    weeks = {}
    for d in school_dates:
        wk_key = (d.isocalendar()[0], d.isocalendar()[1])
        weeks.setdefault(wk_key, {})[d.weekday()] = d

    for wk_key in sorted(weeks.keys()):
        wk_dates = weeks[wk_key]
        cols = st.columns(5)
        for wd in range(5):
            with cols[wd]:
                if wd in wk_dates:
                    d = wk_dates[wd]
                    dk = d.isoformat()
                    hol = holidays.get(dk, "")
                    exam = is_exam_day(subj, d)
                    cur_sch = sch.get(dk, {})
                    if not isinstance(cur_sch, dict):
                        cur_sch = {}
                    actual_day = WEEKDAYS[d.weekday()]

                    label = f"**{d.month}/{d.day}({actual_day})**"

                    if hol:
                        st.markdown(f"🔴 {label}")
                        st.caption(hol)
                    elif exam:
                        st.markdown(f"🟣 {label}")
                        st.caption(exam)
                    else:
                        st.markdown(label)

                        # 원/교/결강 버튼
                        cur_type = cur_sch.get("type", "")
                        if not cur_type:
                            cur_type = "원"  # 초기값 원시간표

                        # 고정 레이아웃: 원/교 같은 줄, 결강 아래
                        btn_html = '<div style="display:flex; gap:3px; margin-bottom:2px;">'
                        for t, lbl, c_active, c_inactive in [
                            ("원","원","btn-orig-active","btn-orig"),
                            ("교","교","btn-cross-active","btn-cross"),
                        ]:
                            cls_name = c_active if cur_type == t else c_inactive
                            btn_html += f'<span class="sch-btn {cls_name}">{lbl}</span>'
                        btn_html += '</div>'
                        cancel_cls = "btn-cancel-active" if cur_type == "결강" else "btn-cancel"
                        btn_html += f'<span class="sch-btn {cancel_cls}" style="display:block;width:fit-content;">결강</span>'
                        st.markdown(btn_html, unsafe_allow_html=True)

                        # 실제 선택 (라디오 숨김 대체)
                        type_opts = ["원","교","결강"]
                        t_idx = type_opts.index(cur_type) if cur_type in type_opts else 0
                        sel_type = st.radio("t", type_opts, index=t_idx,
                            key=f"st_{dk}", label_visibility="collapsed")

                        # 요일변경
                        day_opts = [actual_day] + [x for x in WEEKDAYS if x != actual_day]
                        cur_ov = cur_sch.get("day_override", "")
                        ov_idx = day_opts.index(cur_ov) if cur_ov in day_opts else 0
                        sel_day = st.selectbox("요일변경", day_opts, index=ov_idx,
                            key=f"do_{dk}")

                        # 비고
                        cur_note = cur_sch.get("note", "")
                        sel_note = st.text_input("비고", value=cur_note,
                            key=f"nt_{dk}", label_visibility="collapsed", placeholder="비고")

                        sch[dk] = {
                            "type": sel_type,
                            "day_override": sel_day if sel_day != actual_day else "",
                            "note": sel_note,
                        }
                else:
                    st.markdown("&nbsp;")

    st.session_state.schedule[subj] = sch


# ══════════════════════════════════════════════════════════
# TAB 4: 진도 수정
# ══════════════════════════════════════════════════════════
with tab4:
    if not classes:
        st.warning("사이드바에서 반을 먼저 선택해주세요.")
        st.stop()

    ex = st.session_state.exams.get(subj, {})
    mid_end_d = ex.get("mid_end")
    default_edit = "기말고사"
    if mid_end_d and isinstance(mid_end_d, date) and today <= mid_end_d:
        default_edit = "중간고사"

    edit_mode = st.radio("시기", ["중간고사","기말고사"],
        index=["중간고사","기말고사"].index(default_edit),
        horizontal=True, key="edit_mode")

    exam_key = "mid" if edit_mode == "중간고사" else "fin"
    period_start, period_end = get_period_dates(subj, exam_key)
    progress, total_hours = compute_progress(subj, period_start, period_end, classes)
    first_map = get_first_class_per_lesson(progress, classes)
    all_dates = get_dates(period_start, period_end)
    school_dates = [d for d in all_dates if d.weekday() < 5]
    start_d = all_dates[0] if all_dates else sem_start
    today = date.today()

    # 저장 버튼 (상단)
    save_btn = st.button("💾 수정 저장", type="primary", key="save_edit")

    st.markdown('<div class="section-title">📋 날짜별 진도 수정 (좌) · 미리보기 (우)</div>', unsafe_allow_html=True)

    # ── 날짜별 진도 DataFrame ──
    rows = []
    for d in school_dates:
        dk = d.isoformat()
        hol = holidays.get(dk, "")
        exam = is_exam_day(subj, d)
        stype = get_schedule_type(subj, d)
        note = get_note(subj, d)
        eff_day = get_effective_day(subj, d)
        actual_day = WEEKDAYS[d.weekday()]
        day_prog = progress.get(dk, {})

        row = {
            "날짜": d.strftime("%-m/%d"),
            "요일": actual_day if eff_day == actual_day else f"{actual_day}→{eff_day}",
        }
        for cls in classes:
            if hol: row[cls] = ""
            elif exam: row[cls] = ""
            elif stype == "결강": row[cls] = ""
            elif cls in day_prog:
                v = day_prog[cls].get("차시","")
                row[cls] = str(v) if v else ""
            else: row[cls] = ""
        row["비고"] = note
        row["_date"] = dk
        rows.append(row)

    df = pd.DataFrame(rows)

    edit_left, edit_right = st.columns([1, 1])

    with edit_left:
        col_config = {
            "날짜": st.column_config.TextColumn("날짜", disabled=True, width="small"),
            "요일": st.column_config.TextColumn("요일", disabled=True, width="small"),
            "비고": st.column_config.TextColumn("비고", width="medium"),
            "_date": None,
        }
        for cls in classes:
            col_config[cls] = st.column_config.TextColumn(cls, width="small")

        edited_df = st.data_editor(df, use_container_width=True, height=480,
            column_config=col_config, key="pe", hide_index=True)

    # ── 미리보기 (예쁜 표) ──
    with edit_right:
        cls_ths = "".join(f'<th class="col-cls">{c}</th>' for c in classes)
        phtml = f"""<div style="overflow-x:auto; max-height:480px; overflow-y:auto;">
        <table class="view-table">
        <thead><tr><th class="col-date">날짜</th><th class="col-day">요일</th>{cls_ths}<th class="col-note">비고</th></tr></thead><tbody>"""

        for d in school_dates:
            dk = d.isoformat()
            hol = holidays.get(dk, "")
            exam = is_exam_day(subj, d)
            stype = get_schedule_type(subj, d)
            note = get_note(subj, d)
            eff_day = get_effective_day(subj, d)
            actual_day = WEEKDAYS[d.weekday()]
            is_td = (d == today)
            is_past = (d < today)
            day_prog = progress.get(dk, {})
            date_cls = "d-today" if is_td else ("d-past" if is_past else "")
            day_display = actual_day if eff_day == actual_day else f"{actual_day}→{eff_day}"

            cells = ""
            for cls in classes:
                if hol: cells += '<td class="c-hol"></td>'
                elif exam: cells += '<td class="c-exam"></td>'
                elif stype == "결강": cells += '<td class="c-cancel"></td>'
                elif cls in day_prog:
                    info = day_prog[cls]
                    ln = info.get("차시","")
                    ctype = info.get("type","")
                    edited = info.get("edited",False)
                    cell_cls = "c-edit" if edited else (f"c-{ctype}" if ctype else "")
                    is_first = isinstance(ln,int) and ln in first_map and first_map[ln]==(dk,cls)
                    first_cls = " c-first" if is_first else ""
                    cells += f'<td class="{cell_cls}{first_cls}">{ln}</td>'
                else: cells += '<td>-</td>'

            note_parts = []
            if hol: note_parts.append(hol)
            if exam: note_parts.append(exam)
            if note: note_parts.append(note)
            note_text = ", ".join(note_parts)

            phtml += f'<tr><td class="{date_cls}">{d.strftime("%-m/%d")}</td><td class="{date_cls}">{day_display}</td>{cells}<td style="font-size:0.6rem;color:#78909c;text-align:left;">{note_text}</td></tr>'

        phtml += "</tbody></table></div>"
        st.markdown(phtml, unsafe_allow_html=True)

    # 저장 처리
    if save_btn:
        overrides = st.session_state.overrides.get(subj, {})
        for idx, row in edited_df.iterrows():
            dk = row["_date"]
            if idx >= len(df): continue
            orig_row = df.iloc[idx]
            for cls in classes:
                new_val = str(row[cls]).strip() if pd.notna(row[cls]) else ""
                orig_val = str(orig_row[cls]).strip() if pd.notna(orig_row[cls]) else ""
                if new_val != orig_val:
                    overrides.setdefault(dk, {})[cls] = new_val

            new_note = str(row["비고"]).strip() if pd.notna(row["비고"]) else ""
            orig_note = str(orig_row["비고"]).strip() if pd.notna(orig_row["비고"]) else ""
            if new_note != orig_note:
                sch_entry = st.session_state.schedule.get(subj, {}).get(dk, {})
                if not isinstance(sch_entry, dict): sch_entry = {}
                sch_entry["note"] = new_note
                st.session_state.schedule.setdefault(subj, {})[dk] = sch_entry

        st.session_state.overrides[subj] = overrides
        st.success("저장 완료!")
        st.rerun()

    # ── 차시별 수업 날짜 + 수업내용 (data_editor) ──
    st.divider()
    st.markdown('<div class="section-title">📅 차시별 수업 날짜 · 수업내용</div>', unsafe_allow_html=True)

    lesson_dates = {}
    for dk, day_data in progress.items():
        for cls, info in day_data.items():
            ln = info.get("차시")
            if ln and isinstance(ln, int):
                lesson_dates.setdefault(cls, {})[ln] = dk

    max_lesson = max(total_hours.values()) if total_hours and any(total_hours.values()) else 0
    contents = st.session_state.lesson_contents.get(subj, {}).get(exam_key, {})

    if max_lesson > 0:
        lesson_rows = []
        for ln in range(1, max_lesson + 1):
            row = {"차시": ln}
            for cls in classes:
                dk = lesson_dates.get(cls, {}).get(ln, "")
                if dk:
                    try:
                        d_obj = date.fromisoformat(dk)
                        row[cls] = d_obj.strftime("%-m/%d")
                    except:
                        row[cls] = dk
                else:
                    row[cls] = "-"
            row["수업내용"] = contents.get(str(ln), "")
            lesson_rows.append(row)

        lesson_df = pd.DataFrame(lesson_rows)
        lesson_col_config = {
            "차시": st.column_config.NumberColumn("차시", disabled=True, width="small"),
            "수업내용": st.column_config.TextColumn("수업내용", width="large"),
        }
        for cls in classes:
            lesson_col_config[cls] = st.column_config.TextColumn(cls, disabled=True, width="small")

        edited_lessons = st.data_editor(lesson_df, use_container_width=True, hide_index=True,
            column_config=lesson_col_config, key="le")

        if st.button("수업내용 저장", type="primary", key="save_lc"):
            new_contents = {}
            for _, row in edited_lessons.iterrows():
                c = str(row["수업내용"]).strip() if pd.notna(row["수업내용"]) else ""
                if c:
                    new_contents[str(int(row["차시"]))] = c
            lc = st.session_state.lesson_contents.get(subj, {"mid":{},"fin":{}})
            lc[exam_key] = new_contents
            st.session_state.lesson_contents[subj] = lc
            st.success("수업내용 저장 완료!")
            st.rerun()
    else:
        st.info("시간표와 학사일정을 입력하면 차시가 자동 생성됩니다.")
