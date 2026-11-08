# -*- coding: utf-8 -*-
"""
مترو تبریز - دستیار سفر (خط ۱)

نصب کتابخانه‌ها (فقط یک بار، در ترمینال):
    pip install streamlit folium streamlit-folium jdatetime
اجرا:
    python -m streamlit run app.py
"""

import math
from datetime import datetime, date, time as dtime, timedelta, timezone

import altair as alt
import folium
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

# تقویم شمسی: اگر jdatetime نصب نبود، برنامه با تبدیل داخلی کار می‌کند.
try:
    import jdatetime  # pip install jdatetime
    HAS_JD = True
except Exception:
    jdatetime = None
    HAS_JD = False

st.set_page_config(
    page_title="مترو تبریز",
    page_icon="🚇",
    layout="wide",
    initial_sidebar_state="auto",
)

# >>> نام تیم خودتان را بین دو گیومه بنویسید <<<
TEAM_NAME = "نام تیم شما"

# ----------------------------------------------------------------------
# داده‌ها (همه داخل کد؛ مختصات تقریبی است)
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

OPEN_MIN = 6 * 60       # ۰۶:۰۰
CLOSE_MIN = 21 * 60     # ۲۱:۰۰
HEADWAY = 10            # فاصله قطارها (دقیقه)
MIN_PER_STOP = 2.5      # زمان تقریبی بین دو ایستگاه (دقیقه)

WEEKDAYS_FA = ["شنبه", "یکشنبه", "دوشنبه", "سه‌شنبه", "چهارشنبه", "پنجشنبه", "جمعه"]
JMONTHS = ["فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
           "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"]

# تصویر بنر هر صفحه. اگر لینکی باز نشد، خودکار رنگ و گرادیان نمایش داده می‌شود.
# برای عوض کردن تصویر، فقط آدرس را عوض کنید (یا None بگذارید تا فقط رنگ بماند).
_U = "https://images.unsplash.com/"
_Q = "?auto=format&amp;fit=crop&amp;w=1400&amp;q=60"
PAGE_IMAGES = {
    "dashboard": _U + "photo-1474487548417-781cb71495f3" + _Q,
    "trip": _U + "photo-1474487548417-781cb71495f3" + _Q,
    "map": _U + "photo-1524661135-423995f22d0b" + _Q,
    "calendar": _U + "photo-1506784983877-45594efa4cbe" + _Q,
    "crowd": _U + "photo-1551288049-bebda4e38f71" + _Q,
    "about": _U + "photo-1423666639041-f56000c27a9a" + _Q,
}
PAGE_ICON = {"dashboard": "home", "trip": "clock", "map": "map",
             "calendar": "calendar", "crowd": "chart", "about": "info"}

# ----------------------------------------------------------------------
# ابزارهای کمکی: ارقام فارسی، زمان تهران، آیکون‌ها
# ----------------------------------------------------------------------
_FA_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


def fa(x):
    return str(x).translate(_FA_DIGITS)


def hhmm(minutes):
    minutes = int(minutes) % (24 * 60)
    return fa("%02d:%02d" % (minutes // 60, minutes % 60))


# ایران ساعت تابستانی ندارد؛ اختلاف ثابت ۳:۳۰ با UTC است.
# (سرور آنلاین ساعت UTC دارد، پس باید ساعت تهران را حساب کنیم.)
IRAN_TZ = timezone(timedelta(hours=3, minutes=30))


def now_tehran():
    return datetime.now(IRAN_TZ)


ICONS = {
    "home": '<path d="M3 11l9-8 9 8"/><path d="M5 10v10h14V10"/><path d="M10 20v-6h4v6"/>',
    "train": '<rect x="5" y="3" width="14" height="14" rx="3"/><path d="M5 11h14"/><path d="M9 14h.01M15 14h.01"/><path d="M8 21l2-4M16 21l-2-4"/>',
    "clock": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    "map": '<path d="M12 21s-7-6.2-7-11a7 7 0 0 1 14 0c0 4.8-7 11-7 11z"/><circle cx="12" cy="10" r="2.5"/>',
    "calendar": '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4"/>',
    "chart": '<path d="M5 20V10M12 20V4M19 20v-7"/>',
    "info": '<circle cx="12" cy="12" r="9"/><path d="M12 11v5M12 8h.01"/>',
    "ruler": '<rect x="2" y="8" width="20" height="8" rx="1.5"/><path d="M6 8v3M10 8v4M14 8v3M18 8v4"/>',
    "route": '<circle cx="6" cy="6" r="2"/><circle cx="18" cy="18" r="2"/><path d="M8 6h6a3 3 0 0 1 0 6h-4a3 3 0 0 0 0 6h6"/>',
    "arrow": '<path d="M19 12H5M11 6l-6 6 6 6"/>',
    "bell": '<path d="M6 17v-6a6 6 0 0 1 12 0v6l2 2H4z"/><path d="M10 21a2 2 0 0 0 4 0"/>',
    "gift": '<rect x="3" y="8" width="18" height="4" rx="1"/><path d="M12 8v13M5 12v9h14v-9"/><path d="M12 8c-2-4-6-3-5 0M12 8c2-4 6-3 5 0"/>',
    "mail": '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="M3 7l9 6 9-6"/>',
    "alert": '<path d="M12 3l10 18H2z"/><path d="M12 10v5M12 18h.01"/>',
    "check": '<circle cx="12" cy="12" r="9"/><path d="M8 12l3 3 5-6"/>',
    "users": '<circle cx="9" cy="8" r="3"/><path d="M3 20c0-3.3 2.7-6 6-6s6 2.7 6 6"/><path d="M16 5a3 3 0 0 1 0 6M18 14c2 .8 3 3 3 6"/>',
}


def icon(name, size=22):
    return ('<svg viewBox="0 0 24 24" width="%d" height="%d" fill="none" stroke="currentColor" '
            'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">%s</svg>'
            % (size, size, ICONS[name]))


def html(s):
    st.markdown(s, unsafe_allow_html=True)


_WIN = "".join('<rect x="%d" y="26" width="26" height="16" rx="4" fill="#0B2545" fill-opacity=".85"/>' % (20 + 36 * i)
               for i in range(5))
_WHL = "".join('<circle cx="%d" cy="76" r="7" fill="#0B2545"/>' % x for x in (40, 90, 150, 190))
TRAIN_ART = (
    '<svg class="hero-art" viewBox="0 0 240 100" width="230" height="96" aria-hidden="true">'
    '<rect x="8" y="18" width="204" height="52" rx="16" fill="#ffffff" fill-opacity=".95"/>'
    '<rect x="8" y="46" width="204" height="8" fill="#13A3AD"/>'
    + _WIN + '<circle cx="204" cy="62" r="4" fill="#FFD76A"/>' + _WHL +
    '<line x1="0" y1="86" x2="240" y2="86" stroke="#7FE3E8" stroke-width="3" stroke-linecap="round"/>'
    '</svg>'
)


def banner(key, title, subtitle, art=False):
    img = PAGE_IMAGES.get(key)
    overlay = "linear-gradient(120deg, rgba(11,37,69,.90) 0%, rgba(14,124,134,.66) 100%)"
    if img:
        bg = "background-image:%s,url('%s');" % (overlay, img)
    else:
        bg = "background-image:linear-gradient(120deg,#0B2545,#0E7C86);"
    html('<div class="hero%s" style="%s"><div class="hero-ic">%s</div>'
         '<div><h2>%s</h2><p>%s</p></div>%s</div>'
         % (" tall" if art else "", bg, icon(PAGE_ICON[key], 28), title, subtitle,
            TRAIN_ART if art else ""))


def stat_grid(items):
    """items: لیستی از (نام آیکون، عنوان، مقدار)"""
    cells = "".join(
        '<div class="stat"><div class="stat-ic">%s</div><div><div class="stat-l">%s</div>'
        '<div class="stat-v">%s</div></div></div>' % (icon(ic, 22), label, value)
        for ic, label, value in items
    )
    html('<div class="stat-grid">%s</div>' % cells)


def note(kind, ic, text):
    """kind: ok | warn | bad | info"""
    html('<div class="note %s">%s<div>%s</div></div>' % (kind, icon(ic, 22), text))


# ----------------------------------------------------------------------
# تقویم شمسی
# ----------------------------------------------------------------------
def _g2j(gy, gm, gd):
    g_d_m = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    gy2 = gy + 1 if gm > 2 else gy
    days = (355666 + (365 * gy) + ((gy2 + 3) // 4) - ((gy2 + 99) // 100)
            + ((gy2 + 399) // 400) + gd + g_d_m[gm - 1])
    jy = -1595 + (33 * (days // 12053))
    days %= 12053
    jy += 4 * (days // 1461)
    days %= 1461
    if days > 365:
        jy += (days - 1) // 365
        days = (days - 1) % 365
    if days < 186:
        jm = 1 + days // 31
        jd = 1 + days % 31
    else:
        jm = 7 + (days - 186) // 30
        jd = 1 + (days - 186) % 30
    return jy, jm, jd


def _j2g(jy, jm, jd):
    jy += 1595
    days = -355668 + (365 * jy) + ((jy // 33) * 8) + (((jy % 33) + 3) // 4) + jd
    if jm < 7:
        days += (jm - 1) * 31
    else:
        days += ((jm - 7) * 30) + 186
    gy = 400 * (days // 146097)
    days %= 146097
    if days > 36524:
        days -= 1
        gy += 100 * (days // 36524)
        days %= 36524
        if days >= 365:
            days += 1
    gy += 4 * (days // 1461)
    days %= 1461
    if days > 365:
        gy += (days - 1) // 365
        days = (days - 1) % 365
    gd = days + 1
    leap = (gy % 4 == 0 and gy % 100 != 0) or gy % 400 == 0
    sal_a = [0, 31, 29 if leap else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    gm = 0
    while gm < 13 and gd > sal_a[gm]:
        gd -= sal_a[gm]
        gm += 1
    return gy, gm, gd


def to_jalali(d):
    """تاریخ میلادی (date) -> (سال، ماه، روز) شمسی"""
    if HAS_JD:
        try:
            j = jdatetime.date.fromgregorian(date=d)
            return j.year, j.month, j.day
        except Exception:
            pass
    return _g2j(d.year, d.month, d.day)


def to_gregorian(jy, jm, jd):
    """تاریخ شمسی -> تاریخ میلادی (date)"""
    if HAS_JD:
        try:
            g = jdatetime.date(jy, jm, jd).togregorian()
            return date(g.year, g.month, g.day)
        except Exception:
            pass
    gy, gm, gd = _j2g(jy, jm, jd)
    return date(gy, gm, gd)


def is_jleap(jy):
    g = to_gregorian(jy, 12, 30)
    return to_jalali(g) == (jy, 12, 30)


def jalali_month_length(jy, jm):
    if jm <= 6:
        return 31
    if jm <= 11:
        return 30
    return 30 if is_jleap(jy) else 29


# ----------------------------------------------------------------------
# استایل
# ----------------------------------------------------------------------
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Vazirmatn:wght@300;400;600;800&display=swap');

:root {
    --navy: #0B2545;
    --teal: #0E7C86;
    --soft: #E3F1F3;
    --line: #D5E8EB;
    --muted: #4C6A7A;
    --shadow: 0 4px 16px rgba(11,37,69,.08);
}

html, body, .stApp { background: #F5FAFB; }
.stApp, .stApp p, .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp label,
.stApp li, .stApp td, .stApp th, .stApp button, .stApp input, .stApp textarea,
[data-testid="stSidebar"] a {
    font-family: 'Vazirmatn', Tahoma, 'Segoe UI', sans-serif;
}

/* راست‌چین: فقط برای محتوا (چیدمان کلی صفحه دست نمی‌خورد تا در موبایل به هم نریزد) */
.block-container, .block-container .stMarkdown, [data-testid="stWidgetLabel"],
.block-container label, .block-container .stAlert, [data-testid="stSidebarNav"] {
    direction: rtl;
    text-align: right;
}
/* در لپ‌تاپ، کل صفحه راست‌به‌چپ است (منو سمت راست) */
@media (min-width: 769px) {
    .stApp, [data-testid="stSidebar"] { direction: rtl; }
}
.stApp { overflow-x: hidden; }
.block-container { padding-top: 3rem; max-width: 1200px; }

/* مخفی کردن گیت‌هاب، ویرایش، منوی سه‌نقطه، Deploy و فوتر (دکمه‌ی منوی کناری مخفی نمی‌شود) */
[data-testid="stToolbarActions"], [data-testid="stAppDeployButton"], [data-testid="stMainMenu"],
[data-testid="stDecoration"], [data-testid="stStatusWidget"], .stDeployButton, .stAppDeployButton,
#MainMenu, footer, [class*="viewerBadge"], [data-testid="stHeader"] a[href*="github.com"] {
    display: none !important;
}
[data-testid="stHeader"] { background: rgba(245,250,251,.92); }
[data-testid="stExpandSidebarButton"], [data-testid="stSidebarCollapsedControl"], [data-testid="collapsedControl"] {
    display: flex !important;
    visibility: visible !important;
    opacity: 1 !important;
}
[data-testid="stExpandSidebarButton"] *, [data-testid="stSidebarCollapsedControl"] *, [data-testid="collapsedControl"] * {
    color: #0B2545 !important;
}

/* سایدبار */
[data-testid="stSidebar"] { background: linear-gradient(180deg, #0B2545 0%, #13466B 100%); }
[data-testid="stSidebar"] * { color: #F2FBFC !important; }
[data-testid="stSidebarNav"]::before {
    content: "🚇  مترو تبریز | خط ۱";
    display: block;
    font-size: 1.25rem;
    font-weight: 800;
    padding: 1.2rem 1rem 1rem 1rem;
    margin-bottom: .5rem;
    border-bottom: 1px solid rgba(255,255,255,.25);
    color: #7FE3E8 !important;
}

/* دکمه‌ها (حداقل ۴۴ پیکسل برای لمس راحت) */
.stButton > button, [data-testid="stFormSubmitButton"] > button {
    min-height: 44px; border-radius: 12px; font-weight: 600;
}

/* بنر بالای صفحه */
.hero {
    display: flex; align-items: center; gap: 1rem;
    color: #fff; padding: 1.5rem 1.6rem; border-radius: 18px; margin-bottom: 1.2rem;
    box-shadow: 0 8px 24px rgba(11,37,69,.18);
    background-color: #0B2545; background-size: cover; background-position: center;
}
.hero.tall { padding: 2rem 1.8rem; min-height: 170px; }
.hero-ic {
    flex: 0 0 auto; width: 54px; height: 54px; border-radius: 14px;
    background: rgba(255,255,255,.16); color: #fff;
    display: flex; align-items: center; justify-content: center;
}
.hero h2 { color: #fff !important; margin: 0 0 .25rem 0; padding: 0; line-height: 1.5; font-size: clamp(1.2rem, 3.2vw, 1.8rem); }
.hero p { color: #E3F6F7 !important; margin: 0; font-size: clamp(.8rem, 1.8vw, 1rem); }
.hero-art { margin-inline-start: auto; flex: 0 0 auto; max-width: 40%; height: auto; }

/* کارت‌های آماری */
.stat-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: .8rem; margin: .4rem 0 1rem 0; }
.stat {
    background: #fff; border: 1px solid var(--line); border-radius: 16px; padding: .9rem 1rem;
    display: flex; align-items: center; gap: .8rem; box-shadow: var(--shadow);
    transition: transform .2s ease, box-shadow .2s ease;
}
.stat:hover { transform: translateY(-3px); box-shadow: 0 10px 24px rgba(11,37,69,.14); }
.stat-ic {
    flex: 0 0 auto; width: 42px; height: 42px; border-radius: 12px; color: #fff;
    background: linear-gradient(135deg, #0E7C86, #13A3AD);
    display: flex; align-items: center; justify-content: center;
}
.stat-l { font-size: .78rem; color: var(--muted); margin-bottom: 2px; }
.stat-v { font-size: 1.1rem; font-weight: 800; color: var(--navy); line-height: 1.5; overflow-wrap: anywhere; }

/* نکته و پیام‌ها */
.tip {
    display: flex; gap: .7rem; align-items: flex-start;
    background: #E0F7F8; border-right: 6px solid #0E7C86;
    padding: .9rem 1.1rem; border-radius: 12px; color: #0B2545;
}
.tip svg { flex: 0 0 auto; margin-top: 2px; color: #0E7C86; }
.note { display: flex; gap: .8rem; align-items: flex-start; padding: .9rem 1.1rem; border-radius: 14px; margin: .6rem 0; border: 1px solid; }
.note svg { flex: 0 0 auto; margin-top: 2px; }
.note.ok { background: #E6F6EC; border-color: #B7E2C4; color: #14532D; }
.note.warn { background: #FFF4E0; border-color: #F5D79A; color: #7A4B00; }
.note.bad { background: #FDECEC; border-color: #F3B7B7; color: #7F1D1D; }
.note.info { background: #E3F1F3; border-color: #BFE0E4; color: #0B2545; }

/* کارت قطار بعدی */
.next-train {
    display: flex; align-items: center; gap: 1rem; padding: 1.2rem 1.4rem; border-radius: 18px;
    background: linear-gradient(120deg, #0B2545, #0E7C86); box-shadow: 0 8px 24px rgba(11,37,69,.18);
}
.next-train, .next-train * { color: #fff !important; }
.next-train .ic { flex: 0 0 auto; width: 52px; height: 52px; border-radius: 14px; background: rgba(255,255,255,.16); display: flex; align-items: center; justify-content: center; }
.next-train .big { font-size: clamp(1.4rem, 5vw, 2.1rem); font-weight: 800; line-height: 1.4; }
.next-train .sm { font-size: .9rem; opacity: .9; }

/* کارت‌های دسترسی سریع */
[class*="st-key-card_"] {
    background: #fff; border: 1px solid var(--line); border-radius: 16px; padding: .9rem;
    box-shadow: var(--shadow);
    transition: transform .2s ease, box-shadow .2s ease, border-color .2s ease;
}
[class*="st-key-card_"]:hover { transform: translateY(-4px); box-shadow: 0 12px 28px rgba(11,37,69,.16); border-color: #0E7C86; }
.card-img {
    height: 96px; border-radius: 12px; margin-bottom: .7rem; color: #fff;
    background-color: #13466B; background-size: cover; background-position: center;
    display: flex; align-items: center; justify-content: center;
}
.card-title { font-weight: 800; color: var(--navy); font-size: 1.05rem; margin-bottom: .2rem; }
.card-desc { color: var(--muted); font-size: .88rem; margin-bottom: .4rem; }

/* لیست ایستگاه‌ها */
.st-list { display: flex; flex-direction: column; gap: .5rem; }
.st-item { display: flex; align-items: center; gap: .8rem; background: #fff; border: 1px solid var(--line); border-radius: 12px; padding: .6rem .9rem; box-shadow: var(--shadow); color: var(--navy); }
.st-item .n { flex: 0 0 auto; width: 32px; height: 32px; border-radius: 50%; background: var(--teal); color: #fff; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: .85rem; }
.st-item .t { font-weight: 600; }
.st-item .s { font-size: .78rem; color: var(--muted); }
.st-item.sel { border-color: #E03B3B; background: #FFF3F3; }
.st-item.sel .n { background: #E03B3B; }

/* تقویم */
.cal-title { font-size: 1.25rem; font-weight: 800; color: var(--navy); margin: .4rem 0 .6rem 0; }
table.cal { width: 100%; table-layout: fixed; border-collapse: separate; border-spacing: 6px; direction: rtl; }
table.cal th { background: #0B2545; color: #fff; padding: .5rem; border-radius: 8px; text-align: center; font-size: .85rem; }
table.cal td { background: #fff; border: 1px solid var(--line); border-radius: 10px; text-align: center; padding: .5rem .2rem; height: 62px; vertical-align: top; color: #0B2545; }
table.cal td.free { background: linear-gradient(135deg, #0E7C86, #13A3AD); border-color: #0E7C86; color: #fff; font-weight: 700; }
table.cal td.today { outline: 3px solid #F5A623; outline-offset: 1px; }
table.cal td.empty { background: transparent; border: none; }
table.cal td small { display: block; font-size: .65rem; margin-top: 2px; font-weight: 400; }

/* نمودار شلوغی: دو نسخه با ارتفاع متفاوت */
.st-key-chart_mobile { display: none; }

/* منوی میانبر موبایل (فقط در گوشی دیده می‌شود) */
.st-key-topnav { display: none; }

/* تبلت */
@media (min-width: 769px) and (max-width: 1100px) {
    .block-container { padding: 3rem 1.5rem 2rem 1.5rem; }
}

/* موبایل */
@media (max-width: 768px) {
    .block-container { padding: 4rem .8rem 2rem .8rem; }
    input, textarea { font-size: 16px !important; }
    .hero { padding: 1rem 1.1rem; border-radius: 14px; gap: .8rem; }
    .hero.tall { padding: 1.3rem 1.1rem; min-height: 120px; }
    .hero-ic { width: 42px; height: 42px; border-radius: 11px; }
    .hero-art { display: none; }
    .stat { padding: .7rem .8rem; gap: .6rem; }
    .stat-ic { width: 36px; height: 36px; }
    .stat-v { font-size: .98rem; }
    .next-train { padding: 1rem; }
    iframe { max-width: 100%; }
    table.cal { border-spacing: 3px; }
    table.cal th { font-size: .62rem; padding: .35rem .1rem; }
    table.cal td { height: 46px; padding: .3rem .1rem; font-size: .8rem; }
    table.cal td small { font-size: .5rem; }
    .st-key-chart_desktop { display: none; }
    .st-key-chart_mobile { display: block; }

    .st-key-topnav, .st-key-topnav [data-testid="stVerticalBlock"] {
        display: flex !important; flex-direction: row !important; flex-wrap: nowrap !important;
        overflow-x: auto; gap: .4rem; -webkit-overflow-scrolling: touch;
    }
    .st-key-topnav { padding-bottom: .5rem; margin-bottom: .4rem; }
    .st-key-topnav > div, .st-key-topnav [data-testid="stVerticalBlock"] > div { flex: 0 0 auto !important; width: auto !important; }
    .st-key-topnav a {
        white-space: nowrap; background: #fff; border: 1px solid var(--line);
        border-radius: 999px; padding: .35rem .85rem !important; min-height: 40px;
    }

    /* جایگزین ساده برای مرورگرهایی که :has() را پشتیبانی نمی‌کنند: ستون‌ها زیر هم */
    [data-testid="stHorizontalBlock"] { flex-wrap: wrap; }
    [data-testid="stHorizontalBlock"] > [data-testid="column"],
    [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
        min-width: 100% !important;
        flex: 1 1 100% !important;
    }
    /* کارت‌های دسترسی سریع: دوتا در هر ردیف (مرورگرهای جدید) */
    div[data-testid="stHorizontalBlock"]:has([class*="st-key-card_"]) > div {
        min-width: calc(50% - .5rem) !important;
        flex: 1 1 calc(50% - .5rem) !important;
    }
}
</style>
"""

st.markdown(CSS, unsafe_allow_html=True)


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
    n = now_tehran()
    return n.hour * 60 + n.minute + n.second / 60.0


# ----------------------------------------------------------------------
# صفحه ۱: داشبورد
# ----------------------------------------------------------------------
def page_dashboard():
    banner("dashboard", "داشبورد مترو تبریز", "دستیار سفر شما در خط ۱ مترو تبریز", art=True)

    stat_grid([
        ("train", "ایستگاه‌ها", fa(len(STATIONS))),
        ("ruler", "طول خط (کیلومتر)", fa("17.2")),
        ("clock", "ساعت کاری", "%s تا %s" % (hhmm(OPEN_MIN), hhmm(CLOSE_MIN))),
        ("bell", "فاصله قطارها", "%s دقیقه" % fa(HEADWAY)),
    ])

    today = now_tehran().date()
    jy, jm, jd = to_jalali(today)
    wd = (today.weekday() + 2) % 7
    date_txt = "%s %s %s %s" % (WEEKDAYS_FA[wd], fa(jd), JMONTHS[jm - 1], fa(jy))
    if today.weekday() == 1:  # سه‌شنبه
        tip = "امروز سه‌شنبه است؛ مترو برای همه <b>رایگان</b> است!"
    else:
        days_left = (1 - today.weekday()) % 7
        tip = "سه‌شنبه‌ها مترو رایگان است. تا سه‌شنبه‌ی بعد <b>%s روز</b> مانده." % fa(days_left)
    html('<div class="tip">%s<div><b>نکته امروز</b> (%s)<br>%s</div></div>'
         % (icon("gift", 22), date_txt, tip))

    notes = st.session_state.get("announcements", [])
    if notes:
        note("warn", "bell", "<b>اطلاعیه:</b> " + " | ".join(n["text"] for n in notes[-3:]))

    st.subheader("دسترسی سریع")
    cards = [
        ("trip", "برنامه سفر و یادآور", "clock", ":material/schedule:", "زمان قطار بعدی و هشدار حرکت"),
        ("map", "نقشه و ایستگاه‌ها", "map", ":material/map:", "ایستگاه‌های خط ۱ روی نقشه"),
        ("calendar", "تقویم روزهای رایگان", "calendar", ":material/calendar_month:", "سه‌شنبه‌ها مترو رایگان است"),
        ("crowd", "نمودار شلوغی", "chart", ":material/bar_chart:", "ساعات شلوغ و خلوت هر ایستگاه"),
        ("about", "تماس با ما / درباره", "info", ":material/info:", "درباره‌ی پروژه و ثبت نظر"),
    ]
    cols = None
    for i, (key, label, ic, micon, desc) in enumerate(cards):
        if i % 3 == 0:
            cols = st.columns(3)
        with cols[i % 3]:
            with st.container(key="card_" + key):
                img = PAGE_IMAGES.get(key)
                ov = "linear-gradient(135deg, rgba(14,124,134,.55), rgba(11,37,69,.70))"
                if img:
                    cbg = "background-image:%s,url('%s');" % (ov, img)
                else:
                    cbg = "background-image:linear-gradient(135deg,#0E7C86,#0B2545);"
                html('<div class="card-img" style="%s">%s</div><div class="card-title">%s</div>'
                     '<div class="card-desc">%s</div>' % (cbg, icon(ic, 30), label, desc))
                st.page_link(PAGES[key], label="باز کردن", icon=micon)


# ----------------------------------------------------------------------
# صفحه ۲: برنامه سفر و یادآور
# ----------------------------------------------------------------------
def page_trip():
    banner("trip", "برنامه سفر و یادآور", "مبدأ و مقصد را انتخاب کنید و زمان حرکت را بسنجید")

    c1, c2 = st.columns(2)
    origin = c1.selectbox("ایستگاه مبدأ", NAMES, index=0, key="trip_origin")
    dest = c2.selectbox("ایستگاه مقصد", NAMES, index=len(NAMES) - 1, key="trip_dest")

    if origin == dest:
        note("info", "info", "مبدأ و مقصد یکسان است؛ یک مقصد دیگر انتخاب کنید.")
        return

    i, j = NAMES.index(origin), NAMES.index(dest)
    stops = abs(i - j)
    travel = stops * MIN_PER_STOP
    direction = "به سمت %s" % (NAMES[-1] if j > i else NAMES[0])

    stat_grid([
        ("route", "تعداد ایستگاه تا مقصد", fa(stops)),
        ("clock", "زمان تقریبی سفر", "%s دقیقه" % fa(int(round(travel)))),
        ("arrow", "جهت حرکت", direction),
    ])

    st.subheader(":material/train: قطار بعدی")
    now_m = now_minutes()
    dep = next_departure(now_m)
    if dep is None:
        note("bad", "alert", "سرویس امروز به پایان رسیده است. اولین قطار فردا ساعت <b>%s</b> حرکت می‌کند." % hhmm(OPEN_MIN))
    else:
        wait = max(0, math.ceil(dep - now_m))
        big = "همین الان در ایستگاه است" if wait == 0 else "%s دقیقه دیگر" % fa(wait)
        html('<div class="next-train"><div class="ic">%s</div><div><div class="big">%s</div>'
             '<div class="sm">قطار بعدی ساعت %s حرکت می‌کند</div></div></div>'
             % (icon("train", 28), big, hhmm(dep)))

    st.subheader(":material/alarm: یادآور حرکت")
    st.caption("زمانی که می‌خواهید سوار قطار شوید و مدت پیاده‌روی تا ایستگاه را وارد کنید.")
    n = now_tehran()
    d1, d2 = st.columns(2)
    board_t = d1.time_input("زمان سوار شدن", value=dtime(n.hour, n.minute), step=60, key="trip_board_time")
    walk = d2.number_input("پیاده‌روی تا ایستگاه (دقیقه)", min_value=0, max_value=120,
                           value=10, step=1, key="trip_walk")

    board_m = board_t.hour * 60 + board_t.minute
    dep2 = next_departure(board_m)
    if dep2 is None:
        note("bad", "alert", "در این ساعت مترو سرویس نمی‌دهد (ساعت کاری %s تا %s)." % (hhmm(OPEN_MIN), hhmm(CLOSE_MIN)))
        return

    note("info", "train", "قطار مناسب شما ساعت <b>%s</b> حرکت می‌کند و حدود ساعت <b>%s</b> به %s می‌رسید."
         % (hhmm(dep2), hhmm(dep2 + travel), dest))

    leave_in = (dep2 - now_minutes()) - walk
    if leave_in < 0:
        note("bad", "alert", "برای این قطار دیر شده است. قطار بعدی را در نظر بگیرید یا زمان را تغییر دهید.")
    elif leave_in <= 5:
        note("warn", "bell", "هشدار: <b>%s دقیقه دیگر</b> باید حرکت کنید!" % fa(int(math.ceil(leave_in))))
    else:
        note("ok", "check", "می‌توانید <b>%s دقیقه دیگر</b> از جایتان حرکت کنید." % fa(int(math.ceil(leave_in))))


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
        popup_html = (
            '<div style="direction:rtl;text-align:right;font-family:Tahoma,sans-serif;min-width:170px">'
            "<b>%s</b><br>ایستگاه شماره %s از %s<br>ساعت کاری: %s تا %s<br>سه‌شنبه‌ها: رایگان"
            "</div>" % (name, fa(idx + 1), fa(len(STATIONS)), hhmm(OPEN_MIN), hhmm(CLOSE_MIN))
        )
        is_sel = (idx == selected)
        folium.Marker(
            location=[lat, lon],
            tooltip=name,
            popup=folium.Popup(popup_html, max_width=260, show=is_sel),
            icon=folium.Icon(color="red" if is_sel else "blue", icon="train", prefix="fa"),
        ).add_to(m)
    return m


def page_map():
    banner("map", "نقشه خط و ایستگاه‌ها", "ایستگاه را انتخاب کنید یا روی مارکرها بزنید")

    all_label = "همه ایستگاه‌ها"
    choice = st.selectbox("انتخاب ایستگاه", [all_label] + NAMES, key="map_station")
    selected = None if choice == all_label else NAMES.index(choice)

    tab_map, tab_list = st.tabs([":material/map: نقشه", ":material/format_list_numbered: لیست ایستگاه‌ها"])

    with tab_map:
        m = build_map(selected)
        map_key = "metro_map_%s" % ("all" if selected is None else selected)
        try:
            st_folium(m, height=460, use_container_width=True, returned_objects=[], key=map_key)
        except TypeError:
            st_folium(m, height=460, width=900, returned_objects=[], key=map_key)
        st.caption("مختصات ایستگاه‌ها تقریبی است. نمایش نقشه به اینترنت نیاز دارد.")

    with tab_list:
        items = []
        for idx, (name, _, _) in enumerate(STATIONS):
            cls = "st-item sel" if idx == selected else "st-item"
            items.append('<div class="%s"><div class="n">%s</div><div><div class="t">%s</div>'
                         '<div class="s">ساعت کاری %s تا %s</div></div></div>'
                         % (cls, fa(idx + 1), name, hhmm(OPEN_MIN), hhmm(CLOSE_MIN)))
        html('<div class="st-list">%s</div>' % "".join(items))


# ----------------------------------------------------------------------
# صفحه ۴: تقویم شمسی
# ----------------------------------------------------------------------
def page_calendar():
    banner("calendar", "تقویم روزهای رایگان", "سه‌شنبه‌ها مترو تبریز برای همه رایگان است")

    today_j = to_jalali(now_tehran().date())
    c1, c2 = st.columns(2)
    month = c1.selectbox("ماه", list(range(1, 13)), index=today_j[1] - 1,
                         format_func=lambda x: JMONTHS[x - 1], key="cal_month")
    year = c2.number_input("سال (شمسی)", min_value=1300, max_value=1500,
                           value=today_j[0], step=1, key="cal_year")
    year = int(year)

    first = to_gregorian(year, month, 1)
    offset = (first.weekday() + 2) % 7      # شنبه = ۰ ... سه‌شنبه = ۳ ... جمعه = ۶
    length = jalali_month_length(year, month)

    cells = ["<td class='empty'></td>"] * offset
    free_count = 0
    for d in range(1, length + 1):
        col = (offset + d - 1) % 7
        classes, extra = [], ""
        if col == 3:
            classes.append("free")
            extra = "<small>رایگان</small>"
            free_count += 1
        if (year, month, d) == today_j:
            classes.append("today")
        cells.append("<td class='%s'>%s%s</td>" % (" ".join(classes), fa(d), extra))
    while len(cells) % 7:
        cells.append("<td class='empty'></td>")

    rows = "".join("<tr>%s</tr>" % "".join(cells[k:k + 7]) for k in range(0, len(cells), 7))
    head = "<tr>%s</tr>" % "".join("<th>%s</th>" % d for d in WEEKDAYS_FA)
    html('<div class="cal-title">%s %s</div><table class="cal">%s%s</table>'
         % (JMONTHS[month - 1], fa(year), head, rows))
    st.caption("رنگ سبزآبی: سه‌شنبه‌های رایگان | کادر نارنجی: امروز")
    stat_grid([("gift", "سه‌شنبه‌های رایگان این ماه", fa(free_count)),
               ("calendar", "تعداد روزهای ماه", fa(length))])

    st.subheader(":material/campaign: اطلاعیه‌ها")
    if "announcements" not in st.session_state:
        st.session_state["announcements"] = []

    text = st.text_input("متن اطلاعیه (مثلاً: امروز تعطیل رسمی است)", key="ann_text")
    if st.button("افزودن اطلاعیه", type="primary", key="ann_btn"):
        if text.strip():
            st.session_state["announcements"].append(
                {"text": text.strip(), "time": now_tehran().strftime("%H:%M")}
            )
            st.success("اطلاعیه اضافه شد.")
        else:
            st.warning("ابتدا متن اطلاعیه را بنویسید.")

    if st.session_state["announcements"]:
        for n in reversed(st.session_state["announcements"]):
            note("info", "bell", "%s <small>(ساعت %s)</small>" % (n["text"], fa(n["time"])))
        if st.button("پاک کردن همه اطلاعیه‌ها", key="ann_clear"):
            st.session_state["announcements"] = []
            st.rerun()
    else:
        st.caption("هنوز اطلاعیه‌ای ثبت نشده است.")


# ----------------------------------------------------------------------
# صفحه ۵: نمودار شلوغی
# ----------------------------------------------------------------------
BASE_PROFILE = {  # ساعت: میزان شلوغی پایه (۰ تا ۱۰۰)
    6: 35, 7: 75, 8: 95, 9: 70, 10: 45, 11: 35, 12: 30, 13: 28,
    14: 32, 15: 45, 16: 70, 17: 92, 18: 98, 19: 70, 20: 40,
}


def crowd_for(station_index):
    centrality = 1 - abs(station_index - 9.5) / 9.5   # ایستگاه‌های مرکزی شلوغ‌ترند
    factor = 0.75 + 0.35 * centrality
    wobble = ((station_index * 7) % 5 - 2) * 0.02
    return {h: max(5, min(100, round(v * (factor + wobble)))) for h, v in BASE_PROFILE.items()}


def crowd_chart(data, height):
    df = pd.DataFrame({
        "h": [fa(h) for h in data],                     # برچسب محور: فقط ساعت کامل
        "label": [hhmm(h * 60) for h in data],          # برای tooltip
        "v": list(data.values()),
    })
    order = list(df["h"])
    return (
        alt.Chart(df)
        .mark_bar(cornerRadiusTopLeft=5, cornerRadiusTopRight=5)
        .encode(
            x=alt.X("h:O", sort=order, title="ساعت",
                    axis=alt.Axis(labelAngle=0, labelFontSize=12, titleFontSize=12,
                                  labelFont="Vazirmatn, Tahoma, sans-serif",
                                  titleFont="Vazirmatn, Tahoma, sans-serif")),
            y=alt.Y("v:Q", title="شلوغی (٪)", scale=alt.Scale(domain=[0, 100]),
                    axis=alt.Axis(titleFont="Vazirmatn, Tahoma, sans-serif")),
            color=alt.Color("v:Q", legend=None,
                            scale=alt.Scale(domain=[0, 50, 100],
                                            range=["#9FD9DE", "#0E7C86", "#0B2545"])),
            tooltip=[alt.Tooltip("label:N", title="ساعت"), alt.Tooltip("v:Q", title="شلوغی (٪)")],
        )
        .properties(width="container", height=height)
    )


def page_crowd():
    banner("crowd", "نمودار شلوغی", "ساعات شلوغ و خلوت هر ایستگاه در طول روز")
    name = st.selectbox("ایستگاه", NAMES, index=NAMES.index("میدان ساعت"), key="crowd_station")
    data = crowd_for(NAMES.index(name))

    with st.container(key="chart_desktop"):
        st.altair_chart(crowd_chart(data, 380))
    with st.container(key="chart_mobile"):
        st.altair_chart(crowd_chart(data, 260))

    busiest = max(data, key=data.get)
    quietest = min(data, key=data.get)
    avg = round(sum(data.values()) / len(data))
    stat_grid([
        ("chart", "شلوغ‌ترین ساعت", hhmm(busiest * 60)),
        ("clock", "خلوت‌ترین ساعت", hhmm(quietest * 60)),
        ("users", "میانگین شلوغی", "%s٪" % fa(avg)),
    ])
    st.caption("ساعات پیک معمولاً صبح (۷ تا ۹) و عصر (۱۶ تا ۱۹) است. ظهرها خلوت‌تر است. اعداد برآورد تقریبی‌اند.")


# ----------------------------------------------------------------------
# صفحه ۶: تماس با ما / درباره
# ----------------------------------------------------------------------
def page_about():
    banner("about", "تماس با ما / درباره", "درباره‌ی برنامه و تیم سازنده")
    html('<div class="stat-grid"><div class="stat"><div class="stat-ic">%s</div><div>'
         '<div class="stat-l">نام تیم</div><div class="stat-v">%s</div></div></div></div>'
         % (icon("users", 22), TEAM_NAME))
    st.markdown(
        """
**درباره‌ی برنامه:** «دستیار سفر با مترو تبریز» اطلاعات خط ۱ را در یک‌جا جمع می‌کند:
برنامه سفر و یادآور حرکت، نقشه‌ی ایستگاه‌ها، تقویم روزهای رایگان (سه‌شنبه‌ها) و نمودار ساعات شلوغی.
"""
    )
    note("info", "info",
         "اطلاعات این برنامه از منابع عمومی گردآوری شده است. زمان حرکت قطارها، مدت سفر، میزان شلوغی "
         "و موقعیت ایستگاه‌ها تقریبی‌اند و ممکن است با برنامه‌ی رسمی تفاوت داشته باشند. "
         "برای اطلاعات دقیق به سازمان قطار شهری تبریز مراجعه کنید.")

    st.subheader(":material/chat: ثبت نظر")
    with st.form("feedback_form", clear_on_submit=True):
        st.text_input("نام")
        st.text_input("ایمیل")
        st.text_area("نظر یا پیشنهاد شما")
        sent = st.form_submit_button("ارسال")
    if sent:
        st.success("ممنون از نظر شما! (فعلاً نظرها ذخیره نمی‌شوند.)")


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

def mobile_nav():
    """نوار میانبر بالای صفحه؛ فقط در گوشی نمایش داده می‌شود."""
    items = [("dashboard", "داشبورد", ":material/home:"), ("trip", "سفر", ":material/schedule:"),
             ("map", "نقشه", ":material/map:"), ("calendar", "تقویم", ":material/calendar_month:"),
             ("crowd", "شلوغی", ":material/bar_chart:"), ("about", "درباره", ":material/info:")]
    with st.container(key="topnav"):
        for key, label, micon in items:
            st.page_link(PAGES[key], label=label, icon=micon)


pg = st.navigation(list(PAGES.values()))
mobile_nav()
pg.run()
