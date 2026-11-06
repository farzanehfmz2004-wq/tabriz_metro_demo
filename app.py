# -*- coding: utf-8 -*-
"""دستیار سفر با مترو تبریز - خط ۱ (پروژه دمو)"""

import calendar
import math
from datetime import datetime, date, time as dtime

import folium
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

st.set_page_config(
    page_title="دستیار مترو تبریز",
    page_icon="🚇",
    layout="wide",
)

# >>> نام تیم خودتان را بین دو گیومه بنویسید <<<
TEAM_NAME = "نام تیم شما"

# ----------------------------------------------------------------------
# داده‌ها (همه هاردکد؛ مختصات تقریبی و فقط برای نمایش روی نقشه)
# ----------------------------------------------------------------------
STATIONS = [
    ("ائل‌گلی", 38.0705, 46.3720),
    ("سهند", 38.0695, 46.3600),
    ("امام رضا", 38.0705, 46.3480),
    ("خیام", 38.0720, 46.3380),
    ("۲۹ بهمن", 38.0738, 46.3290),
    ("استاد شهریار", 38.0755, 46.3210),
    ("دانشگاه", 38.0770, 46.3135),
    ("آبرسان", 38.0780, 46.3065),
    ("میدان قطب (سالار ملی)", 38.0790, 46.3000),
    ("شهید بهشتی", 38.0800, 46.2958),
    ("میدان ساعت", 38.0807, 46.2919),
    ("میدان کهن", 38.0815, 46.2860),
    ("قونقا", 38.0830, 46.2800),
    ("گازران", 38.0850, 46.2740),
    ("لاله", 38.0870, 46.2680),
    ("امام حسین", 38.0890, 46.2620),
    ("شهید باکری", 38.0910, 46.2560),
    ("نور", 38.0930, 46.2500),
]
NAMES = [s[0] for s in STATIONS]

OPEN_MIN = 6 * 60      # ۰۶:۰۰
CLOSE_MIN = 21 * 60    # ۲۱:۰۰
HEADWAY = 10           # فاصله قطارها (دقیقه) - شبیه‌سازی
MIN_PER_STOP = 2.5     # زمان تقریبی بین دو ایستگاه (دقیقه)

WEEKDAYS_FA = ["شنبه", "یکشنبه", "دوشنبه", "سه‌شنبه", "چهارشنبه", "پنجشنبه", "جمعه"]
MONTHS_FA = ["ژانویه", "فوریه", "مارس", "آوریل", "مه", "ژوئن",
             "ژوئیه", "اوت", "سپتامبر", "اکتبر", "نوامبر", "دسامبر"]

_FA_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


def fa(x):
    return str(x).translate(_FA_DIGITS)


def hhmm(minutes):
    minutes = int(minutes) % (24 * 60)
    return fa("%02d:%02d" % (minutes // 60, minutes % 60))


# ----------------------------------------------------------------------
# استایل (RTL، رنگ و فونت)
# ----------------------------------------------------------------------
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Vazirmatn:wght@300;400;600;800&display=swap');

.stApp, .stApp p, .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp label,
.stApp li, .stApp td, .stApp th, .stApp button, .stApp input, .stApp textarea,
[data-testid="stSidebar"] a {
    font-family: 'Vazirmatn', Tahoma, 'Segoe UI', sans-serif;
}
.stApp, [data-testid="stSidebar"], .stMarkdown, label, .stAlert {
    direction: rtl;
    text-align: right;
}
.block-container { padding-top: 2rem; max-width: 1200px; }

/* سایدبار */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0B2545 0%, #13466B 100%);
}
[data-testid="stSidebar"] * { color: #F2FBFC !important; }
[data-testid="stSidebarNav"]::before {
    content: "🚇  مترو تبریز | خط ۱";
    display: block;
    font-size: 1.25rem;
    font-weight: 800;
    padding: 1.2rem 1rem 1rem 1rem;
    margin-bottom: .5rem;
    border-bottom: 1px solid rgba(255,255,255,.25);
    color: #7FE3E8;
}

/* بنر بالای صفحه */
.hero {
    background: linear-gradient(120deg, #0B2545 0%, #0E7C86 100%);
    color: #fff;
    padding: 1.4rem 1.6rem;
    border-radius: 16px;
    margin-bottom: 1.2rem;
}
.hero h2 { color: #fff !important; margin: 0 0 .3rem 0; padding: 0; }
.hero p { color: #D8F3F5 !important; margin: 0; }

/* کارت‌ها */
[data-testid="stMetric"] {
    background: #E8F4F6;
    border-radius: 14px;
    padding: .9rem 1rem;
    border: 1px solid #C9E4E8;
}
[data-testid="stVerticalBlockBorderWrapper"] { border-radius: 14px; }
.tip {
    background: #E0F7F8;
    border-right: 6px solid #0E7C86;
    padding: .9rem 1.1rem;
    border-radius: 10px;
    color: #0B2545;
}

/* تقویم */
table.cal { width: 100%; border-collapse: separate; border-spacing: 6px; direction: rtl; }
table.cal th { background: #0B2545; color: #fff; padding: .5rem; border-radius: 8px; text-align: center; font-size: .85rem; }
table.cal td { background: #F3F8F9; border-radius: 8px; text-align: center; padding: .5rem .2rem; height: 62px; vertical-align: top; color: #0B2545; }
table.cal td.free { background: #0E7C86; color: #fff; font-weight: 600; }
table.cal td.today { outline: 3px solid #F5A623; }
table.cal td.empty { background: transparent; }
table.cal td small { display: block; font-size: .65rem; margin-top: 2px; }
/* موبایل و صفحه‌های کوچک */
@media (max-width: 768px) {
    .block-container { padding: 1rem .8rem 2rem .8rem; }
    .hero { padding: 1rem 1.1rem; border-radius: 12px; }
    .hero h2 { font-size: 1.3rem; }
    .hero p { font-size: .85rem; }
    [data-testid="stMetric"] { padding: .6rem .7rem; }
    [data-testid="stMetricValue"] { font-size: 1.3rem; }
    [data-testid="stMetricLabel"] { font-size: .8rem; }
    div[data-testid="stHorizontalBlock"]:has([data-testid="stMetric"]) { flex-wrap: wrap; gap: .6rem; }
    div[data-testid="stHorizontalBlock"]:has([data-testid="stMetric"]) > div {
        min-width: calc(50% - .6rem) !important;
        flex: 1 1 calc(50% - .6rem) !important;
    }
    div[data-testid="stHorizontalBlock"]:has(#maplayout) { flex-direction: column-reverse; }
    iframe { max-width: 100%; }
    table.cal { border-spacing: 3px; }
    table.cal th { font-size: .62rem; padding: .35rem .1rem; }
    table.cal td { height: 46px; padding: .3rem .1rem; font-size: .8rem; }
    table.cal td small { font-size: .5rem; }
}
</style>
"""

st.markdown(CSS, unsafe_allow_html=True)


def hero(title, subtitle):
    st.markdown(
        '<div class="hero"><h2>%s</h2><p>%s</p></div>' % (title, subtitle),
        unsafe_allow_html=True,
    )


# ----------------------------------------------------------------------
# منطق زمان‌بندی قطار
# ----------------------------------------------------------------------
def next_departure(minute_of_day):
    """نزدیک‌ترین حرکت قطار در/بعد از دقیقه‌ی داده‌شده؛ None اگر سرویس تمام شده."""
    if minute_of_day <= OPEN_MIN:
        return OPEN_MIN
    if minute_of_day > CLOSE_MIN:
        return None
    k = math.ceil((minute_of_day - OPEN_MIN) / HEADWAY)
    dep = OPEN_MIN + k * HEADWAY
    return dep if dep <= CLOSE_MIN else None


def now_minutes():
    n = datetime.now()
    return n.hour * 60 + n.minute + n.second / 60.0


# ----------------------------------------------------------------------
# صفحه ۱: داشبورد
# ----------------------------------------------------------------------
def page_dashboard():
    hero("داشبورد مترو تبریز", "دستیار هوشمند سفر شما در خط ۱ مترو تبریز")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("ایستگاه‌ها", fa(len(STATIONS)))
    c2.metric("طول خط (کیلومتر)", fa("17.2"))
    c3.metric("ساعت کاری", "%s تا %s" % (hhmm(OPEN_MIN), hhmm(CLOSE_MIN)))
    c4.metric("فاصله قطارها", "%s دقیقه" % fa(HEADWAY))

    st.write("")
    today = date.today()
    if today.weekday() == 1:  # سه‌شنبه
        tip = "🎉 امروز سه‌شنبه است؛ مترو برای همه <b>رایگان</b> است!"
    else:
        days_left = (1 - today.weekday()) % 7
        tip = "🗓️ سه‌شنبه‌ها مترو رایگان است. تا سه‌شنبه‌ی بعد <b>%s روز</b> مانده." % fa(days_left)
    st.markdown('<div class="tip"><b>نکته امروز:</b> %s</div>' % tip, unsafe_allow_html=True)

    notes = st.session_state.get("announcements", [])
    if notes:
        st.write("")
        st.warning("اطلاعیه: " + " | ".join(n["text"] for n in notes[-3:]))

    st.write("")
    st.subheader("دسترسی سریع")
    cards = [
        ("trip", "برنامه سفر و یادآور", ":material/schedule:", "زمان قطار بعدی و هشدار حرکت"),
        ("map", "نقشه و ایستگاه‌ها", ":material/map:", "ایستگاه‌های خط ۱ روی نقشه"),
        ("calendar", "تقویم روزهای رایگان", ":material/calendar_month:", "سه‌شنبه‌ها مترو رایگان است"),
        ("crowd", "نمودار شلوغی", ":material/bar_chart:", "ساعات شلوغ و خلوت هر ایستگاه"),
        ("about", "تماس با ما / درباره", ":material/info:", "درباره‌ی پروژه و ثبت نظر"),
    ]
    cols = st.columns(3)
    for i, (key, label, icon, desc) in enumerate(cards):
        with cols[i % 3]:
            with st.container(border=True):
                st.markdown("**%s**" % label)
                st.caption(desc)
                st.page_link(PAGES[key], label="باز کردن", icon=icon)


# ----------------------------------------------------------------------
# صفحه ۲: برنامه سفر و یادآور
# ----------------------------------------------------------------------
def page_trip():
    hero("برنامه سفر و یادآور", "مبدأ و مقصد را انتخاب کنید و زمان حرکت را بسنجید")

    c1, c2 = st.columns(2)
    origin = c1.selectbox("ایستگاه مبدأ", NAMES, index=0, key="trip_origin")
    dest = c2.selectbox("ایستگاه مقصد", NAMES, index=len(NAMES) - 1, key="trip_dest")

    if origin == dest:
        st.info("مبدأ و مقصد یکسان است؛ یک مقصد دیگر انتخاب کنید.")
        return

    i, j = NAMES.index(origin), NAMES.index(dest)
    stops = abs(i - j)
    travel = stops * MIN_PER_STOP
    direction = "به سمت %s" % (NAMES[-1] if j > i else NAMES[0])

    m1, m2, m3 = st.columns(3)
    m1.metric("تعداد ایستگاه تا مقصد", fa(stops))
    m2.metric("زمان تقریبی سفر", "%s دقیقه" % fa(int(round(travel))))
    m3.metric("جهت حرکت", direction)

    st.divider()
    st.subheader(":material/train: قطار بعدی")
    now_m = now_minutes()
    dep = next_departure(now_m)
    if dep is None:
        st.error("سرویس امروز به پایان رسیده است. اولین قطار فردا ساعت %s حرکت می‌کند." % hhmm(OPEN_MIN))
    else:
        wait = max(0, math.ceil(dep - now_m))
        if wait == 0:
            st.success("قطار همین الان در ایستگاه است!")
        else:
            st.success("قطار بعدی **%s دقیقه دیگر** (ساعت %s) حرکت می‌کند." % (fa(wait), hhmm(dep)))

    st.divider()
    st.subheader(":material/alarm: یادآور حرکت")
    st.caption("زمانی که می‌خواهید سوار قطار شوید و مدت پیاده‌روی تا ایستگاه را وارد کنید.")
    n = datetime.now()
    default_t = dtime(n.hour, n.minute)
    d1, d2 = st.columns(2)
    board_t = d1.time_input("زمان سوار شدن", value=default_t, key="trip_board_time")
    walk = d2.number_input("پیاده‌روی تا ایستگاه (دقیقه)", min_value=0, max_value=120,
                           value=10, step=1, key="trip_walk")

    board_m = board_t.hour * 60 + board_t.minute
    dep2 = next_departure(board_m)
    if dep2 is None:
        st.error("در این ساعت مترو سرویس نمی‌دهد (ساعت کاری %s تا %s)." % (hhmm(OPEN_MIN), hhmm(CLOSE_MIN)))
        return

    leave_in = (dep2 - now_m) - walk
    st.write("قطار مناسب شما ساعت **%s** حرکت می‌کند و حدود ساعت **%s** به %s می‌رسید."
             % (hhmm(dep2), hhmm(dep2 + travel), dest))

    if leave_in < 0:
        st.error("برای این قطار دیر شده است. قطار بعدی را در نظر بگیرید یا زمان را تغییر دهید.")
    elif leave_in <= 5:
        st.warning("⏰ هشدار: **%s دقیقه دیگر** باید حرکت کنید!" % fa(int(math.ceil(leave_in))))
    else:
        st.info("می‌توانید **%s دقیقه دیگر** از جایتان حرکت کنید." % fa(int(math.ceil(leave_in))))


# ----------------------------------------------------------------------
# صفحه ۳: نقشه
# ----------------------------------------------------------------------
def build_map(selected):
    if selected is not None:
        center, zoom = [STATIONS[selected][1], STATIONS[selected][2]], 15
    else:
        center = [sum(s[1] for s in STATIONS) / len(STATIONS),
                  sum(s[2] for s in STATIONS) / len(STATIONS)]
        zoom = 13
    m = folium.Map(location=center, zoom_start=zoom, tiles="OpenStreetMap")

    folium.PolyLine([(s[1], s[2]) for s in STATIONS], color="#0E7C86", weight=5, opacity=0.85).add_to(m)

    for idx, (name, lat, lon) in enumerate(STATIONS):
        html = (
            '<div style="direction:rtl;text-align:right;font-family:Tahoma,sans-serif;min-width:170px">'
            "<b>%s</b><br>ایستگاه شماره %s از %s<br>ساعت کاری: %s تا %s<br>سه‌شنبه‌ها: رایگان"
            "</div>" % (name, fa(idx + 1), fa(len(STATIONS)), hhmm(OPEN_MIN), hhmm(CLOSE_MIN))
        )
        is_sel = (idx == selected)
        folium.Marker(
            location=[lat, lon],
            tooltip=name,
            popup=folium.Popup(html, max_width=260, show=is_sel),
            icon=folium.Icon(color="red" if is_sel else "blue", icon="train", prefix="fa"),
        ).add_to(m)
    return m


def page_map():
    hero("نقشه خط و ایستگاه‌ها", "روی مارکرها کلیک کنید یا از لیست کنار نقشه ایستگاه را انتخاب کنید")
    st.caption("مختصات ایستگاه‌ها تقریبی است و فقط برای نمایش دمو استفاده می‌شود. نمایش نقشه به اینترنت نیاز دارد.")

    col_list, col_map = st.columns([1, 3])
    with col_list:
        choice = st.radio("لیست ایستگاه‌ها", NAMES, index=None, key="map_station")
    selected = NAMES.index(choice) if choice in NAMES else None

    with col_map:
        st.markdown('<span id="maplayout"></span>', unsafe_allow_html=True)
        m = build_map(selected)
        try:
            st_folium(m, height=560, use_container_width=True, returned_objects=[], key="metro_map")
        except TypeError:
            st_folium(m, height=560, width=900, returned_objects=[], key="metro_map")


# ----------------------------------------------------------------------
# صفحه ۴: تقویم
# ----------------------------------------------------------------------
def page_calendar():
    hero("تقویم روزهای رایگان", "سه‌شنبه‌ها مترو تبریز برای همه رایگان است")

    today = date.today()
    c1, c2 = st.columns(2)
    month = c1.selectbox("ماه", list(range(1, 13)), index=today.month - 1,
                         format_func=lambda x: MONTHS_FA[x - 1], key="cal_month")
    year = c2.number_input("سال (میلادی)", min_value=2000, max_value=2100,
                           value=today.year, step=1, key="cal_year")
    year = int(year)

    cal = calendar.Calendar(firstweekday=5)  # شروع هفته از شنبه
    rows = ["<table class='cal'><tr>" + "".join("<th>%s</th>" % d for d in WEEKDAYS_FA) + "</tr>"]
    for week in cal.monthdayscalendar(year, month):
        rows.append("<tr>")
        for col, day in enumerate(week):
            if day == 0:
                rows.append("<td class='empty'></td>")
                continue
            classes = []
            extra = ""
            if col == 3:  # سه‌شنبه
                classes.append("free")
                extra = "<small>مترو رایگان</small>"
            if date(year, month, day) == today:
                classes.append("today")
            rows.append("<td class='%s'>%s%s</td>" % (" ".join(classes), fa(day), extra))
        rows.append("</tr>")
    rows.append("</table>")
    st.markdown("".join(rows), unsafe_allow_html=True)
    st.caption("🟦 سه‌شنبه‌ها رایگان | کادر نارنجی: امروز")

    st.divider()
    st.subheader(":material/campaign: اطلاعیه‌ها")
    if "announcements" not in st.session_state:
        st.session_state["announcements"] = []

    text = st.text_input("متن اطلاعیه (مثلاً: امروز تعطیل رسمی است)", key="ann_text")
    if st.button("افزودن اطلاعیه", type="primary", key="ann_btn"):
        if text.strip():
            st.session_state["announcements"].append(
                {"text": text.strip(), "time": datetime.now().strftime("%H:%M")}
            )
            st.success("اطلاعیه اضافه شد.")
        else:
            st.warning("ابتدا متن اطلاعیه را بنویسید.")

    if st.session_state["announcements"]:
        for n in reversed(st.session_state["announcements"]):
            st.info("%s  (ساعت %s)" % (n["text"], fa(n["time"])))
        if st.button("پاک کردن همه اطلاعیه‌ها", key="ann_clear"):
            st.session_state["announcements"] = []
            st.rerun()
    else:
        st.caption("هنوز اطلاعیه‌ای ثبت نشده است.")


# ----------------------------------------------------------------------
# صفحه ۵: نمودار شلوغی
# ----------------------------------------------------------------------
BASE_PROFILE = {  # ساعت: میزان شلوغی پایه (۰ تا ۱۰۰) - داده نمونه
    6: 35, 7: 75, 8: 95, 9: 70, 10: 45, 11: 35, 12: 30, 13: 28,
    14: 32, 15: 45, 16: 70, 17: 92, 18: 98, 19: 70, 20: 40,
}


def crowd_for(station_index):
    centrality = 1 - abs(station_index - 9.5) / 9.5   # ایستگاه‌های مرکزی شلوغ‌ترند
    factor = 0.75 + 0.35 * centrality
    wobble = ((station_index * 7) % 5 - 2) * 0.02
    out = {}
    for h, v in BASE_PROFILE.items():
        out["%02d:00" % h] = max(5, min(100, round(v * (factor + wobble))))
    return out


def page_crowd():
    hero("نمودار شلوغی", "ساعات شلوغ و خلوت ایستگاه‌ها (داده نمونه برای دمو)")
    name = st.selectbox("ایستگاه", NAMES, index=NAMES.index("میدان ساعت"), key="crowd_station")
    data = crowd_for(NAMES.index(name))

    df = pd.DataFrame({"شلوغی (٪)": list(data.values())}, index=list(data.keys()))
    st.bar_chart(df, color="#0E7C86", height=380)

    busiest = max(data, key=data.get)
    quietest = min(data, key=data.get)
    c1, c2 = st.columns(2)
    c1.metric("شلوغ‌ترین ساعت", fa(busiest))
    c2.metric("خلوت‌ترین ساعت", fa(quietest))
    st.caption("ساعات پیک: صبح (۷ تا ۹) و عصر (۱۶ تا ۱۹). ظهرها معمولاً خلوت‌تر است.")


# ----------------------------------------------------------------------
# صفحه ۶: درباره
# ----------------------------------------------------------------------
def page_about():
    hero("تماس با ما / درباره", "درباره‌ی پروژه و تیم")
    st.markdown("**نام تیم:** " + TEAM_NAME)
    st.markdown(
        """
**درباره پروژه:** این برنامه یک دمو از «دستیار سفر با مترو تبریز (خط ۱)» است که با پایتون و Streamlit ساخته شده
و شامل برنامه سفر، نقشه، تقویم روزهای رایگان و نمودار شلوغی است.

> ⚠️ داده‌ها از منابع عمومی گردآوری شده و فقط برای **دمو** است. مختصات ایستگاه‌ها، زمان قطارها
> و میزان شلوغی تقریبی یا شبیه‌سازی‌شده هستند و جایگزین اطلاعات رسمی سازمان قطار شهری تبریز نیستند.
"""
    )
    st.subheader(":material/chat: ثبت نظر")
    with st.form("feedback_form", clear_on_submit=True):
        nm = st.text_input("نام")
        email = st.text_input("ایمیل")
        msg = st.text_area("نظر یا پیشنهاد شما")
        sent = st.form_submit_button("ارسال")
    if sent:
        st.success("ممنون از نظر شما! (این فرم فقط ظاهری است و چیزی ذخیره نمی‌شود.)")


# ----------------------------------------------------------------------
# ناوبری
# ----------------------------------------------------------------------
PAGES = {
    "dashboard": st.Page(page_dashboard, title="داشبورد", icon=":material/home:",
                         url_path="dashboard", default=True),
    "trip": st.Page(page_trip, title="برنامه سفر و یادآور", icon=":material/schedule:", url_path="trip"),
    "map": st.Page(page_map, title="نقشه و ایستگاه‌ها", icon=":material/map:", url_path="map"),
    "calendar": st.Page(page_calendar, title="تقویم روزهای رایگان", icon=":material/calendar_month:",
                        url_path="calendar"),
    "crowd": st.Page(page_crowd, title="نمودار شلوغی", icon=":material/bar_chart:", url_path="crowd"),
    "about": st.Page(page_about, title="تماس با ما / درباره", icon=":material/info:", url_path="about"),
}

pg = st.navigation(list(PAGES.values()))
pg.run()
