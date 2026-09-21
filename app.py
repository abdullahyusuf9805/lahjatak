import os
import subprocess

def setup_camel_tools():
    try:
        from camel_tools.morphology.database import MorphologyDB
        _ = MorphologyDB.builtin_db()
        print("Camel tools data already installed.")
    except Exception:
        print("Camel tools data missing. Downloading now...")
        try:
            subprocess.run(['camel_data', '-i', 'morphology-db-msa-r13'], check=True)
            print("Download complete.")
        except subprocess.CalledProcessError as e:
            print(f"Failed to download camel data: {e}")

setup_camel_tools()

import streamlit as st
import nlp_engine
import pandas as pd
import re
import base64
import time

# دالة لقراءة صورة من مجلد المشروع وتحويلها لنص Base64
def get_img_as_base64(file_path):
    try:
        with open(file_path, "rb") as f:
            data = f.read()
        return base64.b64encode(data).decode()
    except Exception as e:
        print(f"Error loading image: {e}")
        return ""

send_icon = get_img_as_base64("send.png")

# قراءة البيانات
@st.cache_data
def load_data():
    return nlp_engine.load_lexicon()

lexicon_df = load_data()

st.set_page_config(page_title="برنامج لهجتك", layout="centered", page_icon="icon.png", initial_sidebar_state="collapsed")

# إخفاء عناصر Streamlit الافتراضية (الشريط العلوي، الفوتر، وعلامات الربط)
hide_st_style = """
            <style>
            /* إخفاء الشريط العلوي بالكامل (GitHub, Share...) */
            header {visibility: hidden;}
            
            /* إخفاء الفوتر الافتراضي */
            footer {visibility: hidden;}
            
            /* إخفاء أيقونة الرابط 🔗 بجانب العناوين (طريقة شاملة وصارمة) */
            h1 a, h2 a, h3 a, h4 a, h5 a, h6 a {
                display: none !important;
                pointer-events: none !important;
            }
            
            /* استهداف حاوية الأيقونة في الإصدارات الحديثة من Streamlit */
            [data-testid="StyledLinkIconContainer"] {
                display: none !important;
            }
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

st.markdown(f"""
    <style>
    /* =========================================
       1. الخطوط والإعدادات العامة
       ========================================= */
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Arabic:wght@400;500;600;700&display=swap');
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400&display=swap');

    html, body, [class*="st-"] {{
        font-family: 'IBM Plex Sans Arabic', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
    }}

    [data-testid="stAppViewContainer"] {{
        direction: rtl;
        background-color: #0e0e0e;
        color: white;
    }}
    
    .block-container {{
        direction: rtl !important;
        text-align: right !important;
        padding-top: 1.5rem !important; 
    }}

    h1 {{
        text-align: right !important;
        margin-top: 0 !important; 
        padding-top: 0 !important;
        margin-right: 5px !important; 
        margin-bottom: 20px !important; 
        font-weight: 700;
        color: #272730 !important;
    }}

    h3 {{
        text-align: right !important;
        direction: rtl !important;
        width: 100% !important;
    }}

    /* =========================================
       2. تصميم مربع الإدخال والزر والقائمة المنسدلة
       ========================================= */
    div[data-testid="stTextInput"] label, div[data-testid="stSelectbox"] label {{
        display: flex !important;
        justify-content: flex-start !important;
        color: #ffffff !important;
        font-size: 15px !important;
        margin-bottom: 10px !important;
    }}

    /* إزالة الإطار الأحمر نهائياً */
    div[data-baseweb="input"] {{
        background-color: #272730 !important; 
        border-radius: 12px !important;
        border: none !important;
        box-shadow: none !important; 
        outline: none !important;
    }}

    div[data-baseweb="input"]:focus-within,
    div[data-baseweb="input"]:focus,
    div[data-baseweb="input"]:active {{
        border: none !important;
        box-shadow: none !important; 
        outline: none !important;
    }}

    div[data-baseweb="input"] input {{
        direction: rtl !important;
        text-align: right !important;
        font-size: 18px !important;
        padding: 16px 16px 16px 65px !important;
        color: white !important;
        background-color: transparent !important;
    }}

    /* إخفاء جملة Press Enter to apply */
    div[data-testid="InputInstructions"], 
    div[data-testid="stTextInputInstructions"],
    div[data-testid="stTextInput"] small {{
        display: none !important;
        visibility: hidden !important;
    }}

    /* تصميم القائمة المنسدلة */
    div[data-baseweb="select"] > div {{
        background-color: #272730 !important; 
        border-radius: 12px !important;
        border: none !important;
        cursor: pointer;
        padding: 5px !important;
    }}
    
    div[data-baseweb="select"] span {{
        color: white !important;
        font-size: 16px !important;
    }}

    /* الحاوية الخاصة بزر الإرسال */
    div[data-testid="stButton"] {{
        margin-top: -51.5px !important; 
        width: 100% !important;
        display: flex !important;
        direction: ltr !important; 
        justify-content: flex-start !important; 
        padding-left: 5px !important; 
        z-index: 50 !important;
        pointer-events: none !important; 
    }}

    /* تخصيص زر الإرسال بصورة PNG الخاصة بك */
    div[data-testid="stButton"] button {{
        pointer-events: auto !important; 
        color: transparent !important; 
        background-color: transparent !important; 
        border: none !important;
        border-radius: 50% !important;
        
        background-image: url('data:image/png;base64,{send_icon}') !important;
        background-size: contain !important; 
        background-position: center !important;
        background-repeat: no-repeat !important;

        width: 32px !important;    
        height: 32px !important;    
        min-height: 32px !important;
        max-width: 32px !important;
        flex: 0 0 32px !important; 
        padding: 0 !important;
        display: flex !important;
        justify-content: center !important;
        align-items: center !important;
        transition: transform 0.2s ease !important;
    }}

    div[data-testid="stButton"] button p {{
        display: none !important; 
    }}

    div[data-testid="stButton"] button:hover {{
        transform: scale(1.1) !important; 
        background-color: transparent !important; 
        border-color: transparent !important;
    }}

    /* تخصيص الـ spinner ليحل محل زر الإرسال تماماً */
    .spinner-replacement {{
        margin-top: -51.5px !important;
        width: 32px !important;
        height: 32px !important;
        display: flex;
        align-items: center;
        justify-content: center;
        margin-left: 5px;
        z-index: 50;
        direction: ltr;
    }}

    /* =========================================
       3. بطاقات الترجمة وقسم "لماذا؟"
       ========================================= */
    .translation-box {{
        background: linear-gradient(145deg, #1c1c1c, #141414);
        border: 1px solid #2a2a2a;
        box-shadow: 0 10px 30px rgba(0,0,0,0.5);
        border-radius: 16px;
        padding: 25px;
        margin-bottom: 25px;
        direction: rtl !important;
    }}
    
    .fusha-section {{
        text-align: center;
        padding-bottom: 20px;
        border-bottom: 1px dashed #333;
        margin-bottom: 20px;
    }}
    
    .fusha-label {{ font-size: 14px; color: #888; margin-bottom: 10px; }}
    .fusha-text {{ font-size: 22px; color: #ffffff; font-weight: 600; }}

    .dialect-card {{
        background-color: #222222;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 15px;
        border-right: 4px solid #4CAF50 !important;
        border-left: none !important;
        display: flex;
        flex-direction: column;
        align-items: flex-start; 
        transition: transform 0.3s ease, box-shadow 0.3s ease !important;
    }}
    
    .dialect-card:hover {{
        transform: translateX(-6px) !important; 
        box-shadow: 0 8px 25px rgba(76, 175, 80, 0.15) !important; 
    }}
    
    .dialect-badge {{
        background-color: rgba(76, 175, 80, 0.15);
        color: #4CAF50;
        padding: 6px 14px;
        border-radius: 20px;
        font-size: 13px;
        font-weight: 700;
        display: flex;
        align-items: center;
        gap: 8px;
    }}
    
    .dialect-text {{
        font-size: 26px;
        color: #4CAF50;
        font-weight: 700;
        width: 100%;
        text-align: right;
    }}
    
    .pronunciation-wrapper {{ width: 100%; margin-top: 5px; text-align: right; }}
    .pronunciation-text {{
        display: inline-block;
        background-color: #111111;
        border: 1px solid #333;
        padding: 8px 15px;
        border-radius: 8px;
        font-size: 15px;
        color: #a0a0a0;
        font-family: 'JetBrains Mono', monospace !important; 
        box-shadow: inset 0 2px 4px rgba(0,0,0,0.5);
    }}
    
    .timeline-container {{
        background-color: #1c1c1c;
        border: 1px solid #2a2a2a;
        border-radius: 12px; 
        padding: 25px;
        direction: rtl !important;
        text-align: right !important;
    }}
    
    .timeline-step {{ display: flex; align-items: center; margin-bottom: 15px; font-size: 16px; color: #e0e0e0; }}
    .circle {{
        border: 2px solid #4CAF50; background-color: rgba(76, 175, 80, 0.1); color: #4CAF50;
        border-radius: 50%; min-width: 35px; height: 35px; display: flex; justify-content: center;
        align-items: center; margin-left: 15px !important; margin-right: 0 !important; font-weight: 700;
    }}

    .highlight-green {{
        color: #4CAF50; font-weight: 700; background-color: rgba(76, 175, 80, 0.15);
        padding: 2px 8px; border-radius: 6px; margin: 0 4px; display: inline-block;
    }}

    /* =========================================
       4. تصميم الزر المزدوج
       ========================================= */
    div[data-testid="stRadio"] > label {{
        display: none !important;
        visibility: hidden !important;
    }}

    div[role="radiogroup"] {{
        background-color: #1a1a1f !important;
        border-radius: 12px !important;
        padding: 6px !important;
        display: flex !important;
        width: 100% !important;
        gap: 8px !important;
        margin-bottom: 25px !important;
        direction: rtl !important;
    }}

    div[role="radiogroup"] label {{
        flex: 1 !important;
        background-color: transparent !important;
        border-radius: 8px !important;
        padding: 10px !important;
        margin: 0 !important;
        cursor: pointer !important;
        transition: all 0.3s ease !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
    }}

    div[role="radiogroup"] label:has(input:checked) {{
        background-color: #272730 !important;
        box-shadow: 0 4px 10px rgba(0,0,0,0.3) !important;
    }}

    div[role="radiogroup"] label p {{
        font-size: 16px !important;
        font-weight: 600 !important;
        color: #888888 !important;
        margin: 0 !important;
    }}

    div[role="radiogroup"] label:has(input:checked) p {{
        color: #4CAF50 !important;
    }}
    </style>
""", unsafe_allow_html=True)

# =====================================================================
# واجهة المستخدم 
# =====================================================================
st.title("برنامج لهجتك")

translation_dir = st.radio(
    label="اتجاه الترجمة",
    options=[
        "من اللهجة العامية إلى اللغة الفصحى", 
        "من اللغة الفصحى إلى اللهجة العامية"
    ],
    horizontal=True,
    label_visibility="collapsed"
)

if translation_dir == "من اللغة الفصحى إلى اللهجة العامية":
    col_input, col_dropdown = st.columns([3, 1.2])
    with col_dropdown:
        dialect_choice = st.selectbox(
            "اختر اللهجة",
            ["اللهجات السعودية", "اللهجة الحجازية", "اللهجة النجدية"]
        )
else:
    col_input = st.container() 
    dialect_choice = "اللهجات السعودية"

with col_input:
    if translation_dir == "من اللغة الفصحى إلى اللهجة العامية":
        input_placeholder = "مثال: ماذا تفعل؟"
        input_label = "اكتب العبارة بالعربية الفصحى"
    else:
        input_placeholder = "مثال: إيش تسوي؟"
        input_label = "اكتب العبارة باللهجة العامية"
        
    text_input = st.text_input(input_label, placeholder=input_placeholder)
    
    # استخدام placeholder للزر لاستبداله بـ spinner عند الضغط
    btn_placeholder = st.empty()
    translate_clicked = btn_placeholder.button("←", use_container_width=True)

def build_dialect_card(sentences, caphis, badge, title, icon):
    header = (
        "<div style='display: flex; justify-content: space-between; align-items: center; width: 100%; margin-bottom: 15px;'>"
        f"<div class='dialect-badge' style='margin-bottom: 0;'>{icon} {title}</div>"
        f"{badge}"
        "</div>"
    )
    
    content = ""
    for i in range(len(sentences)):
        prefix = f"<span style='color: #4CAF50; font-size: 18px; margin-left: 5px;'>{i+1}-</span> " if len(sentences) > 1 else ""
        content += f"<div class='dialect-text' style='margin-bottom: 5px;'>{prefix}{sentences[i]}</div>"
        
        if i < len(caphis) and caphis[i]:
            content += f"<div class='pronunciation-wrapper' style='margin-bottom: 18px;'><div class='pronunciation-text'>🗣️ <span dir='ltr'>[{caphis[i]}]</span></div></div>"
    
    return f"<div class='dialect-card'>{header}{content}</div>"

def build_fusha_card(sentences):
    header = (
        "<div style='display: flex; justify-content: space-between; align-items: center; width: 100%; margin-bottom: 15px;'>"
        "<div class='dialect-badge' style='margin-bottom: 0;'>📖 العربية الفصحى</div>"
        "</div>"
    )
    content = ""
    for i in range(len(sentences)):
        prefix = f"<span style='color: #4CAF50; font-size: 18px; margin-left: 5px;'>{i+1}-</span> " if len(sentences) > 1 else ""
        content += f"<div class='dialect-text' style='margin-bottom: 15px;'>{prefix}{sentences[i]}</div>"
    return f"<div class='dialect-card'>{header}{content}</div>"

# =====================================================================
# النتائج وعرضها مع استبدال الزر بـ spinner عند الضغط
# =====================================================================

if translate_clicked or text_input:
    if text_input:
        # استبدال زر الإرسال بـ spinner في نفس مكانه تماماً أثناء المعالجة
        with btn_placeholder.container():
            st.markdown(
                '<div class="spinner-replacement"><div style="width:20px; height:20px; border:2px solid #4CAF50; border-top:2px solid transparent; border-radius:50%; animation: spin 0.8s linear infinite;"></div></div>'
                '<style>@keyframes spin {{ 0% {{ transform: rotate(0deg); }} 100% {{ transform: rotate(360deg); }} }}</style>',
                unsafe_allow_html=True
            )

        if translation_dir == "من اللغة الفصحى إلى اللهجة العامية":
            result = nlp_engine.process_fusha(text_input, lexicon_df, dialect_choice)
            
            hejazi_card = build_dialect_card(result['hejazi_sentences'], result['hejazi_caphis'], result['hejazi_badge'], "اللهجة الحجازية", "🌴")
            najdi_card = build_dialect_card(result['najdi_sentences'], result['najdi_caphis'], result['najdi_badge'], "اللهجة النجدية", "🐪")

            cards_html = ""
            if dialect_choice == "اللهجات السعودية":
                cards_html = hejazi_card + najdi_card
            elif dialect_choice == "اللهجة الحجازية":
                cards_html = hejazi_card
            elif dialect_choice == "اللهجة النجدية":
                cards_html = najdi_card
                
            original_label = "العبارة الأصلية (فصحى)"

        else: 
            result = nlp_engine.process_ammiya(text_input, lexicon_df, dialect_choice)
                
            cards_html = build_fusha_card(result['fusha_sentences'])
            original_label = "العبارة الأصلية (عامية)"

        # إعادة زر الإرسال الطبيعي بعد انتهاء المعالجة داخل الـ placeholder
        with btn_placeholder:
            st.button("←", use_container_width=True, key="send_btn_after")

        html_box = (
            "<div class='translation-box'>"
            "<div class='fusha-section'>"
            f"<div class='fusha-label'>{original_label}</div>"
            f"<div class='fusha-text'>{text_input}</div>"
            "</div>"
            f"{cards_html}"
            "</div>"
        )
        st.markdown(html_box, unsafe_allow_html=True)
        
        st.markdown("### لماذا؟")
        if result['timeline']:
            timeline_html = "<div class='timeline-container'>"
            for i, step in enumerate(result['timeline']):
                step_cleaned = re.sub(r'ل\+', 'لِـ', step)
                step_cleaned = re.sub(r'([أ-ي])\+', r'_', step_cleaned)
                step_formatted = re.sub(r'\(\((.*?)\)\)', r"<span class='highlight-green'>\1</span>", step_cleaned)
                
                timeline_html += (
                    "<div class='timeline-step'>"
                    f"<div class='circle'>{i+1}</div>"
                    f"<div>{step_formatted}</div>"
                    "</div>"
                )
            timeline_html += "</div>"
            st.markdown(timeline_html, unsafe_allow_html=True)
        else:
            st.info("لا توجد تغييرات معجمية لهذه العبارة.")
    else:
        st.warning("الرجاء إدخال نص صحيح أولاً.")
