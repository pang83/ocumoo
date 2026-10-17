import streamlit as st
import pandas as pd
import os
import textwrap
import re
from datetime import datetime, timedelta, timezone
import socket

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return '127.0.0.1'

# ==========================================
# 1. 상수 및 기본 설정
# ==========================================
KST = timezone(timedelta(hours=9))
DATA_FILE = 'coffee_orders.csv'
st.set_page_config(page_title="오커무", page_icon="☕", layout="centered")

# ==========================================
# 2. 데이터 처리 로직
# ==========================================

@st.cache_data(ttl=10)
def load_data():
    if not os.path.exists(DATA_FILE):
        df = pd.DataFrame(columns=['주문일시', '이름', '메뉴', '온도', '옵션', '수정여부'])
        df.to_csv(DATA_FILE, index=False, encoding='utf-8-sig')
        return df
    df = pd.read_csv(DATA_FILE, encoding='utf-8-sig')
    if '수정여부' not in df.columns:
        df['수정여부'] = False
    return df

def save_order(name, menu, temp, option):
    now = datetime.now(KST)
    now_str = now.strftime("%Y-%m-%d %H:%M:%S")
    today_str = now.strftime("%Y-%m-%d")
    
    df = load_data()
    is_upd = False
    if not df.empty:
        mask = (df['이름'] == name) & (df['주문일시'].str[:10] == today_str)
        if mask.any():
            df.loc[df[mask].index[-1], ['주문일시', '메뉴', '온도', '옵션', '수정여부']] = [now_str, menu, temp, option, True]
            is_upd = True
            
    if not is_upd:
        new_row = pd.DataFrame([{'주문일시': now_str, '이름': name, '메뉴': menu, '온도': temp, '옵션': option, '수정여부': False}])
        df = pd.concat([df, new_row], ignore_index=True)
    
    df.to_csv(DATA_FILE, index=False, encoding='utf-8-sig')
    load_data.clear()
    return is_upd

# ==========================================
# 3. UI 템플릿 (CSS / JS / HTML)
# ==========================================
JS_APP_OBSERVER = """
<script>
    const parentDoc = window.parent.document;
    const hideButtons = () => {
        const buttons = Array.from(parentDoc.querySelectorAll('button'));
        
        ['hidden_order_btn_12345', 'hidden_history_btn_12345'].forEach(btnText => {
            const hiddenBtn = buttons.find(b => b.innerText.includes(btnText));
            if (hiddenBtn) {
                const btnContainer = hiddenBtn.closest('div[data-testid="stButton"]');
                if (btnContainer && btnContainer.style.display !== 'none') {
                    btnContainer.style.display = 'none';
                    btnContainer.style.height = '0px';
                    btnContainer.style.margin = '0px';
                    btnContainer.style.padding = '0px';
                }
            }
        });
    };
    
    if (!parentDoc.body.dataset.appObserver) {
        parentDoc.body.dataset.appObserver = "true";
        const observer = new MutationObserver(() => hideButtons());
        observer.observe(parentDoc.body, { childList: true, subtree: true });
        
        const urlParams = new URLSearchParams(window.parent.location.search);
        if (urlParams.get('tab') === 'order') {
            const checkBtns = setInterval(() => {
                const buttons = Array.from(parentDoc.querySelectorAll('button'));
                const orderBtn = buttons.find(b => b.innerText.includes('hidden_order_btn_12345'));
                if (orderBtn) {
                    orderBtn.click();
                    clearInterval(checkBtns);
                    
                    const newUrl = new URL(window.parent.location.href);
                    newUrl.searchParams.delete('tab');
                    window.parent.history.replaceState({}, '', newUrl);
                }
            }, 100);
        }
    }
</script>
"""


def get_home_html():
    local_ip = get_local_ip()
    return f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200');
    body {{
        margin: 0;
        padding: 0;
        display: flex;
        justify-content: center;
        align-items: center;
        font-family: 'Inter', sans-serif;
        background-color: transparent;
    }}
    .main-wrapper {{
        display: flex;
        flex-direction: column;
        gap: 20px;
        align-items: center;
    }}
    .btn-container {{ display: flex; gap: 20px; }}
    .banner {{
        width: 340px;
        height: 80px;
        border-radius: 15px;
        background-color: #E3EDED;
        display: flex;
        justify-content: center;
        align-items: center;
        color: #333;
        font-weight: 600;
        font-size: 1.1rem;
    }}
    .square-btn {{
        width: 160px;
        height: 160px;
        border-radius: 15px;
        border: none;
        cursor: pointer;
        position: relative;
        background: #ECF1FB;
        color: #333;
        text-align: left;
    }}
    .btn-text {{
        position: absolute;
        top: 20px;
        left: 20px;
        font-size: 1.4rem;
        font-weight: 600;
        line-height: 1.2;
    }}
    .material-symbols-rounded {{
        font-size: 40px;
        color: #333;
        font-variation-settings: 'wght' 300, 'opsz' 40;
    }}
    .icon-wrapper {{
        position: absolute;
        bottom: 20px;
        right: 20px;
        display: inline-block;
    }}
    @media (prefers-color-scheme: dark) {{
        .banner {{ background-color: #2D2D2D; color: #eee; }}
        .square-btn {{ background: #2D2D2D; color: #eee; }}
        .material-symbols-rounded {{ color: #eee; }}
        #qr-code-img {{ filter: brightness(0.8); }}
        .banner div[style*="color: #666"] {{ color: #aaa !important; }}
    }}
    </style>
    <div class="main-wrapper">
        <div class="btn-container">
            <button class="square-btn" onclick="
                const btns = Array.from(window.parent.document.querySelectorAll('button'));
                const target = btns.find(b => b.innerText.includes('hidden_order_btn_12345'));
                if(target) target.click();
            ">
                <span class="btn-text">커피<br>주문하기</span>
                <div class="icon-wrapper">
                    <span class="material-symbols-rounded">local_cafe</span>
                </div>
            </button>
            <button class="square-btn" onclick="
                const btns = Array.from(window.parent.document.querySelectorAll('button'));
                const target = btns.find(b => b.innerText.includes('hidden_history_btn_12345'));
                if(target) target.click();
            ">
                <span class="btn-text">주문<br>상세보기</span>
                <div class="icon-wrapper">
                    <span class="material-symbols-rounded">manage_search</span>
                </div>
            </button>
        </div>
        <div class="banner">
            <div style="flex: 1; padding-left: 20px; text-align: left;">
                <div>QR Order</div>
                <div style="font-size: 0.75rem; font-weight: normal; color: #666; margin-top: 4px;">QR코드를 스캔하면 빠른 주문이 가능합니다.</div>
            </div>
            <img id="qr-code-img" style="width: 50px; height: 50px; margin-right: 20px;">
        </div>
    </div>
    <script>
        const currentUrl = new URL(window.parent.location.href);
        if (currentUrl.hostname === 'localhost' || currentUrl.hostname === '127.0.0.1') {{
            currentUrl.hostname = '{local_ip}';
        }}
        currentUrl.searchParams.set('tab', 'order');
        document.getElementById('qr-code-img').src = 'https://api.qrserver.com/v1/create-qr-code/?size=150x150&data=' + encodeURIComponent(currentUrl.toString());
    </script>
    """

@st.cache_data
def get_cached_styles():
    return f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200');
    @font-face {{
        font-family: 'DaeguBukseongro';
        src: url('https://cdn.jsdelivr.net/gh/projectnoonnu/2511-1@1.0/DaeguBukseongro-Light.woff2') format('woff2');
        font-weight: 300;
        font-style: normal;
        font-display: swap;
    }}
    

    /* 배경 설정 */
    [data-testid="stAppViewBlockContainer"]:has(#home-bg-marker) {{
        position: relative !important;
        z-index: 1 !important;
        background: transparent !important;
        border-radius: 0 !important;
        width: calc(100% + 2rem) !important;
        min-height: calc(100vh - 200px) !important;
        margin-left: -1rem !important;
        margin-top: 1rem !important;
        border: none !important;
        border-top: 1px solid #E5E7EB !important;
        box-sizing: border-box !important;
        overflow: hidden !important;
        display: flex;
        justify-content: center;
        align-items: center;
    }}
    
    [data-testid="stForm"] {{
        position: relative !important;
        z-index: 1 !important;
        background: transparent !important;
        border-radius: 0 !important;
        width: calc(100% + 3rem) !important;
        margin-left: -1.5rem !important;
        margin-bottom: -1.5rem !important;
        padding-left: 1.5rem !important;
        padding-right: 1.5rem !important;
        padding-bottom: 1.5rem !important;
        border: none !important;
        border-top: 1px solid #E5E7EB !important;
        box-sizing: border-box !important;
        overflow: hidden !important;
    }}
    [data-testid="stAppViewBlockContainer"]:has(#home-bg-marker)::before {{
        content: "" !important;
        position: absolute !important;
        top: 0 !important;
        left: 0 !important;
        width: 100% !important;
        background-color: #ffffff !important;
        z-index: -1 !important;
        height: 100% !important;
    }}
    [data-testid="stForm"]::before {{
        content: "" !important;
        position: absolute !important;
        top: 0 !important;
        left: 0 !important;
        width: 100% !important;
        background-color: #F2F6F7 !important;
        z-index: -1 !important;
        height: 100% !important;
    }}
    @media (prefers-color-scheme: dark) {{
        [data-testid="stForm"], [data-testid="stAppViewBlockContainer"]:has(#home-bg-marker) {{ border-top: 1px solid #333 !important; }}
        [data-testid="stForm"]::before, [data-testid="stAppViewBlockContainer"]:has(#home-bg-marker)::before {{ 
            background-color: #1E1E1E !important; 
        }}
    }}
    
    div[data-testid="stAppViewBlockContainer"]:has(#home-bg-marker) div.element-container:has(#st-copyright) {{
        position: absolute !important;
        bottom: 40px !important;
        left: 0 !important;
        width: 100% !important;
    }}

    /* 공통 UI 및 레이아웃 */
    .stButton>button {{ width: 100%; border-radius: 10px; font-weight: bold; }}
    div[data-testid="stElementContainer"]:has([data-testid="stFormSubmitButton"]) {{
        display: flex !important;
        justify-content: flex-end !important;
        width: 100% !important;
    }}
    [data-testid="stFormSubmitButton"] {{ margin-top: 0.5rem !important; display: flex !important; justify-content: flex-end !important; }}
    [data-testid="stFormSubmitButton"] button {{
        background-color: #2D72DB !important;
        color: white !important;
        border: none !important;
        box-shadow: none !important;
        width: auto !important;
        height: 43px !important;
        padding: 0 24px !important;
        border-radius: 3px !important;
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

    .block-container {{
        max-width: 500px !important;
        margin: 0 auto !important;
        padding-top: 1.5rem !important;
        padding-bottom: 2rem !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
    }}
    div[data-testid="stAppViewContainer"] {{
        overflow-y: auto !important;
        overflow-x: hidden !important;
        scrollbar-gutter: stable !important;
    }}

    /* 타이틀 및 탭 조정 */
    h1 {{
        font-family: 'DaeguBukseongro', sans-serif !important;
        font-weight: 300 !important;
        font-size: 30px !important;
        margin: 0 !important;
        padding-top: 15px !important;
        padding-bottom: 40px !important;
        line-height: 40px !important;
        height: 40px !important;
        border-bottom: none !important;
    }}
    [data-testid="stHeadingWithActionElements"] {{ 
        border-bottom: none !important; 
        margin: 0 auto !important; 
        max-width: 340px !important;
    }}

    [data-testid="stWidgetInstructions"], .stTextInput small, .stTextInput label + div + div {{ display: none !important; }}

    /* 카드 및 리스트 스타일 */
    .order-list-container {{
        margin-left: -1.5rem;
        margin-right: -1.5rem;
        margin-bottom: -1.5rem;
        background-color: #F2F6F7;
        min-height: calc(100vh - 200px);
        display: flex;
        flex-direction: column;
    }}
    .order-list-header-line {{ border-top: 1px solid #E5E7EB; margin: 0; }}
    .order-card-wrapper {{ margin: 0; }}
    .order-card-wrapper:not(:last-child) .order-card::after {{
        content: "";
        position: absolute;
        bottom: 0;
        left: 1.2rem;
        right: 1.2rem;
        height: 1px;
        background-color: #EEEEEE;
    }}
    .order-card {{
        border-radius: 0;
        box-shadow: none;
        padding: 14px 1.2rem;
        border: none;
        background: #ffffff;
        color: #333;
        width: auto !important;
        box-sizing: border-box !important;
        display: flex;
        justify-content: space-between;
        align-items: center;
        position: relative;
        overflow: hidden;
    }}
    .card-left {{ display: flex; flex-direction: column; gap: 3px; flex: 1; }}
    .card-right {{ display: flex; flex-direction: column; align-items: flex-end; gap: 3px; padding-left: 16px; }}
    .summary-item {{ color: #333; font-size: 0.9rem; font-weight: 400; margin-bottom: 6px; letter-spacing: -0.01em; }}
    .summary-item .qty {{ font-size: 0.9rem; font-weight: 400; color: #333; font-variant-numeric: tabular-nums; }}
    .summary-total {{ color: #333; font-size: 0.9rem; }}
    .summary-box {{
        background: #ffffff;
        box-shadow: 0 2px 4px rgba(0,0,0,0.04), 0 8px 16px rgba(0,0,0,0.04);
        margin: 10px 0;
        border-radius: 17px;
        padding: 1rem 1.1rem;
        overflow: hidden;
    }}
    .receipt-date {{ text-align: right; font-size: 0.8rem; font-weight: 400; margin-bottom: 0; color: #777; font-variant-numeric: tabular-nums; letter-spacing: 0.02em; }}

    .order-no {{ font-size: 0.7rem; font-weight: 700; color: #777; letter-spacing: 0.3px; font-variant-numeric: tabular-nums; }}
    .order-name {{ font-size: 0.9rem; font-weight: 600; line-height: 1.3; color: #333; letter-spacing: -0.02em; }}
    .order-time {{ font-size: 0.7rem; color: #bbb; font-variant-numeric: tabular-nums; letter-spacing: 0.02em; }}
    .order-info {{ font-size: 0.8rem; line-height: 1.5; color: #333; letter-spacing: -0.01em; }}
    .order-card .card-left, .order-card .card-right {{ position: relative; z-index: 1; }}

    @media (prefers-color-scheme: dark) {{
        .order-list-container {{ background-color: #1E1E1E; }}
        .order-list-header-line {{ border-top: 1px solid #333; }}
        .order-card {{ border: none; color: #eee; background: #2D2D2D; }}
        .order-card-wrapper:not(:last-child) .order-card::after {{ background-color: #333; }}
        .summary-item {{ color: #ddd; }}
        .summary-item .qty {{ color: #aaa; }}
        .summary-total {{ color: #eee; }}
        .receipt-date {{ color: #666; }}
        .summary-box {{
            background: #2D2D2D;
            box-shadow: none;
        }}
        .order-no {{ color: #666; }}
        .order-time {{ color: #666; }}
        .order-info {{ color: #aaa; }}
        .order-name {{ color: #e0e0e0; }}
        .name-badge {{ background: #2A3A52 !important; }}
        .name-badge span {{ color: #7AADEE !important; }}
        .mod-dot {{ border-color: #2D2D2D !important; }}
    }}
    
    /* Input & Pills 스타일 통일 */
    [data-testid="stPills"], [data-testid="stButtonGroup"], [data-testid="stTextInput"] {{
        display: flex !important;
        flex-direction: column !important;
        align-items: flex-start !important;
        gap: 3px !important;
        margin-bottom: 7px !important;
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
        border: 1px solid #E5E7EB !important;
        color: #333 !important;
        background-color: #ffffff !important;
        min-height: 37px !important;
    }}
    button[data-variant="pills"] p, button[data-variant="pills"]:hover p, button[data-variant="pills"]:focus p {{ color: #333 !important; }}
    button[data-variant="pills"][aria-checked="true"], button[data-variant="pills"][aria-pressed="true"], button[data-variant="pills"][aria-checked="true"]:hover, button[data-variant="pills"][aria-pressed="true"]:hover {{
        background-color: #E4EEF9 !important;
        border: 1px solid #E4EEF9 !important;
        color: #214D7E !important;
        min-height: 37px !important;
    }}
    button[data-variant="pills"][aria-checked="true"] p, button[data-variant="pills"][aria-pressed="true"] p, button[data-variant="pills"][aria-checked="true"]:hover p, button[data-variant="pills"][aria-pressed="true"]:hover p {{
        color: #214D7E !important;
    }}
    
    .stTextInput div[data-testid="stTextInputRootElement"] {{ background-color: #ffffff !important; }}
    .stTextInput div[data-testid="stTextInputRootElement"]:focus-within {{ background-color: #ffffff !important; border-color: #2D72DB !important; outline: none !important; box-shadow: none !important; }}
    .stTextInput input {{ font-size: 0.9rem !important; }}

    @media (prefers-color-scheme: dark) {{
        [data-testid="stPills"] > label, [data-testid="stButtonGroup"] > label, .stTextInput label p, .stTextInput label div {{
            color: #ccc !important;
        }}
        .stTextInput div[data-testid="stTextInputRootElement"] {{
            background-color: #2D2D2D !important;
            border: 1px solid #444 !important;
        }}
        .stTextInput div[data-testid="stTextInputRootElement"]:focus-within {{
            background-color: #2D2D2D !important;
            border-color: #444 !important;
        }}
        button[data-variant="pills"], button[data-variant="pills"]:hover, button[data-variant="pills"]:focus {{
            background-color: #2D2D2D !important;
            border: 1px solid #444 !important;
        }}
        button[data-variant="pills"] p, button[data-variant="pills"]:hover p, button[data-variant="pills"]:focus p {{ color: #ccc !important; }}

        button[data-variant="pills"][aria-checked="true"], button[data-variant="pills"][aria-pressed="true"], button[data-variant="pills"][aria-checked="true"]:hover, button[data-variant="pills"][aria-pressed="true"]:hover {{
            background-color: #555 !important;
            border: 1px solid #777 !important;
        }}
        button[data-variant="pills"][aria-checked="true"] p, button[data-variant="pills"][aria-pressed="true"] p, button[data-variant="pills"][aria-checked="true"]:hover p, button[data-variant="pills"][aria-pressed="true"]:hover p {{
            color: #fff !important;
        }}
    }}

    /* 토스트 커스텀 스타일 */
    [data-testid="stToast"] {{
        background-color: #333 !important;
        border-radius: 10px !important;
    }}
    [data-testid="stToast"] div, 
    [data-testid="stToast"] p,
    [data-testid="stToast"] span,
    [data-testid="stToast"] button,
    [data-testid="stToast"] i {{
        color: #ffffff !important;
        font-variation-settings: 'FILL' 1 !important;
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
            <div style="flex: 1; padding: 0 1.5rem 1.5rem 1.5rem; display: flex; flex-direction: column;">
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
        return
    
    today_df['주문일시_dt'] = pd.to_datetime(today_df['주문일시'])
    temp_map = {'핫': 'H)', '아이스': 'I)'}
    opt_map = {'연하게': '-1샷', '샷 추가': '+1샷', '사이즈 업': 'UP', '디카페인': 'Decaf', '두유로 변경': '두유', '오트밀크로 변경': '오트밀크'}
    
    def format_summary(r):
        base = f"{temp_map.get(r['온도'], r['온도'])} {r['메뉴']}"
        if pd.isna(r['옵션']) or str(r['옵션']).strip() == '': return base
        opts = [opt_map.get(o.strip(), o.strip()) for o in str(r['옵션']).split(',')]
        return f"{base}, {', '.join(opts)}"
        
    today_df['주문요약'] = today_df.apply(format_summary, axis=1)
    summary_df = today_df.groupby('주문요약').size().reset_index(name='수량').sort_values('수량', ascending=False)

    summary_items_html = "".join([
        textwrap.dedent(f'''
        <div class="summary-item" style="display: flex; justify-content: space-between; align-items: baseline; gap: 8px;">
            <span style="flex: 1;">{row["주문요약"]}</span>
            <span class="qty">{row["수량"]}</span>
        </div>
        ''') for _, row in summary_df.iterrows()
    ])
    
    total_qty = summary_df['수량'].sum()

    body_html = textwrap.dedent(f'''
        <div style="margin-bottom: 13px; margin-top: 13px;">
            <div class="summary-box">
                <div>
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                        <div style="display:flex;align-items:center;gap:4px;color:#333;">
                            <span style="font-family:'Material Symbols Rounded';font-size:1.2rem;font-variation-settings:'wght' 300,'FILL' 0,'opsz' 20;line-height:1;">receipt</span>
                            <span style="font-size:0.9rem;font-weight:600;letter-spacing:0.2px;">주문내역</span>
                        </div>
                        <div class="receipt-date">{today.strftime('%Y-%m-%d')}</div>
                    </div>
                    <hr style="border: 0; border-top: 1px solid #EEEEEE; margin: 0 0 12px 0;">
                    <div>{summary_items_html}</div>
                    <hr style="border: 0; border-top: 1px solid #EEEEEE; margin: 12px 0;">
                    <div class="summary-total" style="display: flex; justify-content: space-between; font-size: 0.9rem; font-weight: 600; letter-spacing: -0.01em;">
                        <span style="background: linear-gradient(to top, rgba(255, 220, 0, 0.35) 50%, transparent 50%); padding: 0 3px;">총 수량</span>
                        <span style="background: linear-gradient(to top, rgba(255, 220, 0, 0.35) 50%, transparent 50%); padding: 0 3px; font-variant-numeric: tabular-nums;">{total_qty}잔</span>
                    </div>
                </div>
            </div>
        </div>
    ''')

    today_sorted = today_df.sort_values('주문일시').copy()
    today_sorted['연번'] = range(1, len(today_sorted) + 1)
    today_sorted['주문시간_str'] = today_sorted['주문일시_dt'].dt.strftime('%H:%M:%S')

    section_header_html = (
        '<div style="display:flex;align-items:center;gap:4px;color:#777;margin:13px 0 8px 0;">'
        '<span style="font-family:\'Material Symbols Rounded\';font-size:1.2rem;font-variation-settings:\'wght\' 300,\'FILL\' 0,\'opsz\' 20;line-height:1;">group</span>'
        '<span style="font-size:0.9rem;font-weight:600;letter-spacing:0.2px;">개인별 주문상세</span>'
        '</div>'
    )

    cards_list = []
    for _, row in today_sorted.iterrows():
        opts = str(row['옵션']).strip() if pd.notna(row['옵션']) else ""
        info_text = f"{row['온도']} {row['메뉴']}" + (f" · {opts.replace(', ', ' · ')}" if opts else "")
        given_name = str(row['이름'])[1:]
        is_modified = str(row.get('수정여부', False)).lower() == 'true'
        mod_dot = '<span class="mod-dot" style="position:absolute;top:-1px;right:-1px;width:7px;height:7px;background:#5593F6;border-radius:50%;border:1.5px solid #fff;"></span>' if is_modified else ''

        cards_list.append(
            f'<div class="summary-box" style="margin-bottom:10px;margin-top:0;">'
            f'<div style="display:flex;align-items:center;gap:12px;">'
            f'<div style="position:relative;flex-shrink:0;">'
            f'<div class="name-badge" style="width:44px;height:44px;border-radius:50%;background:#E4EEF9;display:flex;align-items:center;justify-content:center;">'
            f'<span style="font-size:0.9rem;font-weight:600;color:#214D7E;letter-spacing:-0.03em;">{given_name}</span>'
            f'</div>'
            f'{mod_dot}'
            f'</div>'
            f'<div style="flex:1;min-width:0;">'
            f'<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:3px;">'
            f'<span style="display:inline-flex;align-items:center;gap:4px;"><span class="order-no">#{row["연번"]:02d}</span>'\
            + ('<span style="font-family:\'Material Symbols Rounded\';font-size:0.9rem;font-variation-settings:\'FILL\' 0,\'wght\' 300,\'opsz\' 20;color:#777;line-height:1;">thumb_up</span>' if row['연번'] == 1 else '') +
            f'</span>'
            f'<span class="order-time">{row["주문시간_str"]}</span>'
            f'</div>'
            f'<div class="order-info" style="white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{info_text}</div>'
            f'</div>'
            f'</div>'
            f'</div>'
        )

    cards_html = section_header_html + "".join(cards_list)
    st.markdown(re.sub(r'\n\s+', '', html_start + body_html + cards_html + html_end), unsafe_allow_html=True)

# ==========================================
# 5. 메인 애플리케이션
# ==========================================
@st.dialog("주문정보 입력")
def show_order_modal():
    with st.form("order_form", clear_on_submit=True):
        name = st.text_input("이름 :red[*]", placeholder="이름을 입력하세요.")
        menu = st.text_input("메뉴 :red[*]", placeholder="예) 아메리카노, 카페라떼")        
        temp = st.pills("음료 온도 :red[*]", ["핫", "아이스"], selection_mode="single", label_visibility="visible")
        option = st.pills("선택 항목", ["산미", "연하게", "샷 추가", "사이즈 업", "디카페인", "두유로 변경", "오트밀크로 변경"], selection_mode="multi", label_visibility="visible")
        
        submitted = st.form_submit_button("제출")

    if submitted:
        if not name.strip() or not menu.strip() or not temp:
            st.toast("필수 항목을 모두 입력해 주세요!", icon=":material/warning:")
        else:
            is_upd = save_order(name, menu.strip(), temp if temp else "", ", ".join(option) if option else "")
            msg = "주문이 성공적으로 업데이트되었습니다!" if is_upd else "주문이 성공적으로 접수되었습니다!"
            st.session_state.show_alert = msg
            st.rerun()

@st.dialog("주문상세")
def show_history_modal():
    show_orders()

def main():
    if "show_alert" in st.session_state:
        st.toast(st.session_state.show_alert, icon=":material/check_circle:")
        del st.session_state.show_alert

    st.markdown(get_cached_styles(), unsafe_allow_html=True)
    st.iframe(JS_APP_OBSERVER, height=1)
    
    st.title("오커무", anchor=False)
    
    st.markdown('<div id="home-bg-marker"></div>', unsafe_allow_html=True)
    st.iframe(get_home_html(), height=280)
    st.markdown("<div id='st-copyright'></div><p style='text-align: center; color: #888; font-size: 0.75rem; margin: 0; pointer-events: none;'>ⓒ 2026 pang83. All rights reserved.</p>", unsafe_allow_html=True)

    if st.button("hidden_order_btn_12345"):
        show_order_modal()
    if st.button("hidden_history_btn_12345"):
        show_history_modal()

if __name__ == "__main__":
    main()
