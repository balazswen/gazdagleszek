import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import urllib.request
import xml.etree.ElementTree as ET
import json
import os
from google import genai

st.set_page_config(
    page_title="Gazdag Leszek Elemzői Iroda",
    layout="wide",
    initial_sidebar_state="collapsed"
)

PORTFOLIO_FILE = "user_portfolio.json"

def load_portfolio():
    if os.path.exists(PORTFOLIO_FILE):
        try:
            with open(PORTFOLIO_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_portfolio(data):
    try:
        with open(PORTFOLIO_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass

portfolio_db = load_portfolio()

if "active_nav" not in st.session_state:
    st.session_state.active_nav = "Szétválasztott Chartok"

# --- EMOJI-MENTES OBSIDIAN BENTO CSS + FALTÓL FALIG NAVIGÁCIÓS SÁV ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@500;600;700&display=swap');

    [data-testid="stSidebar"], [data-testid="collapsedControl"], header {
        display: none !important;
    }
    .block-container {
        padding-top: 1.2rem !important;
        padding-bottom: 3rem !important;
        max-width: 1480px !important;
    }

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, sans-serif;
    }

    .stApp {
        background-color: #09080f;
        background-image: 
            radial-gradient(circle at 15% 5%, rgba(124, 58, 237, 0.14) 0px, transparent 38%),
            radial-gradient(circle at 85% 12%, rgba(56, 189, 248, 0.08) 0px, transparent 38%),
            radial-gradient(circle at 50% 95%, rgba(139, 92, 246, 0.08) 0px, transparent 50%);
        color: #f3f4f6;
    }

    /* Felső fejléc */
    .top-nav-pill {
        background: linear-gradient(165deg, #161522 0%, #100f18 100%);
        border: 1px solid rgba(255, 255, 255, 0.07);
        border-radius: 20px;
        padding: 14px 26px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 18px;
        box-shadow: 0 12px 30px rgba(0,0,0,0.55);
    }

    .purple-badge {
        background: linear-gradient(135deg, #7c3aed, #6d28d9);
        color: #ffffff;
        padding: 6px 18px;
        border-radius: 999px;
        font-size: 0.76rem;
        font-weight: 700;
        letter-spacing: 0.8px;
        text-transform: uppercase;
        box-shadow: 0 4px 15px rgba(124, 58, 237, 0.45);
    }

    /* Egységes Bento Kártya Keret */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background: linear-gradient(165deg, #171624 0%, #100f18 100%) !important;
        border: 1px solid rgba(255, 255, 255, 0.07) !important;
        border-radius: 22px !important;
        padding: 16px 18px !important;
        box-shadow: 0 14px 32px -10px rgba(0, 0, 0, 0.6) !important;
        transition: border-color 0.2s ease !important;
    }
    div[data-testid="stVerticalBlockBorderWrapper"]:hover {
        border-color: rgba(139, 92, 246, 0.35) !important;
    }

    .card-micro-label {
        font-size: 0.72rem;
        font-weight: 600;
        color: #9ca3af;
        text-transform: uppercase;
        letter-spacing: 0.9px;
        margin-bottom: 6px;
        display: block;
    }
    .card-big-value {
        font-family: 'JetBrains Mono', monospace;
        font-size: 1.55rem;
        font-weight: 700;
        color: #ffffff;
        line-height: 1.2;
        margin: 4px 0 8px 0;
    }
    .card-sub-pill {
        display: inline-block;
        font-size: 0.76rem;
        font-weight: 600;
        padding: 3px 11px;
        border-radius: 999px;
        background: rgba(16, 185, 129, 0.14);
        color: #34d399;
        margin-bottom: 10px;
    }
    .card-sub-pill-warn {
        display: inline-block;
        font-size: 0.76rem;
        font-weight: 600;
        padding: 3px 11px;
        border-radius: 999px;
        background: rgba(244, 63, 94, 0.14);
        color: #fb7185;
        margin-bottom: 10px;
    }

    /* Input mezők */
    div[data-baseweb="input"] > div, div[data-baseweb="select"] > div {
        background-color: #0c0b12 !important;
        border: 1px solid rgba(255, 255, 255, 0.09) !important;
        border-radius: 12px !important;
        color: #ffffff !important;
        font-family: 'JetBrains Mono', monospace !important;
        font-weight: 600 !important;
    }

    /* Másodlagos gombok és Popoverek */
    div[data-testid="stPopover"] > button, button[kind="secondary"] {
        width: 100% !important;
        background: #1c1a29 !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 12px !important;
        color: #cbd5e1 !important;
        font-weight: 600 !important;
        font-size: 0.82rem !important;
        height: 42px !important;
        padding: 0 14px !important;
        transition: all 0.2s ease !important;
    }
    div[data-testid="stPopover"] > button:hover, button[kind="secondary"]:hover {
        background: #27243a !important;
        border-color: rgba(167, 139, 250, 0.45) !important;
        color: #ffffff !important;
    }

    /* Elsődleges (AKTÍV NAVIGÁCIÓS FÜL) gomb stílusa */
    button[kind="primary"] {
        width: 100% !important;
        background: linear-gradient(135deg, #7c3aed 0%, #5b21b6 100%) !important;
        border: 1px solid rgba(167, 139, 250, 0.55) !important;
        border-radius: 12px !important;
        color: #ffffff !important;
        font-weight: 700 !important;
        font-size: 0.84rem !important;
        height: 42px !important;
        box-shadow: 0 6px 20px rgba(124, 58, 237, 0.4) !important;
    }

    .mono { font-family: 'JetBrains Mono', monospace; }
</style>
""", unsafe_allow_html=True)

# --- 1. FELSŐ FEJLÉC (EMOJI NÉLKÜL) ---
st.markdown("""
<div class="top-nav-pill">
    <div style="display:flex; align-items:center; gap:16px;">
        <div style="width:38px; height:38px; border-radius:12px; background:linear-gradient(135deg,#7c3aed,#4f46e5); display:flex; align-items:center; justify-content:center; font-weight:800; font-size:0.95rem; color:#fff; letter-spacing:0.5px;">GL</div>
        <div>
            <span style="font-size:1.25rem; font-weight:700; letter-spacing:-0.3px;">Gazdag Leszek <span style="color:#a78bfa; font-weight:400;">Elemzői Iroda</span></span>
            <span style="display:block; font-size:0.73rem; color:#9ca3af;">Intézményi Multi-Chart • Mintázat-Inspektor • Stratégia Backtest • Watchlist</span>
        </div>
    </div>
    <div style="display:flex; align-items:center; gap:12px;">
        <span class="purple-badge">PRO TERMINAL</span>
    </div>
</div>
""", unsafe_allow_html=True)

# --- 2. FELSŐ VEZÉRLŐPULT: 5 EGYFORMA BENTO KÁRTYA EGY SORBAN ---
top1, top2, top3, top4, top5 = st.columns(5)

with top1:
    with st.container(border=True):
        st.markdown('<span class="card-micro-label">Részvény Ticker</span>', unsafe_allow_html=True)
        ticker = st.text_input("Ticker", value="NVDA", label_visibility="collapsed").upper().strip()

with top2:
    with st.container(border=True):
        st.markdown('<span class="card-micro-label">Befektetési Horizont</span>', unsafe_allow_html=True)
        strategy = st.selectbox(
            "Időtáv",
            [
                "Swing Trade (Napi chart • 2-6 hét)",
                "Daytrade (15 perces chart • Napon belüli)",
                "Hosszú Táv (Napi/Heti • 1-3 év + Fundamentum)"
            ],
            index=0,
            label_visibility="collapsed"
        )

saved_pos = portfolio_db.get(ticker, {"has_pos": False, "price": 120.0, "qty": 10.0, "capital": 15000.0, "risk_pct": 1.5})

with top3:
    with st.container(border=True):
        pos_status_txt = f"{saved_pos.get('qty', 10):g} db @ ${saved_pos.get('price', 120):.1f}" if saved_pos.get("has_pos") else "Nincs aktív kötés"
        st.markdown(f'<span class="card-micro-label">Pozíció ({pos_status_txt})</span>', unsafe_allow_html=True)
        with st.popover("Saját Pozícióm"):
            st.markdown(f"##### {ticker} Pozíció Kezelése")
            has_position = st.toggle("Van már ebből a részvényből", value=saved_pos.get("has_pos", False))
            avg_buy_price = st.number_input("Átlagos bekerülési ár ($):", min_value=0.01, value=float(saved_pos.get("price", 120.0)), step=0.5)
            shares_qty = st.number_input("Darabszám (db):", min_value=0.01, value=float(saved_pos.get("qty", 10.0)), step=1.0)
            if st.button("Pozíció mentése"):
                portfolio_db[ticker] = {
                    "has_pos": has_position, "price": avg_buy_price, "qty": shares_qty,
                    "capital": saved_pos.get("capital", 15000.0), "risk_pct": saved_pos.get("risk_pct", 1.5)
                }
                save_portfolio(portfolio_db)
                st.success("Pozíció elmentve.")

with top4:
    with st.container(border=True):
        st.markdown(f'<span class="card-micro-label">Tőke (${saved_pos.get("capital", 15000):,.0f})</span>', unsafe_allow_html=True)
        with st.popover("Tőke és Kockázat"):
            st.markdown("##### Pozícióméretező Kalkulátor")
            account_capital = st.number_input("Kereskedési tőke ($):", min_value=100.0, value=float(saved_pos.get("capital", 15000.0)), step=500.0)
            risk_per_trade = st.slider("Max kockázat / kötés (%):", min_value=0.5, max_value=5.0, value=float(saved_pos.get("risk_pct", 1.5)), step=0.25)

with top5:
    with st.container(border=True):
        st.markdown('<span class="card-micro-label">Elemző Motor</span>', unsafe_allow_html=True)
        with st.popover("AI Kulcs Beállítása"):
            st.markdown("##### Gemini API Kulcs")
            api_key = st.text_input("API Kulcs:", type="password")
            st.caption("[Ingyenes kulcs igénylése](https://aistudio.google.com/apikey)")

# --- ADATLEKÉRŐ ÉS SZÁMÍTÓ FÜGGVÉNYEK ---
@st.cache_data(ttl=180)
def fetch_data(ticker_sym, period, interval):
    stock = yf.Ticker(ticker_sym)
    df = stock.history(period=period, interval=interval)
    try:
        info = stock.info
    except Exception:
        info = {}
    try:
        spy_df = yf.Ticker("SPY").history(period=period, interval=interval)
        vix_df = yf.Ticker("^VIX").history(period="5d", interval="1d")
        vix_val = float(vix_df['Close'].iloc[-1]) if not vix_df.empty else 18.0
    except Exception:
        spy_df = pd.DataFrame()
        vix_val = 18.0
    return df, info, spy_df, vix_val

def get_stock_news(ticker_symbol):
    headlines = []
    try:
        stock = yf.Ticker(ticker_symbol)
        for item in (stock.news or []):
            if 'content' in item and isinstance(item['content'], dict):
                title = item['content'].get('title')
                pub = item['content'].get('provider', {}).get('displayName', 'Yahoo')
                if title:
                    headlines.append(f"**[{pub}]** {title}")
            elif 'title' in item:
                headlines.append(f"**[{item.get('publisher', 'Yahoo')}]** {item['title']}")
    except Exception:
        pass
    if not headlines:
        try:
            clean_t = ticker_symbol.split('.')[0]
            url = f"https://news.google.com/rss/search?q={clean_t}+stock&hl=en-US&gl=US&ceid=US:en"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=5) as resp:
                root = ET.fromstring(resp.read())
            for item in root.findall('.//item')[:8]:
                t = item.find('title')
                if t is not None and t.text:
                    headlines.append(t.text)
        except Exception as e:
            headlines.append(f"Hírlekérési hiba: {e}")
    return headlines[:8]

def calculate_metrics(df):
    df = df.copy()
    df['SMA_20'] = df['Close'].rolling(window=20, min_periods=5).mean()
    df['SMA_50'] = df['Close'].rolling(window=50, min_periods=10).mean()
    df['SMA_200'] = df['Close'].rolling(window=200, min_periods=30).mean()
    df['EMA_9'] = df['Close'].ewm(span=9, adjust=False).mean()
    df['EMA_12'] = df['Close'].ewm(span=12, adjust=False).mean()
    df['EMA_26'] = df['Close'].ewm(span=26, adjust=False).mean()

    typical_p = (df['High'] + df['Low'] + df['Close']) / 3
    vol_roll = df['Volume'].rolling(window=20, min_periods=1).sum().replace(0, np.nan)
    df['VWAP'] = ((typical_p * df['Volume']).rolling(window=20, min_periods=1).sum() / vol_roll).bfill().ffill()

    df['MACD'] = df['EMA_12'] - df['EMA_26']
    df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    df['MACD_Hist'] = df['MACD'] - df['MACD_Signal']

    delta = df['Close'].diff()
    gain = delta.clip(lower=0).ewm(alpha=1/14, min_periods=5, adjust=False).mean()
    loss = (-1 * delta.clip(upper=0)).ewm(alpha=1/14, min_periods=5, adjust=False).mean().replace(0, 1e-9)
    df['RSI'] = (100 - (100 / (1 + (gain / loss)))).fillna(50.0)

    std_20 = df['Close'].rolling(window=20, min_periods=5).std().fillna(0)
    df['BB_Upper'] = df['SMA_20'] + (std_20 * 2)
    df['BB_Lower'] = df['SMA_20'] - (std_20 * 2)

    tr = pd.concat([
        df['High'] - df['Low'],
        np.abs(df['High'] - df['Close'].shift()),
        np.abs(df['Low'] - df['Close'].shift())
    ], axis=1).max(axis=1)
    df['ATR'] = tr.rolling(window=14, min_periods=3).mean().bfill()
    df['Vol_SMA_20'] = df['Volume'].rolling(window=20, min_periods=3).mean().bfill()

    if len(df) > 1 and (df.index[1] - df.index[0]).total_seconds() < 86400:
        df['TimeLabel'] = df.index.strftime('%m.%d %H:%M')
    else:
        df['TimeLabel'] = df.index.strftime('%Y-%m-%d')

    return df

def calculate_volume_profile(df, bins=16):
    recent = df.tail(80)
    low_min, high_max = float(recent['Low'].min()), float(recent['High'].max())
    if low_min == high_max:
        return pd.DataFrame({'price': [low_min], 'volume': [100]}), low_min
    price_bins = np.linspace(low_min, high_max, bins + 1)
    vol_profile = []
    for i in range(bins):
        p_low, p_high = price_bins[i], price_bins[i+1]
        p_mid = (p_low + p_high) / 2
        mask = (recent['Close'] >= p_low) & (recent['Close'] <= p_high)
        vol_sum = float(recent.loc[mask, 'Volume'].sum())
        vol_profile.append({'price': p_mid, 'volume': vol_sum})
    vp_df = pd.DataFrame(vol_profile)
    poc_price = float(vp_df.loc[vp_df['volume'].idxmax(), 'price']) if not vp_df.empty and vp_df['volume'].max() > 0 else float(df['Close'].iloc[-1])
    return vp_df, poc_price

def analyze_patterns_with_expectations(df):
    markers = []
    interactive_patterns = []
    recent = df.tail(65).copy()
    atr_now = float(df['ATR'].iloc[-1]) if not np.isnan(df['ATR'].iloc[-1]) else float(df['Close'].iloc[-1] * 0.015)

    swing_high_pos = int(np.argmax(recent['High'].values))
    swing_low_pos = int(np.argmin(recent['Low'].values))
    swing_high = float(recent['High'].iloc[swing_high_pos])
    swing_low = float(recent['Low'].iloc[swing_low_pos])
    wave_range = max(0.01, swing_high - swing_low)

    fib_382 = swing_high - (wave_range * 0.382)
    fib_500 = swing_high - (wave_range * 0.500)
    fib_618 = swing_high - (wave_range * 0.618)

    y = recent['Close'].values
    x = np.arange(len(y))
    slope, intercept = np.polyfit(x, y, 1)
    reg_line = slope * x + intercept
    std_dev = max(0.01, float(np.std(y - reg_line)))
    upper_ch = reg_line + (1.85 * std_dev)
    lower_ch = reg_line - (1.85 * std_dev)
    pct_slope = (slope * len(y)) / y[0] * 100

    if pct_slope > 1.2:
        interactive_patterns.append({
            "badge": "EMELKEDŐ TRENDCSATORNA",
            "bias": "BIKÁS (Trendkövető)",
            "what_is_it": f"Az árfolyam +{pct_slope:.1f}% meredekségű emelkedő regressziós csatornában mozog.",
            "expectation": f"**Piaci elvárás:** Amíg a csatorna alsó fala (`{lower_ch[-1]:.2f}`) kitart, a korrekciók vételi lehetőséget jelentenek a felső él (`{upper_ch[-1]:.2f}`) irányába.",
            "target": f"{upper_ch[-1]:.2f}",
            "invalidation": f"{lower_ch[-1] - (0.5 * atr_now):.2f}",
            "reliability": "Magas (72%)"
        })
    elif pct_slope < -1.2:
        interactive_patterns.append({
            "badge": "CSÖKKENŐ TRENDCSATORNA",
            "bias": "MEDVÉS (Óvatosság)",
            "what_is_it": f"Az árfolyam {pct_slope:.1f}% meredekségű csökkenő csatornában halad.",
            "expectation": f"**Piaci elvárás:** A felpattanások elakadhatnak a felső falnál (`{upper_ch[-1]:.2f}`). Trendforduló csak `{upper_ch[-1]:.2f}` feletti zárásnál várható.",
            "target": f"{lower_ch[-1]:.2f}",
            "invalidation": f"{upper_ch[-1]:.2f} feletti kitörés",
            "reliability": "Magas (70%)"
        })
    else:
        interactive_patterns.append({
            "badge": "KONSZOLIDÁCIÓS SÁV",
            "bias": "SEMLEGES (Sávmozgás)",
            "what_is_it": "Oldalazó egyensúlyi zóna a vevők és eladók között.",
            "expectation": f"**Piaci elvárás:** Sáv alján (`{lower_ch[-1]:.2f}`) vétel, sáv tetején (`{upper_ch[-1]:.2f}`) profitrealizálás a kitörésig.",
            "target": f"{upper_ch[-1]:.2f}",
            "invalidation": f"{lower_ch[-1]:.2f} alatti zárás",
            "reliability": "Közepes (65%)"
        })

    interactive_patterns.append({
        "badge": f"FIBONACCI GOLDEN POCKET ({fib_618:.2f})",
        "bias": "INTÉZMÉNYI TÁMASZ ZÓNA",
        "what_is_it": f"A fő hullám 50% (`{fib_500:.2f}`) és 61.8% (`{fib_618:.2f}`) közötti aranymetszés korrekciós zónája.",
        "expectation": f"**Piaci elvárás:** Ha az árfolyam felette tartózkodik vagy innen pattan, az algoritmusok a `{swing_high:.2f}` csúcs visszatesztelését célozzák.",
        "target": f"{swing_high:.2f}",
        "invalidation": f"{swing_low:.2f}",
        "reliability": "Kiemelkedő (75%)"
    })

    for i in range(1, len(recent)):
        c = recent.iloc[i]
        p = recent.iloc[i - 1]
        t_lbl = recent['TimeLabel'].iloc[i]
        body = abs(c['Close'] - c['Open'])
        rng = c['High'] - c['Low']
        if rng == 0:
            continue
        upper_sh = c['High'] - max(c['Close'], c['Open'])
        lower_sh = min(c['Close'], c['Open']) - c['Low']

        if p['Close'] < p['Open'] and c['Close'] > c['Open'] and c['Open'] <= p['Close'] and c['Close'] >= p['Open'] and body > (rng * 0.42):
            markers.append({'x': t_lbl, 'y': c['Low'] * 0.996, 'label': 'Bikás Elnyelő', 'color': '#10b981', 'symbol': 'triangle-up', 'pos': 'bottom center'})
            interactive_patterns.append({
                "badge": f"BIKÁS ELNYELŐ ({t_lbl})",
                "bias": "ERŐS VÉTELI IMPULZUS",
                "what_is_it": "A vevők egyetlen gyertya alatt teljesen felvásárolták az előző piros gyertya összes eladói kínálatát.",
                "expectation": "**Piaci elvárás:** Rövid távon folytatódó emelkedés (momentum kitörés) várható a következő 3-8 gyertyában.",
                "target": f"{c['Close'] + (2.2 * atr_now):.2f}",
                "invalidation": f"{min(c['Low'], p['Low']):.2f}",
                "reliability": "Magas (68%)"
            })
        elif p['Close'] > p['Open'] and c['Close'] < c['Open'] and c['Open'] >= p['Close'] and c['Close'] <= p['Open'] and body > (rng * 0.42):
            markers.append({'x': t_lbl, 'y': c['High'] * 1.004, 'label': 'Medvés Elnyelő', 'color': '#f43f5e', 'symbol': 'triangle-down', 'pos': 'top center'})
            interactive_patterns.append({
                "badge": f"MEDVÉS ELNYELŐ ({t_lbl})",
                "bias": "ELADÓI LEFORDULÁS",
                "what_is_it": "Az emelkedés csúcsán agresszív profitrealizálás indult, a piros gyertya bekebelezte az előző zöld gyertyát.",
                "expectation": "**Piaci elvárás:** Rövid távú korrekció és visszahúzódás várható a legközelebbi támaszszintig.",
                "target": f"{c['Close'] - (2.0 * atr_now):.2f}",
                "invalidation": f"{max(c['High'], p['High']):.2f}",
                "reliability": "Magas (67%)"
            })
        elif lower_sh > (body * 2.1) and upper_sh < (body * 0.45) and body > 0:
            markers.append({'x': t_lbl, 'y': c['Low'] * 0.996, 'label': 'Kalapács', 'color': '#34d399', 'symbol': 'diamond', 'pos': 'bottom center'})
            interactive_patterns.append({
                "badge": f"KALAPÁCS ALAKZAT ({t_lbl})",
                "bias": "TÁMASZ MEGERŐSÍTÉS",
                "what_is_it": "Hosszú alsó kanóc: az eladók lenyomták az árat, de zárásra a vevők mindent felvásároltak.",
                "expectation": f"**Piaci elvárás:** Sikeres támasz-teszt `{c['Low']:.2f}` szinten, felfelé pattanás várható.",
                "target": f"{c['Close'] + (2.0 * atr_now):.2f}",
                "invalidation": f"{c['Low']:.2f}",
                "reliability": "Közepes/Magas (64%)"
            })

    channel_overlay = {
        'x_labels': recent['TimeLabel'].values, 'mid': reg_line, 'upper': upper_ch, 'lower': lower_ch,
        'fib_382': fib_382, 'fib_500': fib_500, 'fib_618': fib_618
    }
    return markers[-8:], interactive_patterns[::-1][:8], channel_overlay

def evaluate_quant_model(df, spy_df, strategy_mode):
    curr = df.iloc[-1]
    score = 50
    reasons = []
    rel_strength_pct = 0.0

    if not spy_df.empty and len(spy_df) >= 20 and len(df) >= 20:
        s_ret = ((df['Close'].iloc[-1] / df['Close'].iloc[-20]) - 1) * 100
        m_ret = ((spy_df['Close'].iloc[-1] / spy_df['Close'].iloc[-20]) - 1) * 100
        rel_strength_pct = float(s_ret - m_ret)
        if rel_strength_pct > 2.0:
            score += 10
            reasons.append(f"**Piaci Vezérrészvény (Alpha: {rel_strength_pct:+.1f}%):** A részvény az utolsó 20 gyertyán `{rel_strength_pct:+.1f}%`-kal teljesítette felül az S&P 500 indexet.")
        elif rel_strength_pct < -2.0:
            score -= 10
            reasons.append(f"**Piaci Lemaradó (Alpha: {rel_strength_pct:+.1f}%):** Gyengébb relatív erő a szélesebb piacnál.")

    if "Daytrade" in strategy_mode:
        if curr['Close'] > curr['VWAP']:
            score += 15
            reasons.append(f"**Intraday Vevői Kontroll:** Árfolyam a napon belüli VWAP (`{curr['VWAP']:.2f}`) és EMA 9 (`{curr['EMA_9']:.2f}`) közelében vagy felette.")
        else:
            score -= 15
            reasons.append(f"**Intraday Gyengeség:** Árfolyam a súlyozott átlagár (VWAP: `{curr['VWAP']:.2f}`) alatt mozog.")
        atr_mult_stop, atr_mult_tp = 1.5, 2.5
    elif "Swing" in strategy_mode:
        if curr['Close'] > curr['SMA_20'] and curr['Close'] > curr['SMA_50']:
            score += 15
            reasons.append(f"**Erős Swing Trend:** Árfolyam az SMA 20 (`{curr['SMA_20']:.2f}`) és SMA 50 (`{curr['SMA_50']:.2f}`) felett.")
        elif curr['Close'] < curr['SMA_20'] and curr['Close'] < curr['SMA_50']:
            score -= 15
            reasons.append(f"**Megtört Swing Trend:** Árfolyam az SMA 20 (`{curr['SMA_20']:.2f}`) és SMA 50 (`{curr['SMA_50']:.2f}`) alatt.")
        atr_mult_stop, atr_mult_tp = 2.0, 3.6
    else:
        if curr['Close'] > curr['SMA_200']:
            score += 15
            reasons.append(f"**Hosszú Távú Bika Piac:** Árfolyam a 200 periódusos átlag (`{curr['SMA_200']:.2f}`) felett.")
        else:
            score -= 15
            reasons.append(f"**Medve Struktúra:** Árfolyam a 200 periódusos átlag (`{curr['SMA_200']:.2f}`) alatt.")
        atr_mult_stop, atr_mult_tp = 3.5, 6.5

    if curr['MACD'] > curr['MACD_Signal']:
        score += 10
        reasons.append(f"**Pozitív MACD Momentum:** A MACD (`{curr['MACD']:.2f}`) a szignálvonal (`{curr['MACD_Signal']:.2f}`) felett halad.")
    else:
        score -= 10
        reasons.append(f"**Negatív MACD Momentum:** Lassuló lendület (`{curr['MACD']:.2f}` < `{curr['MACD_Signal']:.2f}`).")

    rsi = float(curr['RSI'])
    if rsi < 32:
        score += 15
        reasons.append(f"**Túladott Zóna (RSI: {rsi:.1f}):** Közel a statisztikai fordulóponthoz (<30), vételi felpattanás esélye.")
    elif rsi > 70:
        score -= 15
        reasons.append(f"**Túlvett Zóna (RSI: {rsi:.1f}):** Túlhevült árfolyam (>70), korrekciós kockázat.")
    else:
        score += 5
        reasons.append(f"**Egészséges RSI ({rsi:.1f}):** Kiegyensúlyozott trendzóna (30 és 70 között).")

    score = max(0, min(100, score))
    if score >= 75: verdict = "ERŐS VÉTEL"
    elif score >= 60: verdict = "VÉTEL"
    elif score >= 45: verdict = "TARTÁS"
    elif score >= 30: verdict = "ÓVATOSSÁG"
    else: verdict = "ELADÁS"

    return score, verdict, reasons, atr_mult_stop, atr_mult_tp, rel_strength_pct

def run_strategy_backtest(df, initial_cap=10000.0):
    bt = df.dropna(subset=['SMA_20', 'RSI', 'MACD', 'MACD_Signal']).copy()
    if len(bt) < 25:
        return None

    buy_cond = ((bt['Close'] > bt['SMA_20']) & (bt['MACD'] > bt['MACD_Signal']) & (bt['RSI'] < 72)) | (bt['RSI'] < 33)
    sell_cond = ((bt['Close'] < bt['SMA_20']) & (bt['MACD'] < bt['MACD_Signal'])) | (bt['RSI'] > 75)

    pos = 0
    positions = []
    trades = []
    entry_p = 0.0

    for i in range(len(bt)):
        p_now = float(bt['Close'].iloc[i])
        if pos == 0 and buy_cond.iloc[i]:
            pos = 1
            entry_p = p_now
        elif pos == 1 and sell_cond.iloc[i]:
            pos = 0
            trades.append((p_now - entry_p) / entry_p * 100)
        positions.append(pos)

    if pos == 1:
        trades.append((float(bt['Close'].iloc[-1]) - entry_p) / entry_p * 100)

    bt['Position'] = positions
    bt['Market_Ret'] = bt['Close'].pct_change().fillna(0)
    bt['Strat_Ret'] = bt['Position'].shift(1).fillna(0) * bt['Market_Ret']

    bt['Buy_Hold_Equity'] = initial_cap * (1 + bt['Market_Ret']).cumprod()
    bt['Strategy_Equity'] = initial_cap * (1 + bt['Strat_Ret']).cumprod()

    strat_total_pct = ((bt['Strategy_Equity'].iloc[-1] / initial_cap) - 1) * 100
    bh_total_pct = ((bt['Buy_Hold_Equity'].iloc[-1] / initial_cap) - 1) * 100
    win_rate = (sum(1 for t in trades if t > 0) / len(trades) * 100) if trades else 0.0

    roll_max = bt['Strategy_Equity'].cummax()
    drawdown = (bt['Strategy_Equity'] - roll_max) / roll_max * 100
    max_dd = float(drawdown.min())

    return {
        'bt_df': bt, 'strat_pct': strat_total_pct, 'bh_pct': bh_total_pct,
        'win_rate': win_rate, 'total_trades': len(trades), 'max_dd': max_dd,
        'final_equity': float(bt['Strategy_Equity'].iloc[-1])
    }

# --- FŐ FUTTATÁS ---
if ticker:
    is_daytrade = "Daytrade" in strategy
    if is_daytrade:
        yf_period, yf_interval = "1mo", "15m"
    elif "Swing" in strategy:
        yf_period, yf_interval = "1y", "1d"
    else:
        yf_period, yf_interval = "2y", "1d"

    with st.spinner(f"Elemző motor futtatása ({ticker} • {yf_interval})..."):
        df, fundamentals, spy_df, vix_val = fetch_data(ticker, yf_period, yf_interval)

        if df.empty or len(df) < 20:
            st.error(f"Nem található elegendő adat a(z) '{ticker}' szimbólumhoz.")
        else:
            df = calculate_metrics(df)
            plot_df = df.tail(120).copy()
            curr = df.iloc[-1]
            prev = df.iloc[-2]
            change_pct = float(((curr['Close'] - prev['Close']) / prev['Close']) * 100)

            support_1 = float(df['Low'].tail(25).min())
            resistance_1 = float(df['High'].tail(25).max())
            vp_df, poc_price = calculate_volume_profile(df)

            score, verdict, reasons, mult_stop, mult_tp, alpha_pct = evaluate_quant_model(df, spy_df, strategy)
            atr = float(curr['ATR']) if not np.isnan(curr['ATR']) and curr['ATR'] > 0 else float(curr['Close'] * 0.015)
            stop_loss = float(curr['Close'] - (mult_stop * atr))
            take_profit = float(curr['Close'] + (mult_tp * atr))

            max_risk_money = account_capital * (risk_per_trade / 100.0)
            risk_per_share = max(0.01, curr['Close'] - stop_loss)
            recommended_shares = int(max_risk_money // risk_per_share)

            # --- 3. MÁSODIK SOR: 5 TELJESEN EGYSÉGES BENTO METRIKA KÁRTYA ---
            k1, k2, k3, k4, k5 = st.columns(5)

            with k1:
                with st.container(border=True):
                    pill_cls = "card-sub-pill" if change_pct >= 0 else "card-sub-pill-warn"
                    st.markdown(f"""
                        <span class="card-micro-label">Utolsó Árfolyam ({yf_interval})</span>
                        <div class="card-big-value">${curr['Close']:.2f}</div>
                        <span class="{pill_cls}">{change_pct:+.2f}% | ATR: {atr:.2f}</span>
                    """, unsafe_allow_html=True)
                    with st.popover("Ár és Volatilitás"):
                        st.markdown(f"**Utolsó ár:** `${curr['Close']:.2f}` ({change_pct:+.2f}%)\n\n**ATR (14) kilengés:** `${atr:.2f}` ({(atr/curr['Close']*100):.2f}%)\n\n**VIX Félelem-index:** `{vix_val:.1f}`")

            with k2:
                with st.container(border=True):
                    pill_cls = "card-sub-pill" if score >= 50 else "card-sub-pill-warn"
                    st.markdown(f"""
                        <span class="card-micro-label">Quant Pontszám</span>
                        <div class="card-big-value">{score} / 100</div>
                        <span class="{pill_cls}">{verdict}</span>
                    """, unsafe_allow_html=True)
                    with st.popover("Quant Index"):
                        st.markdown(f"**{score}/100 pont ({verdict})**\n\nSúlyozza a trendet, az RSI-t, a MACD-t és az S&P 500-hoz mért relatív erőt a választott időtávon.")

            with k3:
                with st.container(border=True):
                    pill_cls = "card-sub-pill" if alpha_pct >= 0 else "card-sub-pill-warn"
                    st.markdown(f"""
                        <span class="card-micro-label">Alpha vs S&P 500</span>
                        <div class="card-big-value">{alpha_pct:+.1f}%</div>
                        <span class="{pill_cls}">RSI (14): {curr['RSI']:.1f}</span>
                    """, unsafe_allow_html=True)
                    with st.popover("Relatív Erő és RSI"):
                        st.markdown(f"**Alpha (`{alpha_pct:+.1f}%`):** Ennyivel teljesít jobban vagy rosszabbul a részvény az S&P 500 indexnél az elmúlt 20 periódusban.\n\n**RSI (`{curr['RSI']:.1f}`):** <30 túladott, >70 túlvett.")

            with k4:
                with st.container(border=True):
                    st.markdown(f"""
                        <span class="card-micro-label">Okos Pénz POC / Szintek</span>
                        <div class="card-big-value">${poc_price:.2f}</div>
                        <span class="card-sub-pill">S1: {support_1:.1f} | R1: {resistance_1:.1f}</span>
                    """, unsafe_allow_html=True)
                    with st.popover("Mi az a POC szint?"):
                        st.markdown(f"**Point of Control (`${poc_price:.2f}`):** Az az árszint, ahol a legtöbb részvényt kötötték az intézmények. Legerősebb támasz/ellenállás.\n\n**Támasz:** `${support_1:.2f}` | **Ellenállás:** `${resistance_1:.2f}`")

            with k5:
                with st.container(border=True):
                    if has_position:
                        pnl_tot = (curr['Close'] - avg_buy_price) * shares_qty
                        pnl_pct = ((curr['Close'] - avg_buy_price) / avg_buy_price) * 100
                        pill_cls = "card-sub-pill" if pnl_pct >= 0 else "card-sub-pill-warn"
                        st.markdown(f"""
                            <span class="card-micro-label">Saját Pozíció P&L</span>
                            <div class="card-big-value">${pnl_tot:+.1f}</div>
                            <span class="{pill_cls}">{pnl_pct:+.2f}% ({shares_qty:g} db)</span>
                        """, unsafe_allow_html=True)
                        with st.popover("Pozícióm Terve"):
                            st.markdown(f"**Pozíció:** `{shares_qty:g} db` @ `${avg_buy_price:.2f}`\n\n**Javasolt Stop-Loss:** `${max(stop_loss, support_1):.2f}`\n\n**Célár:** `${take_profit:.2f}`")
                    else:
                        st.markdown(f"""
                            <span class="card-micro-label">Optimális Méret</span>
                            <div class="card-big-value">{recommended_shares} db</div>
                            <span class="card-sub-pill">Cél: {take_profit:.1f} | Stop: {stop_loss:.1f}</span>
                        """, unsafe_allow_html=True)
                        with st.popover("Pozícióméretező"):
                            st.markdown(f"**{risk_per_trade}% kockázat (`${max_risk_money:.0f}`) mellett:**\n\nPontosan `{recommended_shares} db` részvényt vehetsz `${stop_loss:.2f}`-os Stop-Loss és `${take_profit:.2f}`-os Célár mellett.")

            st.write("")
            # --- 4. GARANTÁLTAN FALTÓL FALIG ÉRŐ 5 OSZLOPOS NAVIGÁCIÓS SÁV (ST.TABS HELYETT) ---
            nav_options = [
                "Szétválasztott Chartok",
                "Mintázat-Inspektor",
                "Stratégia Backtest",
                "Watchlist Radar",
                "AI Elemző és Hírek"
            ]
            nav_cols = st.columns(5)
            for idx_n, nav_label in enumerate(nav_options):
                with nav_cols[idx_n]:
                    btn_type = "primary" if st.session_state.active_nav == nav_label else "secondary"
                    if st.button(nav_label, key=f"nav_btn_{idx_n}", type=btn_type, use_container_width=True):
                        st.session_state.active_nav = nav_label
                        st.rerun()

            st.write("")
            active_view = st.session_state.active_nav

            # =========================================================================
            # 1. NÉZET: SZÉTVÁLASZTOTT CHARTOK
            # =========================================================================
            if active_view == "Szétválasztott Chartok":
                x_vals = plot_df['TimeLabel']

                with st.container(border=True):
                    st.markdown(f"#### 1. Tiszta Árfolyam és Mozgóátlagok ({ticker} • {yf_interval} • Utolsó 120 gyertya)")
                    st.caption("Kategóriás időtengely: Daytrade (15 perces) módban is teljesen hézagmentes, nincsenek éjszakai és hétvégi szakadékok.")

                    fig_price = go.Figure()
                    fig_price.add_trace(go.Candlestick(
                        x=x_vals, open=plot_df['Open'], high=plot_df['High'], low=plot_df['Low'], close=plot_df['Close'],
                        name="Árfolyam", increasing_line_color='#10b981', decreasing_line_color='#f43f5e'
                    ))
                    if is_daytrade:
                        fig_price.add_trace(go.Scatter(x=x_vals, y=plot_df['VWAP'], line=dict(color='#f59e0b', width=2.2), name="VWAP (Intézményi Átlag)"))
                        fig_price.add_trace(go.Scatter(x=x_vals, y=plot_df['EMA_9'], line=dict(color='#a855f7', width=1.6), name="EMA 9"))
                    else:
                        fig_price.add_trace(go.Scatter(x=x_vals, y=plot_df['SMA_20'], line=dict(color='#38bdf8', width=1.6), name="SMA 20"))
                        fig_price.add_trace(go.Scatter(x=x_vals, y=plot_df['SMA_50'], line=dict(color='#a855f7', width=2), name="SMA 50"))
                        fig_price.add_trace(go.Scatter(x=x_vals, y=plot_df['SMA_200'], line=dict(color='#f59e0b', width=2.2), name="SMA 200"))

                    fig_price.add_hline(y=poc_price, line_dash="dot", line_color="#a78bfa", annotation_text=f"POC: {poc_price:.2f}")
                    if has_position:
                        fig_price.add_hline(y=avg_buy_price, line_dash="solid", line_color="#38bdf8", line_width=2, annotation_text=f"Bekerülési ár: {avg_buy_price:.2f}")

                    fig_price.update_layout(
                        height=430, xaxis_rangeslider_visible=False, template="plotly_dark",
                        xaxis=dict(type='category', nticks=12),
                        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(17,16,25,0.6)",
                        margin=dict(l=10, r=10, t=15, b=10), hovermode="x unified",
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                    )
                    st.plotly_chart(fig_price, use_container_width=True)

                sub1, sub2 = st.columns(2)
                with sub1:
                    with st.container(border=True):
                        st.markdown("##### 2. Különálló RSI (14) Momentum Diagram")
                        fig_rsi = go.Figure()
                        fig_rsi.add_trace(go.Scatter(
                            x=x_vals, y=plot_df['RSI'], line=dict(color='#a855f7', width=2),
                            fill='tozeroy', fillcolor='rgba(168, 85, 247, 0.09)', name="RSI (14)"
                        ))
                        fig_rsi.add_hline(y=70, line_dash="dash", line_color="#f43f5e", annotation_text="Túlvett (70)")
                        fig_rsi.add_hline(y=30, line_dash="dash", line_color="#10b981", annotation_text="Túladott (30)")
                        fig_rsi.update_layout(
                            height=250, template="plotly_dark", xaxis=dict(type='category', nticks=8),
                            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(17,16,25,0.6)",
                            margin=dict(l=10, r=10, t=10, b=10), yaxis=dict(range=[10, 90])
                        )
                        st.plotly_chart(fig_rsi, use_container_width=True)

                with sub2:
                    with st.container(border=True):
                        st.markdown("##### 3. Különálló MACD Trend-Lendület Diagram")
                        fig_macd = go.Figure()
                        colors_m = ['#10b981' if v >= 0 else '#f43f5e' for v in plot_df['MACD_Hist']]
                        fig_macd.add_trace(go.Bar(x=x_vals, y=plot_df['MACD_Hist'], marker_color=colors_m, name="Hisztogram"))
                        fig_macd.add_trace(go.Scatter(x=x_vals, y=plot_df['MACD'], line=dict(color='#a855f7', width=1.8), name="MACD"))
                        fig_macd.add_trace(go.Scatter(x=x_vals, y=plot_df['MACD_Signal'], line=dict(color='#f59e0b', width=1.5), name="Signal"))
                        fig_macd.update_layout(
                            height=250, template="plotly_dark", xaxis=dict(type='category', nticks=8),
                            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(17,16,25,0.6)",
                            margin=dict(l=10, r=10, t=10, b=10),
                            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                        )
                        st.plotly_chart(fig_macd, use_container_width=True)

                sub3, sub4 = st.columns(2)
                with sub3:
                    with st.container(border=True):
                        st.markdown("##### 4. Okos Pénz Forgalmi Profil (Volume by Price)")
                        fig_vp = go.Figure(go.Bar(
                            x=vp_df['volume'], y=vp_df['price'], orientation='h',
                            marker=dict(color='#7c3aed', line=dict(color='#a78bfa', width=1))
                        ))
                        fig_vp.add_hline(y=curr['Close'], line_color="#10b981", line_width=2, annotation_text="Jelenlegi ár")
                        fig_vp.update_layout(
                            height=250, template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
                            plot_bgcolor="rgba(17,16,25,0.6)", margin=dict(l=10, r=10, t=10, b=10),
                            xaxis_title="Összforgalom", yaxis_title="Árszint ($)"
                        )
                        st.plotly_chart(fig_vp, use_container_width=True)

                with sub4:
                    with st.container(border=True):
                        st.markdown("##### 5. Relatív Teljesítmény vs. S&P 500 (60 gyertya)")
                        fig_rel = go.Figure()
                        r_stock = ((df['Close'].tail(60) / df['Close'].tail(60).iloc[0]) - 1) * 100
                        r_x = df['TimeLabel'].tail(60)
                        fig_rel.add_trace(go.Scatter(x=r_x, y=r_stock.values, line=dict(color='#a855f7', width=2.5), name=ticker))
                        if not spy_df.empty and len(spy_df) >= 60:
                            r_spy = ((spy_df['Close'].tail(60) / spy_df['Close'].tail(60).iloc[0]) - 1) * 100
                            fig_rel.add_trace(go.Scatter(x=r_x, y=r_spy.values, line=dict(color='#6b7280', width=1.8, dash='dot'), name="S&P 500"))
                        fig_rel.update_layout(
                            height=250, template="plotly_dark", xaxis=dict(type='category', nticks=8),
                            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(17,16,25,0.6)",
                            margin=dict(l=10, r=10, t=10, b=10), yaxis_title="Relatív Hozam (%)",
                            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                        )
                        st.plotly_chart(fig_rel, use_container_width=True)

            # =========================================================================
            # 2. NÉZET: MINTÁZAT-INSPEKTOR
            # =========================================================================
            elif active_view == "Mintázat-Inspektor":
                markers, interactive_patterns, ch_data = analyze_patterns_with_expectations(df)
                p_col1, p_col2 = st.columns([2.85, 1.35])

                with p_col1:
                    with st.container(border=True):
                        st.markdown(f"#### Strukturális Mintázat, Csatorna és Fibonacci ({ticker} • {yf_interval})")
                        recent_df = df.tail(65)
                        rx = ch_data['x_labels']
                        fig_pat = go.Figure()
                        fig_pat.add_trace(go.Candlestick(
                            x=rx, open=recent_df['Open'], high=recent_df['High'], low=recent_df['Low'], close=recent_df['Close'],
                            name="Árfolyam", increasing_line_color='#10b981', decreasing_line_color='#f43f5e'
                        ))
                        fig_pat.add_trace(go.Scatter(x=rx, y=ch_data['upper'], line=dict(color='rgba(168,85,247,0.7)', width=1.5, dash='dot'), name="Csatorna Felső"))
                        fig_pat.add_trace(go.Scatter(
                            x=rx, y=ch_data['lower'], line=dict(color='rgba(168,85,247,0.7)', width=1.5, dash='dot'),
                            fill='tonexty', fillcolor='rgba(124,58,237,0.08)', name="Csatorna Alsó"
                        ))
                        fig_pat.add_trace(go.Scatter(x=rx, y=ch_data['mid'], line=dict(color='#a855f7', width=1.8), name="Regressziós Közép"))
                        fig_pat.add_hline(y=ch_data['fib_500'], line_dash="dot", line_color="rgba(250,204,21,0.5)", annotation_text=f"Fib 50% ({ch_data['fib_500']:.2f})")
                        fig_pat.add_hline(y=ch_data['fib_618'], line_dash="dash", line_color="rgba(250,204,21,0.85)", annotation_text=f"Fib 61.8% Golden ({ch_data['fib_618']:.2f})")

                        for m in markers:
                            fig_pat.add_trace(go.Scatter(
                                x=[m['x']], y=[m['y']], mode="markers+text",
                                marker=dict(symbol=m['symbol'], size=13, color=m['color'], line=dict(width=1.5, color="white")),
                                text=[m['label']], textposition=m['pos'], textfont=dict(size=11, color=m['color']),
                                showlegend=False
                            ))

                        fig_pat.update_layout(
                            height=520, xaxis_rangeslider_visible=False, template="plotly_dark",
                            xaxis=dict(type='category', nticks=10),
                            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(17,16,25,0.6)",
                            margin=dict(l=10, r=10, t=15, b=10)
                        )
                        st.plotly_chart(fig_pat, use_container_width=True)

                with p_col2:
                    with st.container(border=True):
                        st.markdown("#### Kattintható Mintázat-Elvárások")
                        st.caption("Kattints bármelyik felismert mintázatra a **piaci elvárás, célár és stop szint** megnyitásához:")
                        for pat in interactive_patterns:
                            with st.popover(f"{pat['badge']}"):
                                st.markdown(f"#### {pat['badge']}")
                                st.markdown(f"**Irány:** {pat['bias']} | **Megbízhatóság:** `{pat['reliability']}`")
                                st.markdown("---")
                                st.markdown(f"**Mit látunk?**\n\n{pat['what_is_it']}")
                                st.markdown(f"**Milyen elvárást jelent?**\n\n{pat['expectation']}")
                                st.markdown("---")
                                st.markdown(f"**Célzóna:** `{pat['target']}`\n\n**Érvénytelen (Stop):** `{pat['invalidation']}`")

            # =========================================================================
            # 3. NÉZET: STRATÉGIA BACKTEST
            # =========================================================================
            elif active_view == "Stratégia Backtest":
                bt_res = run_strategy_backtest(df, initial_cap=account_capital)
                if not bt_res:
                    st.warning("Nincs elegendő adat a backtesthez.")
                else:
                    b1, b2, b3, b4 = st.columns(4)
                    with b1:
                        with st.container(border=True):
                            st.markdown(f'<span class="card-micro-label">Algoritmus Hozama</span><div class="card-big-value">{bt_res["strat_pct"]:+.2f}%</div><span class="card-sub-pill">Végtőke: ${bt_res["final_equity"]:,.0f}</span>', unsafe_allow_html=True)
                    with b2:
                        with st.container(border=True):
                            st.markdown(f'<span class="card-micro-label">Buy & Hold Hozam</span><div class="card-big-value">{bt_res["bh_pct"]:+.2f}%</div><span class="card-sub-pill">Különbség: {(bt_res["strat_pct"]-bt_res["bh_pct"]):+.2f}%</span>', unsafe_allow_html=True)
                    with b3:
                        with st.container(border=True):
                            st.markdown(f'<span class="card-micro-label">Találati Arány (Win Rate)</span><div class="card-big-value">{bt_res["win_rate"]:.1f}%</div><span class="card-sub-pill">{bt_res["total_trades"]} lezárt kötés</span>', unsafe_allow_html=True)
                    with b4:
                        with st.container(border=True):
                            st.markdown(f'<span class="card-micro-label">Max Visszaesés (Drawdown)</span><div class="card-big-value">{bt_res["max_dd"]:.2f}%</div><span class="card-sub-pill-warn">Kockázati mutató</span>', unsafe_allow_html=True)

                    with st.container(border=True):
                        st.markdown(f"#### Tőkegörbe Szimuláció (Equity Curve) — Kezdőtőke: ${account_capital:,.0f}")
                        bt_df = bt_res['bt_df']
                        fig_bt = go.Figure()
                        fig_bt.add_trace(go.Scatter(
                            x=bt_df['TimeLabel'], y=bt_df['Strategy_Equity'], line=dict(color='#a855f7', width=2.5),
                            fill='tozeroy', fillcolor='rgba(124,58,237,0.1)', name="Quant Algoritmus Portfólió"
                        ))
                        fig_bt.add_trace(go.Scatter(
                            x=bt_df['TimeLabel'], y=bt_df['Buy_Hold_Equity'], line=dict(color='#6b7280', width=1.8, dash='dot'),
                            name="Buy & Hold (Sima Tartás)"
                        ))
                        fig_bt.update_layout(
                            height=400, template="plotly_dark", xaxis=dict(type='category', nticks=10),
                            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(17,16,25,0.6)",
                            margin=dict(l=10, r=10, t=15, b=10), yaxis_title="Portfólió Érték ($)", hovermode="x unified"
                        )
                        st.plotly_chart(fig_bt, use_container_width=True)

            # =========================================================================
            # 4. NÉZET: WATCHLIST RADAR
            # =========================================================================
            elif active_view == "Watchlist Radar":
                with st.container(border=True):
                    st.markdown("#### Többrészvényes Watchlist Szkenner és Bento Rangsor")
                    wl_col1, wl_col2 = st.columns([3.5, 1.2])
                    with wl_col1:
                        wl_input = st.text_input("Figyelt Tickerek:", value="NVDA, AAPL, MSFT, TSLA, META, AMZN, GOOGL, AMD", label_visibility="collapsed")
                    with wl_col2:
                        run_wl = st.button("Watchlist Szkennelése", type="primary")

                    if run_wl:
                        tickers_list = [t.strip().upper() for t in wl_input.split(",") if t.strip()]
                        rows = []
                        close_dict = {}
                        prog = st.progress(0)
                        for idx_t, sym in enumerate(tickers_list):
                            try:
                                w_df = yf.Ticker(sym).history(period="6mo", interval="1d")
                                if not w_df.empty and len(w_df) >= 30:
                                    w_df = calculate_metrics(w_df)
                                    close_dict[sym] = w_df['Close'].pct_change()
                                    sc, verd, _, _, _, alp = evaluate_quant_model(w_df, spy_df, "Swing")
                                    c_row = w_df.iloc[-1]
                                    p_row = w_df.iloc[-2]
                                    chg = ((c_row['Close'] - p_row['Close']) / p_row['Close']) * 100
                                    sup = w_df['Low'].tail(20).min()
                                    res = w_df['High'].tail(20).max()
                                    rows.append({
                                        "Ticker": sym, "Ár": float(c_row['Close']), "Napi %": float(chg),
                                        "Quant Pont": int(sc), "Ajánlás": verd, "RSI": float(c_row['RSI']),
                                        "Alpha %": float(alp), "Támasz": float(sup), "Ellenállás": float(res)
                                    })
                            except Exception:
                                pass
                            prog.progress((idx_t + 1) / len(tickers_list))

                        if rows:
                            rows = sorted(rows, key=lambda x: x["Quant Pont"], reverse=True)
                            st.markdown("##### Rangsorolt Részvény Kártyák (Quant Pontszám szerint)")
                            grid_cols = st.columns(4)
                            for i, r_item in enumerate(rows):
                                with grid_cols[i % 4]:
                                    with st.container(border=True):
                                        p_cls = "card-sub-pill" if r_item["Quant Pont"] >= 55 else "card-sub-pill-warn"
                                        st.markdown(f"""
                                            <span class="card-micro-label">{r_item['Ticker']} • RSI: {r_item['RSI']:.0f}</span>
                                            <div class="card-big-value">${r_item['Ár']:.2f} <span style="font-size:0.9rem; color:#9ca3af;">({r_item['Napi %']:+.1f}%)</span></div>
                                            <span class="{p_cls}">Pont: {r_item['Quant Pont']}/100 • {r_item['Ajánlás']}</span>
                                            <div style="font-size:0.76rem; color:#9ca3af; margin-top:4px;">S1: ${r_item['Támasz']:.1f} | R1: ${r_item['Ellenállás']:.1f} | Alpha: {r_item['Alpha %']:+.1f}%</div>
                                        """, unsafe_allow_html=True)

                            if len(close_dict) >= 3:
                                st.write("")
                                st.markdown("##### Portfólió Korrelációs Mátrix")
                                corr_df = pd.DataFrame(close_dict).corr().round(2)
                                fig_corr = go.Figure(data=go.Heatmap(
                                    z=corr_df.values, x=corr_df.columns, y=corr_df.index,
                                    colorscale='Purples', text=corr_df.values, texttemplate="%{text}", showscale=True
                                ))
                                fig_corr.update_layout(height=340, template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", margin=dict(l=10, r=10, t=10, b=10))
                                st.plotly_chart(fig_corr, use_container_width=True)

            # =========================================================================
            # 5. NÉZET: AI ELEMZŐ ÉS HÍREK
            # =========================================================================
            elif active_view == "AI Elemző és Hírek":
                a1, a2 = st.columns([1.3, 1])
                with a1:
                    with st.container(border=True):
                        st.markdown("<h4>Részletes Technikai Indoklás</h4>", unsafe_allow_html=True)
                        for r in reasons:
                            st.markdown(f"- {r}")

                with a2:
                    headlines = get_stock_news(ticker)
                    with st.container(border=True):
                        st.markdown("<h4>Legfrissebb Piaci Hírek</h4>", unsafe_allow_html=True)
                        for h in headlines[:6]:
                            st.markdown(f"- {h}")

                with st.container(border=True):
                    st.markdown("<h4>AI Vezető Portfóliómenedzser Stratégiai Szintézis</h4>", unsafe_allow_html=True)
                    if not api_key:
                        st.info("Kattints a jobb felső 'AI Kulcs Beállítása' kártyára, és add meg a Gemini API kulcsodat a személyre szabott elemzéshez.")
                    else:
                        try:
                            client = genai.Client(api_key=api_key.strip())
                            pos_txt = f"Van pozíciója: {shares_qty} db @ {avg_buy_price:.2f}" if has_position else "Nincs még pozíciója."
                            prompt = f"""
                            Te a Gazdag Leszek Elemzői Iroda vezető intézményi portfóliómenedzsere vagy. Elemezd a(z) {ticker} részvényt magyar nyelven, emojik használata nélkül!
                            - Időtáv: {strategy} ({yf_interval}), Pozíció: {pos_txt}
                            - Ár: {curr['Close']:.2f}, POC szint: {poc_price:.2f}, Alpha vs SPY: {alpha_pct:+.1f}%
                            - Quant Pontszám: {score}/100 ({verdict}), RSI: {curr['RSI']:.1f}, Stop: {stop_loss:.2f}, Célár: {take_profit:.2f}
                            - Hírek: {headlines}

                            Adj részletes, oktató jellegű elemzést:
                            1. Technikai és Intézményi Kép (POC szint, trend, relatív erő)
                            2. Hírek és Fundamentális Katalizátorok
                            3. Konkrét Akcióterv pontos árszintekkel (Belépő / Pozíciókezelés / Stop-Loss / Take-Profit).
                            """
                            with st.spinner("Elemzés generálása..."):
                                resp = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
                                st.markdown(resp.text)
                        except Exception as e:
                            st.error(f"API Hiba: {e}")
