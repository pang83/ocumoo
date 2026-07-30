import streamlit as st
import pandas as pd
import os
import base64
import textwrap
import re
from datetime import datetime, timedelta, timezone

# ==========================================
# 1. 상수 및 기본 설정
# ==========================================
KST = timezone(timedelta(hours=9))
DATA_FILE = 'coffee_orders.csv'
st.set_page_config(page_title="오커무", page_icon="☕", layout="centered")

# ==========================================
# 2. 데이터 및 에셋 처리 로직
# ==========================================
@st.cache_data
def get_base64_image(image_file):
    try:
        if os.path.exists(image_file):
            with open(image_file, "rb") as f:
                return base64.b64encode(f.read()).decode()
    except Exception:
        pass
    return ""

@st.cache_data(ttl=10)
def load_data():
    if not os.path.exists(DATA_FILE):
        df = pd.DataFrame(columns=['주문일시', '이름', '메뉴', '온도', '옵션'])
        df.to_csv(DATA_FILE, index=False, encoding='utf-8-sig')
        return df
    return pd.read_csv(DATA_FILE, encoding='utf-8-sig')

def save_order(name, menu, temp, option):
    now = datetime.now(KST)
    now_str = now.strftime("%Y-%m-%d %H:%M:%S")
    today_str = now.strftime("%Y-%m-%d")
    
    df = load_data()
    is_upd = False
    if not df.empty:
        mask = (df['이름'] == name) & (df['주문일시'].str[:10] == today_str)
        if mask.any():
            df.loc[df[mask].index[-1], ['주문일시', '메뉴', '온도', '옵션']] = [now_str, menu, temp, option]
            is_upd = True
            
    if not is_upd:
        new_row = pd.DataFrame([{'주문일시': now_str, '이름': name, '메뉴': menu, '온도': temp, '옵션': option}])
        df = pd.concat([df, new_row], ignore_index=True)
    
    df.to_csv(DATA_FILE, index=False, encoding='utf-8-sig')
    load_data.clear()
    return is_upd

def reset_todays_orders():
    df = load_data()
    if not df.empty:
        today_str = datetime.now(KST).strftime("%Y-%m-%d")
        df = df[df['주문일시'].str[:10] != today_str]
        df.to_csv(DATA_FILE, index=False, encoding='utf-8-sig')
        load_data.clear()

# ==========================================
# 3. UI 템플릿 (CSS / JS / HTML)
# ==========================================
JS_TITLE_OBSERVER = """
<script>
    const parentDoc = window.parent.document;
    const applyTitleClick = () => {
        const titleElements = parentDoc.querySelectorAll('h1');
        titleElements.forEach(title => {
            if (title.innerText.includes("오커무") && !title.dataset.hasHomeNav) {
                title.dataset.hasHomeNav = "true";
                title.style.position = "relative";
                title.style.width = "fit-content";
                
                const textNodes = Array.from(title.childNodes).filter(n => n.nodeType === 3 && n.nodeValue.trim() !== "");
                if (textNodes.length > 0) {
                    const span = parentDoc.createElement("span");
                    span.id = "dynamic-app-title";
                    span.innerText = textNodes[0].nodeValue;
                    title.replaceChild(span, textNodes[0]);
                } else if (!parentDoc.getElementById('dynamic-app-title')) {
                    title.innerHTML = `<span id="dynamic-app-title">오커무</span>`;
                }
                
                if (!parentDoc.getElementById('dynamic-back-btn')) {
                    const backBtn = parentDoc.createElement('div');
                    backBtn.id = 'dynamic-back-btn';
                    backBtn.className = 'back-btn';
                    
                    const goHome = (e) => {
                        const tabs = parentDoc.querySelectorAll('[role="tab"]');
                        if (tabs.length > 0) tabs[0].click();
                        e.stopPropagation();
                        if (e.cancelable) e.preventDefault();
                    };
                    backBtn.addEventListener("click", goHome);
                    backBtn.addEventListener("touchend", goHome);
                    title.appendChild(backBtn);
                }
                
                if (!parentDoc.getElementById('dynamic-subtitle')) {
                    const subtitle = parentDoc.createElement('div');
                    subtitle.id = 'dynamic-subtitle';
                    subtitle.className = 'home-subtitle';
                    
                    const divider = parentDoc.createElement('div');
                    divider.className = 'home-subtitle-divider';
                    
                    const textDiv = parentDoc.createElement('div');
                    textDiv.className = 'home-subtitle-text';
                    textDiv.innerHTML = '<span>스마트한</span><span>커피 주문의 시작</span>';
                    
                    subtitle.appendChild(divider);
                    subtitle.appendChild(textDiv);
                    title.appendChild(subtitle);
                }
            }
        });
        
        const tabs = parentDoc.querySelectorAll('[role="tab"]');
        if (tabs.length >= 3) {
            const updateTitle = (index) => {
                const titleSpan = parentDoc.getElementById('dynamic-app-title');
                const mainTitle = parentDoc.querySelector('h1');
                const backBtn = parentDoc.getElementById('dynamic-back-btn');
                const subtitle = parentDoc.getElementById('dynamic-subtitle');
                if (titleSpan && mainTitle) {
                    let targetText = "오커무";
                    let targetWidth = "fit-content";
                    let targetJustify = "flex-start";
                    let targetBackBtn = "none";
                    let targetSubtitle = "flex";
                    
                    if (index === 1) targetText = "주문하기";
                    else if (index === 2) targetText = "내역보기";
                    
                    if (index !== 0) {
                        targetWidth = "100%";
                        targetJustify = "center";
                        targetBackBtn = "block";
                        targetSubtitle = "none";
                    }

                    if (titleSpan.innerText !== targetText) titleSpan.innerText = targetText;
                    if (mainTitle.style.width !== targetWidth) mainTitle.style.width = targetWidth;
                    if (mainTitle.style.justifyContent !== targetJustify) mainTitle.style.justifyContent = targetJustify;
                    if (backBtn && backBtn.style.display !== targetBackBtn) backBtn.style.display = targetBackBtn;
                    if (subtitle && subtitle.style.display !== targetSubtitle) subtitle.style.display = targetSubtitle;
                }
            };

            tabs.forEach((tab, index) => {
                if (tab.getAttribute('aria-selected') === 'true') {
                    updateTitle(index);
                }
                if (!tab.dataset.hasTitleListener) {
                    tab.dataset.hasTitleListener = "true";
                    tab.addEventListener('click', () => updateTitle(index));
                }
            });
        }
    };
    
    if (!parentDoc.body.dataset.badgeObserver) {
        parentDoc.body.dataset.badgeObserver = "true";
        const observer = new MutationObserver(() => applyTitleClick());
        observer.observe(parentDoc.body, { childList: true, subtree: true });
    }
</script>
"""

JS_RESET_OBSERVER = """
<script>
    const parentDoc = window.parent.document;
    if (!parentDoc.getElementById('reset-btn-observer-script')) {
        const script = parentDoc.createElement('script');
        script.id = 'reset-btn-observer-script';
        script.innerHTML = `
            (() => {
                const hideBtn = () => {
                    const buttons = Array.from(document.querySelectorAll('button'));
                    const hiddenBtn = buttons.find(btn => btn.innerText.includes('reset_btn_hidden_12345'));
                    if (hiddenBtn) {
                        const btnContainer = hiddenBtn.closest('div[data-testid="stButton"]');
                        if (btnContainer && btnContainer.style.display !== 'none') {
                            btnContainer.style.display = 'none';
                            btnContainer.style.height = '0px';
                            btnContainer.style.margin = '0px';
                            btnContainer.style.padding = '0px';
                        }
                        
                        const icons = document.querySelectorAll('.reset-icon');
                        icons.forEach(icon => {
                            if (!icon.dataset.hasListener) {
                                icon.dataset.hasListener = "true";
                                icon.addEventListener('click', () => {
                                    if(confirm('주문 내역을 초기화하시겠습니까?')) {
                                        hiddenBtn.click();
                                    }
                                });
                            }
                        });
                    }
                };

                const observer = new MutationObserver((mutations) => hideBtn());
                observer.observe(document.body, { childList: true, subtree: true });
                hideBtn();
            })();
        `;
        parentDoc.head.appendChild(script);
    }
</script>
"""

def get_home_html(person_img, paper_img):
    return f"""
    <style>
    body {{
        margin: 0;
        padding: 0;
        display: flex;
        justify-content: center;
        align-items: center;
        font-family: 'Inter', sans-serif;
        background-color: transparent;
    }}
    .btn-container {{ display: flex; gap: 20px; }}
    .square-btn {{
        width: 160px;
        height: 160px;
        border-radius: 15px;
        border: none;
        font-size: 1.4rem;
        font-weight: 700;
        cursor: pointer;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        gap: 15px;
        background: rgba(255, 255, 255, 0.7);
        color: #6F4E37;
        border: 1px solid #6F4E37;
    }}
    .icon {{
        width: 48px;
        height: 48px;
        background-color: #6F4E37;
        -webkit-mask-size: contain;
        -webkit-mask-position: center;
        -webkit-mask-repeat: no-repeat;
        mask-size: contain;
        mask-position: center;
        mask-repeat: no-repeat;
    }}
    .icon-wrapper {{ position: relative; display: inline-block; }}
    .icon-wrapper[data-badge="true"]::after {{
        content: '';
        position: absolute;
        top: -2px;
        left: 40px;
        width: 6px;
        height: 6px;
        background-color: #FF3B30;
        border-radius: 50%;
        z-index: 10;
    }}
    </style>
    <div class="btn-container">
        <button class="square-btn" onclick="window.parent.document.querySelectorAll('[role=\\'tab\\']')[1].click();">
            <div class="icon" style="-webkit-mask-image: url('data:image/png;base64,{person_img}'); mask-image: url('data:image/png;base64,{person_img}');"></div>
            주문하기
        </button>
        <button class="square-btn" onclick="window.parent.document.querySelectorAll('[role=\\'tab\\']')[2].click();">
            <div class="icon-wrapper" id="history-icon-wrapper">
                <div class="icon" style="-webkit-mask-image: url('data:image/png;base64,{paper_img}'); mask-image: url('data:image/png;base64,{paper_img}');"></div>
            </div>
            내역보기
        </button>
    </div>
    <script>
        const parentDoc = window.parent.document;
        let copyDiv = parentDoc.getElementById('custom-copyright');
        if (!copyDiv) {{
            copyDiv = parentDoc.createElement('div');
            copyDiv.id = 'custom-copyright';
            copyDiv.innerHTML = 'ⓒ 2026 pang83. All rights reserved.';
            copyDiv.style.position = 'absolute'; copyDiv.style.bottom = '20px'; copyDiv.style.left = '0'; copyDiv.style.width = '100%'; copyDiv.style.textAlign = 'center'; copyDiv.style.color = '#888'; copyDiv.style.fontSize = '0.75rem'; copyDiv.style.zIndex = '99'; copyDiv.style.pointerEvents = 'none';
            
            const marker = parentDoc.getElementById('home-bg-marker');
            if (marker) {{
                const tabpanel = marker.closest('div[role="tabpanel"]');
                if (tabpanel) tabpanel.appendChild(copyDiv);
            }}
        }}

        const updateHomeBadge = () => {{
            const countStr = parentDoc.body.dataset.badgeCount || "0";
            const historyIcon = document.getElementById('history-icon-wrapper');
            if (historyIcon) {{
                if (parseInt(countStr, 10) > 0) historyIcon.setAttribute('data-badge', 'true');
                else historyIcon.removeAttribute('data-badge');
            }}
        }};
        
        updateHomeBadge();
        setInterval(updateHomeBadge, 500);
    </script>
    """

@st.cache_data
def get_cached_styles():
    bg_img = get_base64_image('cafe.jpg')
    airplane_icon = get_base64_image('airplane.png')
    receipt_bg = get_base64_image('receipt_paper.jpg')
    back_icon = get_base64_image('back.png')
    
    return f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Libre+Barcode+39&display=swap');
    @font-face {{
        font-family: 'DaeguBukseongro';
        src: url('https://cdn.jsdelivr.net/gh/projectnoonnu/2511-1@1.0/DaeguBukseongro-Light.woff2') format('woff2');
        font-weight: 300;
        font-style: normal;
        font-display: swap;
    }}
    
    .back-btn {{
        display: none;
        width: 25px;
        height: 25px;
        background-color: currentColor;
        -webkit-mask: url("data:image/png;base64,{back_icon}") no-repeat center / contain;
        mask: url("data:image/png;base64,{back_icon}") no-repeat center / contain;
        cursor: pointer;
        position: absolute;
        left: 0;
        top: 50%;
        transform: translateY(-50%);
        z-index: 10000;
    }}
    
    /* 배경 설정 */
    [data-testid="stForm"], div[role="tabpanel"]:has(#home-bg-marker) {{
        position: relative !important;
        z-index: 1 !important;
        background: transparent !important;
        border-radius: 0 !important;
        width: calc(100% + 2rem) !important;
        min-height: calc(100vh - 200px) !important;
        margin-left: -1rem !important;
        border: none !important;
        border-top: 1px solid #D0D1D5 !important;
        box-sizing: border-box !important;
        overflow: hidden !important;
    }}
    div[role="tabpanel"]:has(#home-bg-marker) {{
        min-height: calc(100vh - 200px) !important;
        margin-top: 1rem !important;
        display: flex;
        justify-content: center;
        align-items: center;
    }}
    div[role="tabpanel"]:has(#home-bg-marker)::before {{
        content: "" !important;
        position: absolute !important;
        top: 0 !important;
        left: 0 !important;
        width: 100% !important;
        background-image: linear-gradient(rgba(255, 255, 255, 0.6), rgba(255, 255, 255, 0.6)), url("data:image/jpeg;base64,{bg_img}");
        background-size: cover !important;
        background-position: center !important;
        z-index: -1 !important;
        height: 100% !important;
    }}
    [data-testid="stForm"]::before {{
        content: "" !important;
        position: absolute !important;
        top: 0 !important;
        left: 0 !important;
        width: 100% !important;
        background-color: #F0EDE8 !important;
        z-index: -1 !important;
        height: 100% !important;
    }}
    @media (prefers-color-scheme: dark) {{
        [data-testid="stForm"], div[role="tabpanel"]:has(#home-bg-marker) {{ border-top: 1px solid #333 !important; }}
        [data-testid="stForm"]::before {{ background-color: #1E1E1E !important; }}
        div[role="tabpanel"]:has(#home-bg-marker)::before {{
            background-image: linear-gradient(rgba(0, 0, 0, 0.7), rgba(0, 0, 0, 0.7)), url("data:image/jpeg;base64,{bg_img}");
        }}
    }}

    /* 공통 UI 및 레이아웃 */
    .stButton>button {{ width: 100%; border-radius: 10px; font-weight: bold; }}
    [data-testid="stFormSubmitButton"] {{ width: 100% !important; margin-top: 1rem !important; display: block !important; }}
    [data-testid="stFormSubmitButton"] button {{
        background-color: #333 !important;
        color: white !important;
        border: none !important;
        box-shadow: none !important;
        width: 100% !important;
        height: 50px !important;
        padding: 0 !important;
        border-radius: 5px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
    }}
    [data-testid="stFormSubmitButton"] button div, [data-testid="stFormSubmitButton"] button p {{
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        margin: 0 !important;
    }}
    [data-testid="stFormSubmitButton"] button p {{
        font-size: 1.15rem !important;
        font-weight: 700 !important;
        color: white !important;
        position: relative !important;
    }}
    [data-testid="stFormSubmitButton"] button p::before {{
        content: '' !important;
        display: inline-block !important;
        width: 22px !important;
        height: 22px !important;
        background-color: white !important;
        -webkit-mask: url("data:image/png;base64,{airplane_icon}") no-repeat center / contain;
        mask: url("data:image/png;base64,{airplane_icon}") no-repeat center / contain;
        margin-right: 10px !important;
        opacity: 1 !important;
        flex-shrink: 0 !important;
    }}
    [data-testid="stFormSubmitButton"] button:hover, [data-testid="stFormSubmitButton"] button:active, [data-testid="stFormSubmitButton"] button:focus {{
        background-color: #333 !important;
        box-shadow: none !important;
        color: white !important;
    }}
    
    .block-container {{
        max-width: 500px !important;
        margin: 0 auto !important;
        padding-top: 1.5rem !important;
        padding-bottom: 2rem !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
    }}
    [data-testid="stHeader"], [data-testid="stToolbar"], [data-testid="stDecoration"], footer {{ display: none !important; }}
    html, body, .stApp, section[data-testid="stMain"], div[data-testid="stAppViewContainer"] {{
        overflow-y: scroll !important;
        overflow-x: hidden !important;
        scrollbar-gutter: stable !important;
    }}
    #MainMenu {{ visibility: hidden !important; }}

    /* 타이틀 및 탭 조정 */
    h1 {{
        font-family: 'DaeguBukseongro', sans-serif !important;
        font-weight: 300 !important;
        font-size: 30px !important;
        margin-top: -1.5rem;
        padding-bottom: 0 !important;
        line-height: 40px !important;
        height: 40px !important;
        border-bottom: none !important;
        display: flex;
        align-items: flex-end;
    }}
    .home-subtitle {{ display: flex; align-items: center; margin-left: 12px; height: 40px; padding-bottom: 2px; box-sizing: border-box; }}
    .home-subtitle-divider {{ width: 1px; height: 24px; background-color: #D0D1D5; margin-right: 12px; }}
    .home-subtitle-text {{
        display: flex;
        flex-direction: column;
        justify-content: center;
        font-size: 0.7rem;
        line-height: 1.3;
        color: #888;
        font-family: sans-serif;
        font-weight: 400;
        letter-spacing: -0.2px;
    }}
    @media (prefers-color-scheme: dark) {{ .home-subtitle-divider {{ background-color: #555; }} .home-subtitle-text {{ color: #aaa; }} }}
    [data-testid="stHeadingWithActionElements"] {{ border-bottom: none !important; margin-bottom: 0 !important; }}
    div[data-baseweb="tab-list"], div[data-testid="stTabs"] [role="tablist"] {{
        justify-content: flex-end;
        border-bottom: none !important;
        gap: 0 !important;
        margin-top: 37px !important;
        padding-right: 1px !important;
        visibility: hidden !important;
        pointer-events: none !important;
    }}
    div[data-baseweb="tab-border"], div[data-baseweb="tab-highlight"] {{ display: none !important; background-color: transparent !important; }}
    div[data-testid="stTabs"] {{ margin-top: -75px !important; }}
    div[role="tabpanel"] {{ gap: 0 !important; }}
    [data-testid="stWidgetInstructions"], .stTextInput small, .stTextInput label + div + div {{ display: none !important; }}

    /* 카드 및 리스트 스타일 */
    .order-list-container {{
        margin-left: -1rem;
        margin-right: -1rem;
        background-color: #F0EDE8;
        min-height: calc(100vh - 200px);
        display: flex;
        flex-direction: column;
    }}
    .order-list-header-line {{ border-top: 1px solid #D0D1D5; margin: 0; }}
    .order-card-wrapper {{ margin: 0 -1rem 2px -1rem; }}
    .order-card {{
        background: #ffffff;
        border-radius: 0;
        padding: 16px 1.5rem;
        border: none;
        color: #333;
        width: auto !important;
        box-sizing: border-box !important;
        display: flex;
        justify-content: space-between;
        align-items: center;
        position: relative;
        overflow: hidden;
    }}
    .card-left {{ display: flex; flex-direction: column; gap: 4px; flex: 1; }}
    .card-right {{ display: flex; flex-direction: column; align-items: flex-end; gap: 4px; padding-left: 15px; }}
    .summary-item {{ color: #333; font-size: 1.05rem; margin-bottom: 4px; }}
    .summary-total {{ color: #333; font-size: 1.2rem; }}
    .summary-box-wrapper {{ filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.08)) drop-shadow(0 8px 16px rgba(0, 0, 0, 0.06)); }}
    .summary-box {{
        background-image: url("data:image/jpeg;base64,{receipt_bg}");
        background-size: cover;
        background-position: center top;
        background-color: #ffffff;
        margin: 10px 0;
        border-radius: 4px 4px 0 0;
        padding: 0 1rem 12px 1rem;
        overflow: hidden;
        mask-image: radial-gradient(circle at 10px 100%, transparent 6px, black 6.5px), linear-gradient(black, black);
        mask-size: 20px 10px, 100% calc(100% - 10px);
        mask-repeat: repeat-x, no-repeat;
        mask-position: bottom left, top left;
        -webkit-mask-image: radial-gradient(circle at 10px 100%, transparent 6px, black 6.5px), linear-gradient(black, black);
        -webkit-mask-size: 20px 10px, 100% calc(100% - 10px);
        -webkit-mask-repeat: repeat-x, no-repeat;
        -webkit-mask-position: bottom left, top left;
    }}
    .summary-content {{ padding: 30px 0; }}
    .receipt-date {{ text-align: left; font-size: 0.85rem; margin-bottom: 8px; color: #333; }}
    .reset-icon {{ width: 1.3rem; height: 1.3rem; cursor: pointer; }}

    @media (prefers-color-scheme: dark) {{
        .order-list-container {{ background-color: #1E1E1E; }}
        .order-list-header-line {{ border-top: 1px solid #333; }}
        .order-card {{ background: #2d2d2d; border: none; color: #eee; }}
        .summary-item, .summary-total, .receipt-date {{ color: #eee; }}
        .summary-box-wrapper {{ filter: drop-shadow(0 2px 6px rgba(0, 0, 0, 0.4)) drop-shadow(0 10px 20px rgba(0, 0, 0, 0.25)); }}
        .summary-box {{
            background-image: linear-gradient(rgba(0, 0, 0, 0.6), rgba(0, 0, 0, 0.6)), url("data:image/jpeg;base64,{receipt_bg}");
            background-color: #262626;
        }}
        div[data-baseweb="tab-list"] button[data-baseweb="tab"] {{ filter: invert(1); }}
        .order-no {{ color: #aaa; }}
        .order-time {{ color: #888; }}
        .reset-icon {{ filter: invert(1); opacity: 0.8; }}
        .order-info {{ color: #aaa; }}
    }}
    .order-no {{ font-size: 0.65rem; font-weight: 800; color: #888; letter-spacing: 0.5px; opacity: 0.8; }}
    .order-name {{ font-size: 1.15rem; font-weight: 700; line-height: 1.2; }}
    .order-time {{ font-size: 0.75rem; color: #999; }}
    .order-info {{ font-size: 0.9rem; line-height: 1.4; color: #666; }}
    .order-card .card-left, .order-card .card-right {{ position: relative; z-index: 1; }}
    
    /* Input & Pills 스타일 통일 */
    [data-testid="stPills"], [data-testid="stButtonGroup"], [data-testid="stTextInput"] {{
        display: flex !important;
        flex-direction: column !important;
        align-items: flex-start !important;
        gap: 5px !important;
        margin-bottom: 13px !important;
    }}
    [data-testid="stPills"] > label, [data-testid="stButtonGroup"] > label, [data-testid="stTextInput"] > label {{
        font-size: 0.9rem !important;
        font-weight: normal !important;
        margin-bottom: 0 !important;
        color: #333 !important;
    }}
    [data-testid="stPills"] > div, [data-testid="stButtonGroup"] > div, [data-testid="stTextInput"] > div {{ width: 100% !important; }}
    .stTextInput label p, .stTextInput label div {{
        font-size: 0.9rem !important;
        font-weight: normal !important;
        color: #333 !important;
        margin: 0 !important;
    }}
    
    button[data-variant="pills"], button[data-variant="pills"]:hover, button[data-variant="pills"]:focus {{
        border: 1px solid #6F4E37 !important;
        color: #6F4E37 !important;
        background-color: #ffffff !important;
        min-height: 37px !important;
    }}
    button[data-variant="pills"] p, button[data-variant="pills"]:hover p, button[data-variant="pills"]:focus p {{ color: #6F4E37 !important; }}
    button[data-variant="pills"][aria-checked="true"], button[data-variant="pills"][aria-pressed="true"], button[data-variant="pills"][aria-checked="true"]:hover, button[data-variant="pills"][aria-pressed="true"]:hover {{
        background-color: #6F4E37 !important;
        border: 1px solid #6F4E37 !important;
        color: white !important;
        font-weight: bold !important;
        min-height: 37px !important;
    }}
    button[data-variant="pills"][aria-checked="true"] p, button[data-variant="pills"][aria-pressed="true"] p, button[data-variant="pills"][aria-checked="true"]:hover p, button[data-variant="pills"][aria-pressed="true"]:hover p {{
        color: white !important;
        font-weight: bold !important;
    }}
    
    .stTextInput div[data-testid="stTextInputRootElement"] {{ background-color: #ffffff !important; }}
    .stTextInput div[data-testid="stTextInputRootElement"]:focus-within {{ border-color: #6F4E37 !important; background-color: #ffffff !important; }}
    .stTextInput input {{ font-size: 16px !important; }}

    @media (prefers-color-scheme: dark) {{
        [data-testid="stPills"] > label, [data-testid="stButtonGroup"] > label, .stTextInput label p, .stTextInput label div {{
            color: #ccc !important;
        }}
        .stTextInput div[data-testid="stTextInputRootElement"] {{
            background-color: rgba(0, 0, 0, 0.5) !important;
            border-color: rgba(255, 255, 255, 0.2) !important;
        }}
        .stTextInput div[data-testid="stTextInputRootElement"]:focus-within {{
            background-color: rgba(0, 0, 0, 0.7) !important;
            border-color: #A0836D !important;
        }}
        button[data-variant="pills"], button[data-variant="pills"]:hover, button[data-variant="pills"]:focus {{
            background-color: rgba(0, 0, 0, 0.5) !important;
            border-color: rgba(255, 255, 255, 0.2) !important;
        }}
        button[data-variant="pills"] p, button[data-variant="pills"]:hover p, button[data-variant="pills"]:focus p {{ color: #ccc !important; }}
    }}
    </style>
    """

# ==========================================
# 4. 핵심 UI 컴포넌트
# ==========================================
@st.fragment(run_every=timedelta(seconds=10))
def show_orders():
    df = load_data()
    
    html_start = textwrap.dedent('''
        <div class="order-list-container">
            <div class="order-list-header-line"></div>
            <div style="flex: 1; padding: 0 1rem 0 1rem; display: flex; flex-direction: column;">
    ''')
    
    html_end = textwrap.dedent('''
            </div>
        </div>
    ''')
    
    empty_msg = textwrap.dedent('''
        <div style="flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: flex-start; text-align: center; color: #888; padding-top: 15vh;">
            <div style="font-size: 3rem; margin-bottom: 10px;">😴</div>
            <div style="font-size: 1.1rem; font-weight: normal;">아직 접수된 주문이 없어요!</div>
        </div>
    ''')

    today = datetime.now(KST)
    today_str = today.strftime("%Y-%m-%d")
    today_df = df[df['주문일시'].str[:10] == today_str].copy()
    
    if df.empty or today_df.empty:
        st.markdown(re.sub(r'\n\s+', '', html_start + empty_msg + html_end), unsafe_allow_html=True)
        st.iframe(f'<script>window.parent.document.body.dataset.badgeCount = "{len(today_df)}";</script>', height=1)
        return
    
    today_df['주문일시_dt'] = pd.to_datetime(today_df['주문일시'])
    temp_map = {'핫': 'H)', '아이스': 'I)'}
    opt_map = {'연하게': '-1샷', '샷 추가': '+1샷', '사이즈 업': 'UP', '디카페인': 'Decaf', '두유로 변경': '두유'}
    
    def format_summary(r):
        base = f"{temp_map.get(r['온도'], r['온도'])} {r['메뉴']}"
        if pd.isna(r['옵션']) or str(r['옵션']).strip() == '': return base
        opts = [opt_map.get(o.strip(), o.strip()) for o in str(r['옵션']).split(',')]
        return f"{base}, {', '.join(opts)}"
        
    today_df['주문요약'] = today_df.apply(format_summary, axis=1)
    summary_df = today_df.groupby('주문요약').size().reset_index(name='수량').sort_values('수량', ascending=False)

    summary_items_html = "".join([
        textwrap.dedent(f'''
        <div class="summary-item" style="display: flex; justify-content: space-between; align-items: center;">
            <span>{row["주문요약"]}</span>
            <span>{row["수량"]}</span>
        </div>
        ''') for _, row in summary_df.iterrows()
    ])
    
    total_qty = summary_df['수량'].sum()
    barcode = f"{today.strftime('%Y%m%d')}{total_qty:04d}"
    
    body_html = textwrap.dedent(f'''
        <div class="summary-box-wrapper" style="margin-bottom: 30px; margin-top: 28px;">
            <div class="summary-box">
                <div class="summary-content">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                        <div class="receipt-date" style="margin-bottom: 0;">{today.strftime('%Y-%m-%d(%a)')}</div>
                        <img src="data:image/png;base64,{get_base64_image('reset.png')}" class="reset-icon" />
                    </div>
                    <hr style="border: 0; border-top: 1px dashed #ccc; margin: 0 0 12px 0;">
                    <div class="summary-items-container">{summary_items_html}</div>
                    <hr style="border: 0; border-top: 1px dashed #ccc; margin: 15px 0;">
                    <div class="summary-total" style="display: flex; justify-content: space-between; font-weight: bold;">
                        <span style="background: linear-gradient(to top, rgba(255, 255, 0, 0.4) 50%, transparent 50%); padding: 0 4px;">수량</span>
                        <span style="background: linear-gradient(to top, rgba(255, 255, 0, 0.4) 50%, transparent 50%); padding: 0 4px;">{total_qty}개</span>
                    </div>
                    <hr style="border: 0; border-top: 1px dashed #ccc; margin: 15px 0 10px 0;">
                    <div style="text-align: center; display: flex; flex-direction: column; align-items: center; margin-bottom: 5px; width: 100%; overflow: hidden;">
                        <div style="font-family: 'Libre Barcode 39', cursive; font-size: 2.2rem; transform: scaleY(1.4); transform-origin: top; line-height: 1; font-weight: normal; color: #333; margin-bottom: 6px; white-space: nowrap;">*{barcode}*</div>
                        <div style="font-size: 0.75rem; color: #888; letter-spacing: 4px;">{barcode}</div>
                    </div>
                </div>
            </div>
        </div>
    ''')
    
    today_sorted = today_df.sort_values('주문일시').copy()
    today_sorted['연번'] = range(1, len(today_sorted) + 1)
    today_sorted['주문시간_str'] = today_sorted['주문일시_dt'].dt.strftime('%H:%M:%S')
    
    cards_list = []
    for _, row in today_sorted.iterrows():
        opts = str(row['옵션']).strip() if pd.notna(row['옵션']) else ""
        info_text = f"{row['온도']} {row['메뉴']}" + (f" · {opts.replace(', ', ' · ')}" if opts else "")
        cards_list.append(textwrap.dedent(f'''
            <div class="order-card-wrapper">
                <div class="order-card">
                    <div class="card-left">
                        <div class="order-name">{row["이름"]}</div>
                        <div class="order-info">{info_text}</div>
                    </div>
                    <div class="card-right">
                        <div class="order-no">ORDER #{row["연번"]:02d}</div>
                        <div class="order-time">{row["주문시간_str"]}</div>
                    </div>
                </div>
            </div>
        '''))
    
    st.markdown(re.sub(r'\n\s+', '', html_start + body_html + "".join(cards_list) + html_end), unsafe_allow_html=True)
    st.iframe(f'<script>window.parent.document.body.dataset.badgeCount = "{len(today_df)}";</script>', height=1)
    st.iframe(JS_RESET_OBSERVER, height=1)
    
    if st.button("reset_btn_hidden_12345"):
        reset_todays_orders()
        st.rerun()

# ==========================================
# 5. 메인 애플리케이션
# ==========================================
def main():
    st.markdown(get_cached_styles(), unsafe_allow_html=True)
    st.iframe(JS_TITLE_OBSERVER, height=1)
    
    st.title("오커무", anchor=False)
    tab_home, tab1, tab2 = st.tabs(["홈", "주문하기", "내역보기"])
    
    with tab_home:
        st.markdown('<div id="home-bg-marker"></div>', unsafe_allow_html=True)
        st.iframe(get_home_html(get_base64_image("person.png"), get_base64_image("paper.png")), height=250)

    with tab1:
        with st.form("order_form", clear_on_submit=True):
            name = st.text_input("이름 :red[*]", placeholder="이름을 입력하세요.")
            menu = st.text_input("메뉴 :red[*]", placeholder="예) 아메리카노, 카페라떼")        
            temp = st.pills("음료 온도 :red[*]", ["핫", "아이스"], selection_mode="single", label_visibility="visible")
            option = st.pills("선택 항목", ["산미", "연하게", "샷 추가", "사이즈 업", "디카페인", "두유로 변경"], selection_mode="multi", label_visibility="visible")
            submitted = st.form_submit_button("제출하기", use_container_width=True)

        if submitted:
            now_ts = datetime.now().timestamp()
            if not name.strip() or not menu.strip() or not temp:
                st.iframe(f'<script>/* {now_ts} */ alert("이름, 메뉴, 음료 온도는 필수 항목입니다.");</script>', height=1)
            else:
                is_upd = save_order(name, menu.strip(), temp if temp else "", ", ".join(option) if option else "")
                msg = "주문이 성공적으로 업데이트되었습니다!" if is_upd else "주문이 성공적으로 접수되었습니다!"
                st.iframe(f'<script>/* {now_ts} */ alert("{msg}");</script>', height=1)

    with tab2:
        show_orders()

if __name__ == "__main__":
    main()
