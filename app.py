import streamlit as st
import pandas as pd
import sqlite3
import os
import io
import base64
import textwrap
from datetime import datetime, timedelta, timezone
import socket
import urllib.parse
import qrcode

# ==========================================
# 1. 상수 및 기본 설정
# ==========================================
KST = timezone(timedelta(hours=9))
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, 'coffee_orders.csv')
DB_FILE = os.path.join(BASE_DIR, 'coffee_orders.db')
PROFILES_DIR = os.path.join(BASE_DIR, 'profiles')
os.makedirs(PROFILES_DIR, exist_ok=True)

st.set_page_config(page_title="오커무", page_icon="☕", layout="centered")

# 음료 온도 및 옵션 축약 표기 맵
TEMP_MAP = {'핫': 'H)', '아이스': 'I)'}
OPT_MAP = {
    '연하게': '-1샷',
    '샷 추가': '+1샷',
    '사이즈 업': 'UP',
    '디카페인': 'DECAF',
    '두유로 변경': '두유',
    '오트밀크로 변경': '오트밀크'
}

# ==========================================
# 2. 유틸리티 및 헬퍼 함수
# ==========================================
def get_round_prefix(round_num):
    round_int = max(1, int(round_num))
    res = ""
    while round_int > 0:
        round_int, rem = divmod(round_int - 1, 26)
        res = chr(65 + rem) + res
    return res

def queue_toast(msg, icon=":material/check_circle:"):
    st.session_state["queued_toast"] = (msg, icon)

def check_queued_toast():
    if "queued_toast" in st.session_state:
        msg, icon = st.session_state.pop("queued_toast")
        st.toast(msg, icon=icon)

@st.cache_data
def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        pass

    try:
        hostname = socket.gethostname()
        for ip in socket.gethostbyname_ex(hostname)[2]:
            if not ip.startswith('127.') and not ip.startswith('169.254.'):
                return ip
    except Exception:
        pass

    return '127.0.0.1'

@st.cache_data
def get_qr_b64(url):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=6,
        border=1,
    )
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()

@st.cache_data
def get_profile_b64(file_path, mtime):
    try:
        with open(file_path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except Exception:
        return None

@st.cache_data(ttl=60)
def get_profiles_map():
    mapping = {}
    if os.path.exists(PROFILES_DIR):
        try:
            for fname in os.listdir(PROFILES_DIR):
                name_part, ext = os.path.splitext(fname)
                if ext.lower().lstrip('.') in ['jpg', 'jpeg', 'png', 'webp', 'gif']:
                    mapping[name_part.strip()] = os.path.join(PROFILES_DIR, fname)
        except Exception:
            pass
    return mapping

# 프로필 뱃지 생성 (사진 또는 기본 아이콘)
@st.cache_data(ttl=60)
def get_profile_badge_html(name):
    clean_name = str(name).strip()
    p_map = get_profiles_map()
    file_path = p_map.get(clean_name)
    if file_path:
        try:
            mtime = os.path.getmtime(file_path)
            data = get_profile_b64(file_path, mtime)
            if data:
                ext = os.path.splitext(file_path)[1].lower().lstrip('.')
                mime_type = "image/jpeg" if ext in ["jpg", "jpeg"] else f"image/{ext}"
                return (
                    f'<div class="profile-badge">'
                    f'<img src="data:{mime_type};base64,{data}" alt="{clean_name}">'
                    f'</div>'
                )
        except Exception:
            pass

    return (
        f'<div class="profile-badge">'
        f'<span>person</span>'
        f'</div>'
    )

def format_order_summary(row):
    base = f"{TEMP_MAP.get(row['온도'], row['온도'])} {row['메뉴']}"
    if pd.isna(row['옵션']) or str(row['옵션']).strip() == '':
        return base
    opts = [OPT_MAP.get(o.strip(), o.strip()) for o in str(row['옵션']).split(',')]
    return f"{base}, {', '.join(opts)}"

def render_order_card(row):
    opts = str(row['옵션']).strip() if pd.notna(row['옵션']) else ""
    info_text = f"{row['온도']} {row['메뉴']}" + (f" · {opts.replace(', ', ' · ')}" if opts else "")
    user_name = str(row['이름']).strip()
    is_modified = str(row.get('수정여부', False)).lower() == 'true'

    badge_html = get_profile_badge_html(user_name)
    modified_icon_html = '<span style="font-family:\'Material Symbols Rounded\';font-size:0.9rem;font-variation-settings:\'FILL\' 0,\'wght\' 300,\'opsz\' 20;color:#888;line-height:1;display:inline-block;user-select:none;">update</span>' if is_modified else ''
    first_icon_html = '<span style="font-family:\'Material Symbols Rounded\';font-size:0.9rem;font-variation-settings:\'FILL\' 0,\'wght\' 300,\'opsz\' 20;color:#888;line-height:1;display:inline-block;user-select:none;">thumb_up</span>' if row['연번'] == 1 else ''

    return (
        f'<div class="summary-box" style="margin-bottom:10px;margin-top:0;">'
        f'<div style="display:flex;align-items:center;gap:12px;">'
        f'{badge_html}'
        f'<div style="flex:1;min-width:0;">'
        f'<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:3px;">'
        f'<span style="display:inline-flex;align-items:center;gap:4px;"><span class="order-name">{user_name}</span>{modified_icon_html}{first_icon_html}</span>'
        f'<span class="order-time">{row["주문시간_str"]}</span>'
        f'</div>'
        f'<div class="order-info" style="white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{info_text}</div>'
        f'</div>'
        f'</div>'
        f'</div>'
    )

# ==========================================
# 3. 데이터 처리 로직 (SQLite)
# ==========================================
def get_db_connection():
    conn = sqlite3.connect(DB_FILE, timeout=10.0)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    with conn:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                주문일시 TEXT NOT NULL,
                이름 TEXT NOT NULL,
                메뉴 TEXT NOT NULL,
                온도 TEXT NOT NULL,
                옵션 TEXT DEFAULT '',
                수정여부 INTEGER DEFAULT 0,
                마감여부 INTEGER DEFAULT 0,
                회차 REAL DEFAULT 1.0
            );
        """)
        cursor = conn.execute("SELECT COUNT(*) FROM orders")
        count = cursor.fetchone()[0]
        # 기존 coffee_orders.csv 파일이 있고 DB가 비어있다면 자동 1회 마이그레이션
        if count == 0 and os.path.exists(DATA_FILE):
            try:
                csv_df = pd.read_csv(DATA_FILE, encoding='utf-8-sig')
                if not csv_df.empty:
                    for _, row in csv_df.iterrows():
                        conn.execute("""
                            INSERT INTO orders (주문일시, 이름, 메뉴, 온도, 옵션, 수정여부, 마감여부, 회차)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            str(row.get('주문일시', '')),
                            str(row.get('이름', '')).strip(),
                            str(row.get('메뉴', '')).strip(),
                            str(row.get('온도', '')).strip(),
                            str(row.get('옵션', '')) if pd.notna(row.get('옵션')) else '',
                            1 if str(row.get('수정여부', False)).lower() == 'true' else 0,
                            1 if str(row.get('마감여부', False)).lower() == 'true' else 0,
                            float(row.get('회차', 1.0)) if pd.notna(row.get('회차')) else 1.0
                        ))
            except Exception:
                pass
    conn.close()

@st.cache_data(ttl=5)
def load_data():
    init_db()
    conn = get_db_connection()
    try:
        df = pd.read_sql_query(
            "SELECT 주문일시, 이름, 메뉴, 온도, 옵션, 수정여부, 마감여부, 회차 FROM orders ORDER BY id ASC",
            conn
        )
    finally:
        conn.close()

    if df.empty:
        return pd.DataFrame(columns=['주문일시', '이름', '메뉴', '온도', '옵션', '수정여부', '마감여부', '회차'])

    df['수정여부'] = df['수정여부'].astype(int) == 1
    df['마감여부'] = df['마감여부'].astype(int) == 1
    df['회차'] = pd.to_numeric(df['회차'], errors='coerce').fillna(1.0)
    df['옵션'] = df['옵션'].fillna('')
    return df

def save_order(name, menu, temp, option):
    init_db()
    now = datetime.now(KST)
    now_str = now.strftime("%Y-%m-%d %H:%M:%S")
    today_str = now.strftime("%Y-%m-%d")
    
    conn = get_db_connection()
    is_upd = False
    with conn:
        # 오늘 날짜이면서 아직 마감되지 않은 동일 사용자 주문 검색
        cursor = conn.execute("""
            SELECT id FROM orders 
            WHERE 이름 = ? AND substr(주문일시, 1, 10) = ? AND 마감여부 = 0
            ORDER BY id DESC LIMIT 1
        """, (name, today_str))
        row = cursor.fetchone()
        
        if row:
            order_id = row['id']
            conn.execute("""
                UPDATE orders 
                SET 주문일시 = ?, 메뉴 = ?, 온도 = ?, 옵션 = ?, 수정여부 = 1
                WHERE id = ?
            """, (now_str, menu, temp, option, order_id))
            is_upd = True
        else:
            cursor = conn.execute("""
                SELECT 회차, 마감여부 FROM orders
                WHERE substr(주문일시, 1, 10) = ?
            """, (today_str,))
            today_orders = cursor.fetchall()
            current_round = 1.0
            if today_orders:
                max_round = max([float(r['회차']) for r in today_orders if r['회차'] is not None] or [1.0])
                all_closed = all([int(r['마감여부']) == 1 for r in today_orders])
                current_round = max_round + 1.0 if all_closed else max_round

            conn.execute("""
                INSERT INTO orders (주문일시, 이름, 메뉴, 온도, 옵션, 수정여부, 마감여부, 회차)
                VALUES (?, ?, ?, ?, ?, 0, 0, ?)
            """, (now_str, name, menu, temp, option, current_round))
            
    conn.close()
    load_data.clear()
    return is_upd

def reset_todays_orders():
    init_db()
    today_str = datetime.now(KST).strftime("%Y-%m-%d")
    conn = get_db_connection()
    with conn:
        conn.execute("""
            UPDATE orders 
            SET 마감여부 = 1
            WHERE substr(주문일시, 1, 10) = ? AND 마감여부 = 0
        """, (today_str,))
    conn.close()
    load_data.clear()

# ==========================================
# 4. UI 템플릿 (CSS / JS / HTML)
# ==========================================
JS_APP_OBSERVER = """
<script>
    const parentDoc = window.parent.document;
    let hideScheduled = false;
    const hideButtons = () => {
        if (hideScheduled) return;
        hideScheduled = true;
        requestAnimationFrame(() => {
            hideScheduled = false;
            const buttons = Array.from(parentDoc.querySelectorAll('button'));
            ['hidden_order_btn_12345', 'hidden_history_btn_12345', 'hidden_reset_btn_12345'].forEach(btnText => {
                const hiddenBtn = buttons.find(b => (b.innerText || b.textContent || '').includes(btnText));
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
        });
    };
    
    if (!parentDoc.body.dataset.resetListenerV2) {
        parentDoc.body.dataset.resetListenerV2 = "true";
        parentDoc.addEventListener('click', (e) => {
            const resetIcon = e.target.closest('.btn-reset-orders');
            if (resetIcon) {
                e.stopPropagation();
                e.preventDefault();
                if (confirm('신규 주문을 접수하시겠습니까?')) {
                    const buttons = Array.from(parentDoc.querySelectorAll('button'));
                    const resetBtn = buttons.find(b => (b.innerText || b.textContent || '').includes('hidden_reset_btn_12345'));
                    if (resetBtn) resetBtn.click();
                }
            }
        });
    }

    if (!parentDoc.body.dataset.appObserver) {
        parentDoc.body.dataset.appObserver = "true";
        const observer = new MutationObserver(() => hideButtons());
        observer.observe(parentDoc.body, { childList: true, subtree: true });
    }
    hideButtons();
</script>
"""

@st.cache_data
def get_home_html(roulette_url="https://pickerwheel.com/emb/"):
    local_ip = get_local_ip()
    port = st.config.get_option('server.port') or 8501
    order_url = f"http://{local_ip}:{port}/?tab=order"
    qr_b64 = get_qr_b64(order_url)
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
        text-decoration: none;
    }}
    .banner:visited, .banner:active, .banner:hover {{
        color: #333;
        text-decoration: none;
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
        font-family: 'Material Symbols Rounded';
        font-size: 40px;
        line-height: 1;
        display: inline-block;
        user-select: none;
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
        .banner, .banner:visited, .banner:active, .banner:hover {{ background-color: #2D2D2D; color: #eee; }}
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
                const target = btns.find(b => (b.innerText || b.textContent || '').includes('hidden_order_btn_12345'));
                if(target) target.click();
            ">
                <span class="btn-text">커피<br>주문하기</span>
                <div class="icon-wrapper">
                    <span class="material-symbols-rounded">local_cafe</span>
                </div>
            </button>
            <button class="square-btn" onclick="
                const btns = Array.from(window.parent.document.querySelectorAll('button'));
                const target = btns.find(b => (b.innerText || b.textContent || '').includes('hidden_history_btn_12345'));
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
                <div style="font-size: 0.75rem; font-weight: normal; color: #666; margin-top: 4px;">QR코드 스캔하고 바로 주문!</div>
            </div>
            <img id="qr-code-img" src="data:image/png;base64,{qr_b64}" alt="QR Order" style="width: 50px; height: 50px; margin-right: 20px;">
        </div>
        <a href="{roulette_url}" target="_blank" rel="noopener noreferrer" class="banner" style="cursor: pointer; text-decoration: none; color: inherit;">
            <div style="flex: 1; padding-left: 20px; text-align: left;">
                <div>랜덤 추첨</div>
                <div style="font-size: 0.75rem; font-weight: normal; color: #666; margin-top: 4px;">오늘의 커피값, 지갑 열 주인공은 누구?</div>
            </div>
            <div style="margin-right: 20px; display: flex; align-items: center; justify-content: center; width: 50px; height: 50px;">
                <span class="material-symbols-rounded" style="font-size: 40px; line-height: 1;">stadia_controller</span>
            </div>
        </a>
    </div>
    """

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

    /* 1. 홈 화면 및 배경 설정 */
    [data-testid="stAppViewBlockContainer"]:has(#home-bg-marker) {{
        position: relative !important;
        background-color: #ffffff !important;
        border-radius: 0 !important;
        width: calc(100% + 2rem) !important;
        margin-left: -1rem !important;
        margin-top: 1rem !important;
        border: none !important;
        border-top: 1px solid #E5E7EB !important;
        box-sizing: border-box !important;
        overflow: hidden !important;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        padding-bottom: 20px !important;
    }}
    
    [data-testid="stForm"] {{
        position: relative !important;
        background-color: #F2F6F7 !important;
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
    }}
    @media (prefers-color-scheme: dark) {{
        [data-testid="stForm"], [data-testid="stAppViewBlockContainer"]:has(#home-bg-marker) {{ 
            border-top: 1px solid #333 !important; 
            background-color: #1E1E1E !important; 
        }}
    }}
    
    div[data-testid="stAppViewBlockContainer"]:has(#home-bg-marker) div[data-testid="stElementContainer"]:has(#st-copyright) {{
        width: 100% !important;
        margin-top: 10px !important;
        margin-bottom: 0px !important;
    }}

    /* 2. 공통 UI 및 버튼 레이아웃 */
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
    }}

    /* 3. 타이틀 및 위젯 안내 문구 */
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

    /* 4. 주문내역 요약 및 카드 리스트 스타일 */
    .order-list-container {{
        margin-left: -1.5rem;
        margin-right: -1.5rem;
        margin-bottom: -1.5rem;
        background-color: #F2F6F7;
        display: flex;
        flex-direction: column;
        padding-bottom: 1.5rem;
    }}
    .order-list-header-line {{ border-top: 1px solid #E5E7EB; margin: 0; }}
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
    .summary-header {{ display: flex; justify-content: space-between; align-items: center; gap: 8px; font-size: 0.9rem; font-weight: 400; color: #333; margin-bottom: 6px; letter-spacing: -0.01em; }}
    .summary-order-no {{ display: flex; justify-content: space-between; align-items: center; font-size: 0.9rem; font-weight: 600; color: #888; margin: 13px 0 8px 0; letter-spacing: 0.2px; font-variant-numeric: tabular-nums; }}

    .order-name {{ font-size: 0.9rem; font-weight: 600; color: #333; }}
    .order-time {{ font-size: 0.7rem; color: #bbb; font-variant-numeric: tabular-nums; letter-spacing: 0.02em; }}
    .order-info {{ font-size: 0.8rem; line-height: 1.5; color: #333; letter-spacing: -0.01em; }}

    /* 프로필 뱃지 */
    .profile-badge {{
        width: 44px;
        height: 44px;
        border-radius: 50%;
        overflow: hidden;
        flex-shrink: 0;
        display: flex;
        align-items: center;
        justify-content: center;
        background: #E4EEF9;
    }}
    .profile-badge img {{
        width: 100%;
        height: 100%;
        object-fit: cover;
        display: block;
    }}
    .profile-badge span {{
        font-family: 'Material Symbols Rounded';
        font-size: 1.7rem;
        color: #214D7E;
        font-variation-settings: 'wght' 300, 'FILL' 1, 'opsz' 24;
        line-height: 1;
        user-select: none;
    }}

    @media (prefers-color-scheme: dark) {{
        .order-list-container {{ background-color: #1E1E1E; }}
        .order-list-header-line {{ border-top: 1px solid #333; }}
        .summary-item {{ color: #ddd; }}
        .summary-item .qty {{ color: #aaa; }}
        .summary-total {{ color: #eee; }}
        .summary-header {{ color: #888; }}
        .summary-order-no {{ color: #aaa; }}
        .summary-box {{
            background: #2D2D2D;
            box-shadow: none;
        }}
        .order-name {{ color: #eee; }}
        .order-time {{ color: #666; }}
        .order-info {{ color: #aaa; }}
        .profile-badge {{ background: #2A3A52 !important; }}
        .profile-badge span {{ color: #7AADEE !important; }}
    }}
    
    /* 5. Input & Pills 스타일 통일 */
    [data-testid="stPills"], [data-testid="stButtonGroup"], [data-testid="stTextInput"] {{
        display: flex !important;
        flex-direction: column !important;
        align-items: flex-start !important;
        gap: 3px !important;
        margin-bottom: 7px !important;
    }}
    [data-testid="stPills"] > label, [data-testid="stButtonGroup"] > label, [data-testid="stTextInput"] > label, [data-testid="stTextInput"] label p {{
        font-size: 0.9rem !important;
        font-weight: normal !important;
        margin-bottom: 0 !important;
        color: #333 !important;
    }}
    [data-testid="stPills"] > div, [data-testid="stButtonGroup"] > div, [data-testid="stTextInput"] > div {{ width: 100% !important; }}
    
    button[data-variant="pills"], button[data-variant="pills"]:hover, button[data-variant="pills"]:focus {{
        border: 1px solid #E5E7EB !important;
        color: #333 !important;
        background-color: #ffffff !important;
        min-height: 37px !important;
    }}
    button[data-variant="pills"] p, button[data-variant="pills"]:hover p, button[data-variant="pills"]:focus p {{ color: #333 !important; }}
    button[data-variant="pills"][aria-checked="true"], button[data-variant="pills"][aria-pressed="true"] {{
        background-color: #E4EEF9 !important;
        border: 1px solid #E4EEF9 !important;
        color: #214D7E !important;
        min-height: 37px !important;
    }}
    button[data-variant="pills"][aria-checked="true"] p, button[data-variant="pills"][aria-pressed="true"] p {{
        color: #214D7E !important;
    }}
    
    .stTextInput div[data-testid="stTextInputRootElement"] {{ background-color: #ffffff !important; }}
    .stTextInput div[data-testid="stTextInputRootElement"]:focus-within {{ background-color: #ffffff !important; border-color: #2D72DB !important; outline: none !important; box-shadow: none !important; }}
    .stTextInput input {{ font-size: 0.9rem !important; }}

    @media (prefers-color-scheme: dark) {{
        [data-testid="stPills"] > label, [data-testid="stButtonGroup"] > label, [data-testid="stTextInput"] > label, [data-testid="stTextInput"] label p {{
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

        button[data-variant="pills"][aria-checked="true"], button[data-variant="pills"][aria-pressed="true"] {{
            background-color: #555 !important;
            border: 1px solid #777 !important;
        }}
        button[data-variant="pills"][aria-checked="true"] p, button[data-variant="pills"][aria-pressed="true"] p {{
            color: #fff !important;
        }}
    }}

    /* 6. 토스트 커스텀 스타일 */
    [data-testid="stToast"] {{
        background-color: rgba(45, 45, 45, 0.9) !important;
        border-radius: 3px !important;
    }}
    [data-testid="stToast"] * {{
        color: #ffffff !important;
    }}
    [data-testid="stToast"] :is([data-testid="stIconMaterial"], .material-symbols-rounded, i, span) {{
        font-variation-settings: 'FILL' 0, 'wght' 400, 'GRAD' 0, 'opsz' 24 !important;
    }}
    [data-testid="stToast"] button {{
        background-color: transparent !important;
    }}
    </style>
    """

# ==========================================
# 5. 핵심 UI 컴포넌트 & 다이얼로그
# ==========================================
@st.fragment(run_every=timedelta(seconds=10))
def show_orders():
    df = load_data()
    
    html_start = textwrap.dedent('''
        <div class="order-list-container">
            <div class="order-list-header-line"></div>
            <div style="flex: 1; padding: 0 1rem 1.5rem 1rem; display: flex; flex-direction: column;">
    ''')
    
    html_end = textwrap.dedent('''
            </div>
        </div>
    ''')

    today = datetime.now(KST)
    today_str = today.strftime("%Y-%m-%d")
    today_df = df[(df['주문일시'].str[:10] == today_str) & (~df['마감여부'])].copy()
    
    if df.empty or today_df.empty:
        st.toast("아직 접수된 주문이 없어요!", icon=":material/info:")
        return
    
    today_df['주문일시_dt'] = pd.to_datetime(today_df['주문일시'])
    today_df['주문요약'] = today_df.apply(format_order_summary, axis=1)
    summary_df = today_df.groupby('주문요약').size().reset_index(name='수량').sort_values('수량', ascending=False)

    summary_items_html = "".join([
        f'<div class="summary-item" style="display:flex;justify-content:space-between;align-items:baseline;gap:8px;">'
        f'<span style="flex:1;">{row["주문요약"]}</span>'
        f'<span class="qty">{row["수량"]}</span>'
        f'</div>'
        for _, row in summary_df.iterrows()
    ])
    
    valid_rounds = pd.to_numeric(today_df['회차'], errors='coerce').dropna()
    current_round = int(valid_rounds.iloc[-1]) if not valid_rounds.empty else 1

    total_qty = summary_df['수량'].sum()
    round_char = get_round_prefix(current_round)
    order_no_str = f"NO : {today.strftime('%Y%m%d')}-{round_char}{total_qty}"

    body_html = textwrap.dedent(f'''
        <div style="margin-bottom: 10px; margin-top: 10px;">
            <div class="summary-order-no" style="display: flex; justify-content: space-between; align-items: center;">
                <span>{order_no_str}</span>
                <span class="material-symbols-rounded btn-reset-orders" style="font-family:'Material Symbols Rounded';font-size:1rem;font-variation-settings:'FILL' 0,'wght' 300,'opsz' 20;line-height:1;display:inline-flex;align-items:center;user-select:none;cursor:pointer;">new_window</span>
            </div>
            <div class="summary-box" style="margin-top: 0;">
                <div class="summary-header">
                    <span style="flex: 1;">메뉴명</span>
                    <span>수량</span>
                </div>
                <hr style="border: 0; border-top: 1px solid #EEEEEE; margin: 0 0 12px 0;">
                <div>{summary_items_html}</div>
                <hr style="border: 0; border-top: 1px solid #EEEEEE; margin: 12px 0;">
                <div class="summary-total" style="display: flex; justify-content: space-between; font-weight: 600; letter-spacing: -0.01em;">
                    <span>합계</span>
                    <span style="font-variant-numeric: tabular-nums;">{total_qty}</span>
                </div>
            </div>
        </div>
    ''')

    today_sorted = today_df.sort_values('주문일시').copy()
    today_sorted['연번'] = range(1, len(today_sorted) + 1)
    today_sorted['주문시간_str'] = today_sorted['주문일시_dt'].dt.strftime('%H:%M:%S')

    section_header_html = (
        '<div style="display:flex;align-items:center;gap:4px;color:#888;margin:10px 0 8px 0;">'
        '<span style="font-size:0.9rem;font-weight:600;letter-spacing:0.2px;">개인별 주문상세</span>'
        '</div>'
    )

    cards_html = section_header_html + "".join([render_order_card(row) for _, row in today_sorted.iterrows()])
    st.markdown(html_start + body_html + cards_html + html_end, unsafe_allow_html=True)

@st.dialog("주문정보 입력")
def show_order_modal():
    with st.form("order_form", clear_on_submit=True):
        name = st.text_input("이름 :red[*]", placeholder="이름을 입력하세요.")
        menu = st.text_input("메뉴 :red[*]", placeholder="메뉴를 입력하세요.")        
        temp = st.pills("음료 온도 :red[*]", ["핫", "아이스"], selection_mode="single", label_visibility="visible")
        option = st.pills("선택 항목", ["산미", "연하게", "샷 추가", "사이즈 업", "디카페인", "두유로 변경", "오트밀크로 변경"], selection_mode="multi", label_visibility="visible")
        
        submitted = st.form_submit_button("제출")

    if submitted:
        if not name.strip() or not menu.strip() or not temp:
            st.toast("필수 항목을 모두 입력해 주세요!", icon=":material/info:")
        else:
            is_upd = save_order(name, menu.strip(), temp, ", ".join(option) if option else "")
            msg = "주문이 성공적으로 업데이트되었습니다!" if is_upd else "주문이 성공적으로 접수되었습니다!"
            queue_toast(msg)
            st.rerun()

@st.dialog("주문내역")
def show_history_modal():
    show_orders()

def main():
    check_queued_toast()

    if st.query_params.get("tab") == "order":
        st.query_params.clear()
        show_order_modal()

    st.markdown(get_cached_styles(), unsafe_allow_html=True)
    st.iframe(JS_APP_OBSERVER, height=1)
    
    st.title("오커무", anchor=False)
    
    today = datetime.now(KST)
    today_str = today.strftime("%Y-%m-%d")
    df = load_data()
    today_df = df[(df['주문일시'].str[:10] == today_str) & (~df['마감여부'])].copy()
    candidates = [str(x).strip().replace(',', ' ') for x in today_df['이름'].dropna().unique() if str(x).strip()]

    if candidates:
        encoded_choices = urllib.parse.quote(','.join(candidates), safe=',')
        roulette_url = f"https://pickerwheel.com/emb/?choices={encoded_choices}"
    else:
        roulette_url = "https://pickerwheel.com/emb/"

    st.markdown('<div id="home-bg-marker"></div>', unsafe_allow_html=True)
    st.iframe(get_home_html(roulette_url), height=380)
    st.markdown("<div id='st-copyright'></div><p style='text-align: center; color: #888; font-size: 0.75rem; margin: 0; pointer-events: none;'>ⓒ 2026-2027 pang83. All rights reserved.</p>", unsafe_allow_html=True)

    if st.button("hidden_order_btn_12345"):
        show_order_modal()
    if st.button("hidden_history_btn_12345"):
        if today_df.empty:
            st.toast("아직 접수된 주문이 없어요!", icon=":material/info:")
        else:
            show_history_modal()
    if st.button("hidden_reset_btn_12345"):
        reset_todays_orders()
        queue_toast("기존 주문내역이 모두 삭제되었습니다!")
        st.rerun()

if __name__ == "__main__":
    main()
