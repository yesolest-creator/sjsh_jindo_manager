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

/* ── 진도 현황 테이블 (보기용) ── */
.view-table { width:100%; border-collapse:collapse; font-size:0.72rem; }
.view-table th {
    background:#1e3a5f; color:#fff; padding:3px 4px; text-align:center;
    border:1px solid #152d4a; font-size:0.7rem; font-weight:500;
}
.view-table td {
    padding:2px 3px; text-align:center; border:1px solid #cbd5e1;
    min-width:28px; font-size:0.7rem; line-height:1.2;
}
.view-table tr:hover td { background:#f0f7ff; }

/* 셀 색상 — 파스텔톤 */
.c-fixed { background:#fff3e0 !important; color:#e65100; }      /* 고정: 연주황 */
.c-orig  { background:#e8f5e9 !important; color:#2e7d32; }      /* 원: 연초록 */
.c-cross { background:#e3f2fd !important; color:#1565c0; }      /* 교차: 연파랑 */
.c-edit  { background:#fff !important; border:2px dashed #9e9e9e !important; }  /* 수정: 테두리 */
.c-cancel{ background:#f5f5f5 !important; color:#9e9e9e; }      /* 결강: 연회색 */
.c-hol   { background:#ffebee !important; color:#c62828; }      /* 공휴일: 연빨강 */
.c-exam  { background:#f3e5f5 !important; color:#6a1b9a; }      /* 시험: 연보라 */

/* 날짜 관련 (인쇄 미적용) */
.d-past  { color:#bdbdbd !important; }
.d-today { background:#ffeb3b !important; color:#000 !important; font-weight:700; }

/* 원/교 뱃지 */
.b-orig  { background:#c8e6c9; color:#2e7d32; padding:1px 5px; border-radius:6px; font-size:0.65rem; font-weight:600; }
.b-cross { background:#bbdefb; color:#1565c0; padding:1px 5px; border-radius:6px; font-size:0.65rem; font-weight:600; }
.b-fixed { background:#ffe0b2; color:#e65100; padding:1px 5px; border-radius:6px; font-size:0.65rem; font-weight:600; }

/* 주차 구분 */
.wk-sep td { background:#eceff1 !important; font-weight:600; color:#455a64; font-size:0.68rem; padding:2px; }

/* ── 인쇄 스타일 ── */
@media print {
    .stSidebar, .stButton, .stTabs, [data-testid="stToolbar"],
    [data-testid="stHeader"], .no-print { display:none !important; }
    .main { margin:0 !important; padding:0 !important; }
    @page { size:A4 landscape; margin:8mm; }
    .view-table { font-size:0.62rem; }
    .view-table th { background:#333 !important; -webkit-print-color-adjust:exact; print-color-adjust:exact; }
    .view-table td { padding:1px 2px; }
    /* 인쇄시 날짜 색상 미적용 */
    .d-past { color:inherit !important; }
    .d-today { background:transparent !important; color:inherit !important; font-weight:normal; }
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

# ── 상수 ────────────────────────────────────────────────
WEEKDAYS = ["월","화","수","목","금"]
BLOCKED_CELLS = {("수",6), ("수",7)}  # 창체 고정

# ── 세션 초기화 ─────────────────────────────────────────
def init():
    d = {
        "subjects": ["고급지구과학"],
        "cur_subj": "고급지구과학",
        "year": 2026,
        "class_checks": {"고급지구과학": [True]*8},
        # 통합 시간표: {과목: {"요일_교시": "값"}}
        # 값 형식: "6" (고정), "8,4" (원=8반, 교차=4반), "창체" (블록)
        "timetable": {"고급지구과학": {}},
        # 학사일정: {과목: {날짜str: {"type":"원"/"교"/"결강"/"", "day_override":"", "note":""}}}
        "schedule": {"고급지구과학": {}},
        # 시험: {과목: {"mid_start":"","mid_end":"","fin_start":"","fin_end":""}}
        "exams": {"고급지구과학": {"mid_start":"","mid_end":"","fin_start":"","fin_end":""}},
        # 학기
        "sem_start": {"1학기":"2026-03-02","2학기":"2026-09-01"},
        "sem_end": {"1학기":"2026-07-17","2학기":"2026-12-31"},
        "cur_sem": "1학기",
        # 진도 수정 (오버라이드): {과목: {날짜str: {반str: 차시int or ""}}}
        "overrides": {"고급지구과학": {}},
        # 차시 메모: {과목: {차시int: 메모str}}
        "lesson_notes": {"고급지구과학": {}},
    }
    for k, v in d.items():
        if k not in st.session_state:
            st.session_state[k] = v
init()

def ensure_subj(s):
    for key, default in [
        ("class_checks",[False]*8),("timetable",{}),("schedule",{}),
        ("exams",{"mid_start":"","mid_end":"","fin_start":"","fin_end":""}),
        ("overrides",{}),("lesson_notes",{})
    ]:
        if s not in st.session_state[key]:
            st.session_state[key][s] = copy.deepcopy(default)

def get_classes(subj):
    checks = st.session_state.class_checks.get(subj, [False]*8)
    return [f"{i+1}반" for i in range(8) if i < len(checks) and checks[i]]

def get_dates(sem):
    s = date.fromisoformat(st.session_state.sem_start[sem])
    e = date.fromisoformat(st.session_state.sem_end[sem])
    out = []
    c = s
    while c <= e:
        out.append(c)
        c += timedelta(days=1)
    return out

# ── 시간표 파싱 ─────────────────────────────────────────
def parse_tt_cell(val):
    """
    시간표 셀 값 파싱.
    "6" → {"fixed":"6반"}
    "8,4" → {"orig":"8반","cross":"4반"}
    "창체" → {"blocked":"창체"}
    "" → None
    """
    val = str(val).strip()
    if not val or val == "nan":
        return None
    if not val.replace(",","").replace(" ","").isdigit():
        return {"blocked": val}
    parts = [p.strip() for p in val.split(",") if p.strip()]
    if len(parts) == 1:
        return {"fixed": f"{parts[0]}반"}
    elif len(parts) == 2:
        return {"orig": f"{parts[0]}반", "cross": f"{parts[1]}반"}
    return None

def get_effective_day(subj, d):
    """해당 날짜의 실제 수업 요일 (요일변경 반영)"""
    sch = st.session_state.schedule.get(subj, {}).get(d.isoformat(), {})
    override_day = sch.get("day_override", "")
    if override_day and override_day in WEEKDAYS:
        return override_day
    return WEEKDAYS[d.weekday()] if d.weekday() < 5 else ""

def get_schedule_type(subj, d):
    """해당 날짜의 일정 유형"""
    dk = d.isoformat()
    sch = st.session_state.schedule.get(subj, {}).get(dk, {})
    return sch.get("type", "")

def get_note(subj, d):
    dk = d.isoformat()
    sch = st.session_state.schedule.get(subj, {}).get(dk, {})
    return sch.get("note", "")

def is_exam_day(subj, d):
    ex = st.session_state.exams.get(subj, {})
    dk = d.isoformat()
    for prefix, label in [("mid","중간고사"),("fin","기말고사")]:
        s = ex.get(f"{prefix}_start","")
        e = ex.get(f"{prefix}_end","")
        if s and e:
            try:
                if date.fromisoformat(s) <= d <= date.fromisoformat(e):
                    return label
            except: pass
    return ""

def get_classes_for_date(subj, d):
    """
    해당 날짜에 수업 있는 반 목록과 유형 반환.
    Returns: [(반str, 유형str)] 유형: "fixed"/"orig"/"cross"
    """
    holidays = get_holidays(st.session_state.year)
    if d.weekday() >= 5 or d.isoformat() in holidays:
        return []
    if is_exam_day(subj, d):
        return []
    stype = get_schedule_type(subj, d)
    if stype == "결강":
        return []

    eff_day = get_effective_day(subj, d)
    if not eff_day:
        return []

    tt = st.session_state.timetable.get(subj, {})
    results = []

    for period in range(1, 8):
        if (eff_day, period) in BLOCKED_CELLS:
            continue
        key = f"{eff_day}_{period}"
        val = tt.get(key, "")
        parsed = parse_tt_cell(val)
        if not parsed or "blocked" in parsed:
            continue
        if "fixed" in parsed:
            results.append((parsed["fixed"], "fixed"))
        elif "orig" in parsed and "cross" in parsed:
            if stype == "교":
                results.append((parsed["cross"], "cross"))
            else:
                results.append((parsed["orig"], "orig"))
    return results

holidays = get_holidays(st.session_state.year)

# ── 진도 자동 계산 ──────────────────────────────────────
def compute_progress(subj, sem, classes):
    """
    반별로 수업 날짜 순서대로 차시 자동 배정.
    오버라이드가 있으면 그 값을 우선.
    Returns: {날짜str: {반str: {"차시":int,"type":str,"edited":bool}}}
    """
    try:
        all_dates = get_dates(sem)
    except:
        return {}

    school_dates = [d for d in all_dates if d.weekday() < 5]
    overrides = st.session_state.overrides.get(subj, {})

    # 반별 차시 카운터
    class_counter = {cls: 1 for cls in classes}
    progress = {}

    for d in school_dates:
        dk = d.isoformat()
        hol = holidays.get(dk, "")
        exam = is_exam_day(subj, d)
        stype = get_schedule_type(subj, d)

        progress[dk] = {}

        if hol or exam or stype == "결강":
            continue

        cls_list = get_classes_for_date(subj, d)

        for cls, ctype in cls_list:
            if cls not in classes:
                continue
            # 오버라이드 확인
            ov = overrides.get(dk, {}).get(cls, None)
            if ov is not None and ov != "":
                try:
                    lesson = int(ov)
                    progress[dk][cls] = {"차시": lesson, "type": ctype, "edited": True}
                except:
                    progress[dk][cls] = {"차시": "", "type": ctype, "edited": True}
            else:
                lesson = class_counter[cls]
                progress[dk][cls] = {"차시": lesson, "type": ctype, "edited": False}
                class_counter[cls] += 1

    return progress

# ── 사이드바 ────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="main-title">📚 수업 진도 관리</div>', unsafe_allow_html=True)
    st.caption("교차시간표 지원 · 자동 시수 계산")
    st.divider()

    # 과목
    st.markdown('<div class="section-title">📖 과목</div>', unsafe_allow_html=True)
    sc1, sc2 = st.columns([3,1])
    new_s = sc1.text_input("과목추가", placeholder="새 과목명", label_visibility="collapsed")
    if sc2.button("추가", key="as") and new_s.strip():
        if new_s.strip() not in st.session_state.subjects:
            st.session_state.subjects.append(new_s.strip())
            ensure_subj(new_s.strip())
            st.rerun()

    subj = st.selectbox("과목 선택", st.session_state.subjects, key="ss")
    st.session_state.cur_subj = subj
    ensure_subj(subj)

    if len(st.session_state.subjects) > 1:
        if st.button(f"'{subj}' 삭제"):
            st.session_state.subjects.remove(subj)
            st.session_state.cur_subj = st.session_state.subjects[0]
            st.rerun()

    st.divider()

    # 학년도 / 학기
    st.markdown('<div class="section-title">🗓️ 학년도·학기</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    st.session_state.year = c1.selectbox("학년도", [2025,2026,2027], index=1, key="yr")
    st.session_state.cur_sem = c2.selectbox("학기", ["1학기","2학기"], key="sm")
    sem = st.session_state.cur_sem
    st.session_state.sem_start[sem] = st.text_input("학기 시작", st.session_state.sem_start[sem], key="s1")
    st.session_state.sem_end[sem] = st.text_input("학기 종료", st.session_state.sem_end[sem], key="s2")

    st.divider()

    # 시험 날짜
    st.markdown('<div class="section-title">📝 시험 날짜</div>', unsafe_allow_html=True)
    ex = st.session_state.exams.get(subj, {"mid_start":"","mid_end":"","fin_start":"","fin_end":""})
    ex["mid_start"] = st.text_input("중간 시작", ex.get("mid_start",""), key="ms", placeholder="2026-04-23")
    ex["mid_end"]   = st.text_input("중간 종료", ex.get("mid_end",""), key="me", placeholder="2026-04-24")
    ex["fin_start"] = st.text_input("기말 시작", ex.get("fin_start",""), key="fs", placeholder="2026-07-01")
    ex["fin_end"]   = st.text_input("기말 종료", ex.get("fin_end",""), key="fe", placeholder="2026-07-02")
    st.session_state.exams[subj] = ex

    st.divider()

    # 반 구성
    st.markdown('<div class="section-title">🏫 반 구성</div>', unsafe_allow_html=True)
    checks = st.session_state.class_checks.get(subj, [False]*8)
    cols4 = st.columns(4)
    new_checks = []
    for i in range(8):
        with cols4[i % 4]:
            v = st.checkbox(f"{i+1}반", value=checks[i] if i < len(checks) else False, key=f"cl_{i}")
            new_checks.append(v)
    st.session_state.class_checks[subj] = new_checks

# ── 메인 ────────────────────────────────────────────────
subj = st.session_state.cur_subj
sem = st.session_state.cur_sem
classes = get_classes(subj)

st.markdown(f'<div class="main-title">📚 {subj} — {st.session_state.year}학년도 {sem}</div>', unsafe_allow_html=True)

tab1, tab2, tab3, tab4 = st.tabs(["📊 진도 현황", "⏰ 시간표 입력", "📅 학사일정 입력", "✏️ 진도 수정"])

# ══════════════════════════════════════════════════════════
# TAB 1: 진도 현황 (보기 전용 + 인쇄)
# ══════════════════════════════════════════════════════════
with tab1:
    if not classes:
        st.warning("사이드바에서 반을 먼저 선택해주세요.")
        st.stop()

    try:
        all_dates = get_dates(sem)
    except:
        st.error("학기 날짜를 확인해주세요.")
        st.stop()

    today = date.today()
    start_d = all_dates[0]
    progress = compute_progress(subj, sem, classes)
    ex = st.session_state.exams.get(subj, {})

    # 시기 자동 선택
    default_view = "전체"
    try:
        mid_end = date.fromisoformat(ex.get("mid_end",""))
        fin_start = date.fromisoformat(ex.get("fin_start",""))
        if today <= mid_end:
            default_view = "중간고사"
        elif today < fin_start:
            default_view = "기말고사"
    except:
        pass

    top_c1, top_c2 = st.columns([1, 5])
    with top_c1:
        if st.button("🖨️ 인쇄", use_container_width=True):
            st.markdown("<script>window.print();</script>", unsafe_allow_html=True)
    with top_c2:
        view_options = ["중간고사","기말고사","전체"]
        view_mode = st.radio("보기", view_options,
            index=view_options.index(default_view), horizontal=True, label_visibility="collapsed")

    # 날짜 필터
    school_dates = [d for d in all_dates if d.weekday() < 5]
    try:
        if view_mode == "중간고사" and ex.get("mid_end"):
            cutoff = date.fromisoformat(ex["mid_end"])
            school_dates = [d for d in school_dates if d <= cutoff]
        elif view_mode == "기말고사" and ex.get("mid_end") and ex.get("fin_end"):
            mid_e = date.fromisoformat(ex["mid_end"])
            fin_e = date.fromisoformat(ex["fin_end"])
            school_dates = [d for d in school_dates if d > mid_e and d <= fin_e]
    except:
        pass

    # ── 좌우 배치 ──
    left_col, right_col = st.columns([3, 2])

    # ── 왼쪽: 날짜별 진도 현황 ──
    with left_col:
        st.markdown('<div class="section-title">📋 날짜별 진도 현황</div>', unsafe_allow_html=True)

        # 반별 총 시수 계산
        total_hours = {cls: 0 for cls in classes}
        for dk, day_data in progress.items():
            for cls, info in day_data.items():
                if info.get("차시") and cls in total_hours:
                    total_hours[cls] += 1

        # 시수 요약
        summary = " | ".join([f"**{cls}**: {total_hours[cls]}시간" for cls in classes])
        st.caption(f"반별 총 시수: {summary}")

        cls_th = "".join(f"<th>{c}</th>" for c in classes)
        html = f"""<div style="overflow-x:auto; max-height:620px; overflow-y:auto;">
        <table class="view-table">
        <thead><tr><th>주</th><th>날짜</th><th>요일</th><th>원/교</th>{cls_th}<th>비고</th></tr></thead>
        <tbody>"""

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

            # 주차 구분
            if wk != prev_wk:
                html += f'<tr class="wk-sep"><td colspan="{4+len(classes)+1}">{wk}주차</td></tr>'
                prev_wk = wk

            # 날짜 셀 클래스
            date_cls = ""
            if is_td: date_cls = "d-today"
            elif is_past: date_cls = "d-past"

            # 요일 표시 (변경 시 표시)
            day_display = actual_day
            if eff_day != actual_day:
                day_display = f"{actual_day}→{eff_day}"

            wk_cell = str(wk) if d.weekday() == 0 or (prev_wk != wk) else ""

            # 원/교 뱃지
            if stype == "원":
                badge = '<span class="b-orig">원</span>'
            elif stype == "교":
                badge = '<span class="b-cross">교</span>'
            else:
                badge = ""

            # 반별 셀
            cells = ""
            for cls in classes:
                if hol:
                    cells += f'<td class="c-hol">{hol[:3]}</td>'
                elif exam:
                    cells += f'<td class="c-exam">{exam[:2]}</td>'
                elif stype == "결강":
                    cells += f'<td class="c-cancel">결강</td>'
                elif cls in day_prog:
                    info = day_prog[cls]
                    ln = info.get("차시","")
                    ctype = info.get("type","")
                    edited = info.get("edited", False)

                    if edited:
                        cell_cls = "c-edit"
                    elif ctype == "fixed":
                        cell_cls = "c-fixed"
                    elif ctype == "orig":
                        cell_cls = "c-orig"
                    elif ctype == "cross":
                        cell_cls = "c-cross"
                    else:
                        cell_cls = ""
                    cells += f'<td class="{cell_cls}">{ln}</td>'
                else:
                    cells += '<td>-</td>'

            # 비고
            note_parts = []
            if hol: note_parts.append(hol)
            if exam: note_parts.append(exam)
            if stype == "결강": note_parts.append("결강")
            if note: note_parts.append(note)
            if eff_day != actual_day: note_parts.append(f"{eff_day}요일수업")
            note_text = ", ".join(note_parts)

            html += f"""<tr>
                <td>{wk_cell}</td>
                <td class="{date_cls}">{d.strftime("%m/%d")}</td>
                <td class="{date_cls}">{day_display}</td>
                <td>{badge}</td>
                {cells}
                <td style="font-size:0.65rem;color:#78909c;text-align:left;">{note_text}</td>
            </tr>"""

        html += "</tbody></table></div>"
        st.markdown(html, unsafe_allow_html=True)

    # ── 오른쪽: 차시별 수업 날짜 + 시간표 ──
    with right_col:
        st.markdown('<div class="section-title">📅 차시별 수업 날짜</div>', unsafe_allow_html=True)

        # 차시별 날짜 매핑 구축
        lesson_dates = {}  # {반: {차시: (날짜str, type)}}
        for dk, day_data in progress.items():
            for cls, info in day_data.items():
                ln = info.get("차시")
                if ln and isinstance(ln, int):
                    lesson_dates.setdefault(cls, {})[ln] = (dk, info.get("type",""))

        # 최대 차시 수 계산
        max_lesson = 0
        for cls in classes:
            if cls in total_hours:
                max_lesson = max(max_lesson, total_hours[cls])

        if max_lesson > 0:
            notes = st.session_state.lesson_notes.get(subj, {})
            cls_th2 = "".join(f"<th>{c}</th>" for c in classes)
            html2 = f"""<div style="overflow-x:auto; max-height:400px; overflow-y:auto;">
            <table class="view-table">
            <thead><tr><th>차시</th>{cls_th2}<th>메모</th></tr></thead><tbody>"""

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
                            cells2 += f'<td class="{type_cls} {date_cls}">{d_obj.strftime("%m/%d")}</td>'
                        except:
                            cells2 += f'<td>{dk}</td>'
                    else:
                        cells2 += '<td>-</td>'

                memo = notes.get(str(ln), "")
                html2 += f'<tr><td>{ln}</td>{cells2}<td style="font-size:0.65rem;text-align:left;color:#546e7a;">{memo}</td></tr>'

            html2 += "</tbody></table></div>"
            st.markdown(html2, unsafe_allow_html=True)
        else:
            st.info("시간표와 학사일정을 입력하면 자동으로 표시됩니다.")

        # ── 요일별/반별 수업 교시 ──
        st.markdown('<div class="section-title">🕐 요일별/반별 수업 교시</div>', unsafe_allow_html=True)

        tt = st.session_state.timetable.get(subj, {})
        if tt:
            cls_th3 = "".join(f"<th>{c}</th>" for c in classes)
            html3 = f"""<table class="view-table">
            <thead><tr><th></th><th>요일</th>{cls_th3}</tr></thead><tbody>"""

            # 원시간표
            for day in WEEKDAYS:
                cells3 = ""
                for cls in classes:
                    periods = []
                    for p in range(1, 8):
                        if (day, p) in BLOCKED_CELLS:
                            continue
                        key = f"{day}_{p}"
                        val = tt.get(key, "")
                        parsed = parse_tt_cell(val)
                        if not parsed: continue
                        if "fixed" in parsed and parsed["fixed"] == cls:
                            periods.append(f"<span style='color:#e65100;'>{p}</span>")
                        elif "orig" in parsed and parsed["orig"] == cls:
                            periods.append(f"<span style='color:#2e7d32;'>{p}</span>")
                    cells3 += f'<td>{"·".join(periods) if periods else "-"}</td>'
                label = '<span class="b-orig">원</span>' if day == "월" else ""
                html3 += f'<tr><td>{label}</td><td>{day}</td>{cells3}</tr>'

            html3 += f'<tr class="wk-sep"><td colspan="{2+len(classes)}"></td></tr>'

            # 교차시간표
            for day in WEEKDAYS:
                cells3 = ""
                for cls in classes:
                    periods = []
                    for p in range(1, 8):
                        if (day, p) in BLOCKED_CELLS:
                            continue
                        key = f"{day}_{p}"
                        val = tt.get(key, "")
                        parsed = parse_tt_cell(val)
                        if not parsed: continue
                        if "fixed" in parsed and parsed["fixed"] == cls:
                            periods.append(f"<span style='color:#e65100;'>{p}</span>")
                        elif "cross" in parsed and parsed["cross"] == cls:
                            periods.append(f"<span style='color:#1565c0;'>{p}</span>")
                    cells3 += f'<td>{"·".join(periods) if periods else "-"}</td>'
                label = '<span class="b-cross">교</span>' if day == "월" else ""
                html3 += f'<tr><td>{label}</td><td>{day}</td>{cells3}</tr>'

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
    **입력 방법:**
    - 고정 수업 → 반 번호만 입력 (예: `6`)
    - 교차 수업 → 쉼표로 구분. 앞=원시간표, 뒤=교차시간표 (예: `8,4`)
    - 빈칸 → 수업 없음
    - 수요일 6,7교시 → 창체 (입력 불가)
    """)

    if not classes:
        st.warning("사이드바에서 반을 먼저 선택해주세요.")
    else:
        tt = st.session_state.timetable.get(subj, {})

        # 헤더
        hcols = st.columns([1.5] + [1]*5)
        hcols[0].markdown("**교시 \\ 요일**")
        for i, day in enumerate(WEEKDAYS):
            hcols[i+1].markdown(f"**{day}**")

        new_tt = dict(tt)
        for period in range(1, 8):
            rcols = st.columns([1.5] + [1]*5)
            rcols[0].markdown(f"**{period}교시**")
            for i, day in enumerate(WEEKDAYS):
                key = f"{day}_{period}"
                if (day, period) in BLOCKED_CELLS:
                    rcols[i+1].markdown("🔒 창체")
                    new_tt[key] = "창체"
                else:
                    cur = tt.get(key, "")
                    val = rcols[i+1].text_input(
                        f"{day}{period}", value=cur,
                        label_visibility="collapsed", key=f"tt_{day}_{period}",
                        placeholder="수업반")
                    if val.strip():
                        new_tt[key] = val.strip()
                    elif key in new_tt:
                        new_tt.pop(key, None)

        if st.button("시간표 저장", type="primary"):
            st.session_state.timetable[subj] = new_tt
            st.success("시간표가 저장되었습니다!")
            st.rerun()

        # CSV 업로드
        st.divider()
        st.markdown('<div class="section-title">📂 CSV 업로드 (선택)</div>', unsafe_allow_html=True)
        st.caption("형식: `요일,교시,수업반` — 수업반은 고정이면 `6`, 교차면 `8,4`")
        upload = st.file_uploader("CSV", type=["csv"], key="ttu")
        if upload:
            try:
                df = pd.read_csv(upload)
                new_tt2 = {}
                for _, row in df.iterrows():
                    day = str(row["요일"]).strip()
                    per = int(row["교시"])
                    val = str(row["수업반"]).strip()
                    key = f"{day}_{per}"
                    if (day, per) not in BLOCKED_CELLS:
                        new_tt2[key] = val
                # 창체 고정
                for day, per in BLOCKED_CELLS:
                    new_tt2[f"{day}_{per}"] = "창체"
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
    st.caption("🟩 원시간표  🟦 교차시간표  ⬜ 결강(회색)  🟥 공휴일  🟪 시험")

    try:
        all_dates = get_dates(sem)
    except:
        st.error("학기 날짜를 확인해주세요.")
        st.stop()

    start_d = all_dates[0]
    end_d = all_dates[-1]
    sch = st.session_state.schedule.get(subj, {})

    # 월 목록
    months = []
    cur_m = date(start_d.year, start_d.month, 1)
    while cur_m <= end_d:
        months.append(cur_m)
        cur_m = date(cur_m.year + (1 if cur_m.month == 12 else 0),
                     (cur_m.month % 12) + 1, 1)

    for m in months:
        st.markdown(f"#### {m.year}년 {m.month}월")
        _, days_in = calendar.monthrange(m.year, m.month)

        # 주별로 묶기 (월~금)
        weeks = {}
        for day_num in range(1, days_in + 1):
            d = date(m.year, m.month, day_num)
            if d < start_d or d > end_d or d.weekday() >= 5:
                continue
            # ISO week 기준
            wk = d.isocalendar()[1]
            weeks.setdefault(wk, {})
            weeks[wk][d.weekday()] = d

        for wk, wk_dates in weeks.items():
            # 5열 (월~금)
            cols = st.columns(5)
            for wd in range(5):
                with cols[wd]:
                    if wd in wk_dates:
                        d = wk_dates[wd]
                        dk = d.isoformat()
                        hol = holidays.get(dk, "")
                        exam = is_exam_day(subj, d)
                        cur_sch = sch.get(dk, {"type":"","day_override":"","note":""})
                        actual_day = WEEKDAYS[d.weekday()]

                        label = f"**{d.strftime('%d')}({actual_day})**"

                        if hol:
                            st.markdown(f"🔴 {label}")
                            st.caption(hol)
                        elif exam:
                            st.markdown(f"🟣 {label}")
                            st.caption(exam)
                        else:
                            st.markdown(label)

                            # 요일변경
                            day_opts = ["변경없음"] + WEEKDAYS
                            cur_override = cur_sch.get("day_override","")
                            ov_idx = day_opts.index(cur_override) if cur_override in day_opts else 0
                            sel_day = st.selectbox("수업요일", day_opts, index=ov_idx,
                                key=f"do_{dk}", label_visibility="collapsed")

                            cur_type = cur_sch.get("type", "")
                            # 원/교/결강 라디오
                            type_opts = ["미설정","원","교","결강"]
                            t_idx = type_opts.index(cur_type) if cur_type in type_opts else 0
                            sel_type = st.radio("유형", type_opts, index=t_idx,
                                key=f"st_{dk}", label_visibility="collapsed")

                            # 비고
                            cur_note = cur_sch.get("note","")
                            sel_note = st.text_input("비고", value=cur_note,
                                key=f"nt_{dk}", label_visibility="collapsed", placeholder="메모")

                            sch[dk] = {
                                "type": sel_type if sel_type != "미설정" else "",
                                "day_override": sel_day if sel_day != "변경없음" else "",
                                "note": sel_note
                            }
                    else:
                        st.markdown("&nbsp;")

    st.session_state.schedule[subj] = sch


# ══════════════════════════════════════════════════════════
# TAB 4: 진도 수정 (data_editor)
# ══════════════════════════════════════════════════════════
with tab4:
    st.markdown('<div class="section-title">✏️ 진도 수정</div>', unsafe_allow_html=True)
    st.info("셀을 더블클릭하여 차시를 수정하세요. 수정 내용은 진도 현황 탭에 자동 반영됩니다.")

    if not classes:
        st.warning("사이드바에서 반을 먼저 선택해주세요.")
        st.stop()

    try:
        all_dates = get_dates(sem)
    except:
        st.error("학기 날짜를 확인해주세요.")
        st.stop()

    progress = compute_progress(subj, sem, classes)

    # 날짜별 표를 DataFrame으로 변환
    school_dates = [d for d in all_dates if d.weekday() < 5]
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
            "날짜": d.strftime("%m/%d"),
            "요일": actual_day if eff_day == actual_day else f"{actual_day}→{eff_day}",
            "원/교": stype,
        }
        for cls in classes:
            if hol:
                row[cls] = hol[:3]
            elif exam:
                row[cls] = exam[:2]
            elif stype == "결강":
                row[cls] = "결강"
            elif cls in day_prog:
                row[cls] = day_prog[cls].get("차시","")
            else:
                row[cls] = ""
        row["비고"] = note
        row["_date"] = dk  # 숨김 키
        rows.append(row)

    df = pd.DataFrame(rows)

    # 편집 가능한 열 설정
    col_config = {
        "날짜": st.column_config.TextColumn("날짜", disabled=True, width="small"),
        "요일": st.column_config.TextColumn("요일", disabled=True, width="small"),
        "원/교": st.column_config.TextColumn("원/교", disabled=True, width="small"),
        "비고": st.column_config.TextColumn("비고", width="medium"),
        "_date": None,  # 숨김
    }
    for cls in classes:
        col_config[cls] = st.column_config.TextColumn(cls, width="small")

    edited_df = st.data_editor(df, use_container_width=True, height=600,
        column_config=col_config, key="progress_editor", hide_index=True)

    if st.button("수정 저장", type="primary"):
        overrides = st.session_state.overrides.get(subj, {})
        notes_update = {}

        for _, row in edited_df.iterrows():
            dk = row["_date"]
            orig_row = df[df["_date"] == dk].iloc[0] if len(df[df["_date"] == dk]) > 0 else None

            for cls in classes:
                new_val = row[cls]
                orig_val = orig_row[cls] if orig_row is not None else ""

                if str(new_val) != str(orig_val):
                    if dk not in overrides:
                        overrides[dk] = {}
                    try:
                        overrides[dk][cls] = int(new_val) if new_val and str(new_val).isdigit() else str(new_val)
                    except:
                        overrides[dk][cls] = str(new_val)

            # 비고 업데이트
            if row["비고"]:
                sch_entry = st.session_state.schedule.get(subj, {}).get(dk, {})
                sch_entry["note"] = str(row["비고"])
                st.session_state.schedule.setdefault(subj, {})[dk] = sch_entry

        st.session_state.overrides[subj] = overrides
        st.success("수정 내용이 저장되었습니다!")
        st.rerun()

    # ── 차시 메모 편집 ──
    st.divider()
    st.markdown('<div class="section-title">📖 차시별 메모</div>', unsafe_allow_html=True)
    st.caption("차시별 수업 내용을 메모하세요.")

    max_lesson = max((total_hours.get(cls, 0) for cls in classes), default=0) if 'total_hours' in dir() else 0
    if max_lesson == 0:
        # 재계산
        progress_temp = compute_progress(subj, sem, classes)
        th_temp = {cls: 0 for cls in classes}
        for dk, dd in progress_temp.items():
            for cls, info in dd.items():
                if info.get("차시") and cls in th_temp:
                    th_temp[cls] += 1
        max_lesson = max(th_temp.values()) if th_temp else 0

    if max_lesson > 0:
        notes = st.session_state.lesson_notes.get(subj, {})
        note_rows = []
        for ln in range(1, max_lesson + 1):
            note_rows.append({"차시": ln, "메모": notes.get(str(ln), "")})

        note_df = pd.DataFrame(note_rows)
        edited_notes = st.data_editor(note_df, use_container_width=True, hide_index=True,
            column_config={
                "차시": st.column_config.NumberColumn("차시", disabled=True, width="small"),
                "메모": st.column_config.TextColumn("메모", width="large"),
            }, key="note_editor")

        if st.button("메모 저장", type="primary", key="save_notes"):
            new_notes = {}
            for _, row in edited_notes.iterrows():
                if row["메모"]:
                    new_notes[str(int(row["차시"]))] = str(row["메모"])
            st.session_state.lesson_notes[subj] = new_notes
            st.success("메모가 저장되었습니다!")
            st.rerun()
    else:
        st.info("시간표와 학사일정을 입력하면 차시가 자동으로 생성됩니다.")
