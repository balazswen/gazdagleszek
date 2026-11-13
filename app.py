import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime
import json
import os
import joblib
from google import genai
from sklearn.ensemble import RandomForestClassifier

st.set_page_config(
    page_title="Gazdag Leszek Elemzői Iroda",
    layout="wide",
    initial_sidebar_state="collapsed"
)

PORTFOLIO_FILE = "user_portfolio.json"
JOURNAL_FILE = "prediction_journal.json"
MODELS_DIR = "ml_models"
FEATURE_COLS = ['RSI', 'Stoch_RSI', 'MACD_Hist', 'ADX', 'BB_Width', 'Dist_SMA20_Pct', 'Dist_SMA50_Pct', 'Vol_Ratio', 'Ret_5']

os.makedirs(MODELS_DIR, exist_ok=True)

# --- ADATBÁZIS KEZELÉS ---
def load_portfolio():
    default_data = {
        "capital": 15000.0,
        "risk_pct": 1.5,
        "holdings": {
            "NVDA": {"price": 125.0, "qty": 15.0},
            "AAPL": {"price": 210.0, "qty": 10.0}
        }
    }
    if os.path.exists(PORTFOLIO_FILE):
        try:
            with open(PORTFOLIO_FILE, "r", encoding="utf-8") as f:
                raw = json.load(f)
            if "holdings" in raw and isinstance(raw["holdings"], dict):
                return raw
        except Exception:
            return default_data
    return default_data

def save_portfolio(data):
    try:
        with open(PORTFOLIO_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass

def load_journal():
    if os.path.exists(JOURNAL_FILE):
        try:
            with open(JOURNAL_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_journal(data):
    try:
        with open(JOURNAL_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass

if "portfolio_db" not in st.session_state:
    st.session_state.portfolio_db = load_portfolio()
if "journal_db" not in st.session_state:
    st.session_state.journal_db = load_journal()

portfolio_db = st.session_state.portfolio_db
journal_db = st.session_state.journal_db

if "active_nav" not in st.session_state:
    st.session_state.active_nav = "Szétválasztott Chartok"

# --- EMOJI-MENTES OBSIDIAN BENTO CSS ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@500;600;700&display=swap');

    [data-testid="stSidebar"], [data-testid="collapsedControl"], header {
        display: none !important;
    }
    .block-container {
        padding-top: 1.1rem !important;
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
        padding: 6px 16px;
        border-radius: 999px;
        font-size: 0.74rem;
        font-weight: 700;
        letter-spacing: 0.8px;
        text-transform: uppercase;
        box-shadow: 0 4px 15px rgba(124, 58, 237, 0.45);
    }

    .live-dot {
        display: inline-block;
        width: 8px;
        height: 8px;
        background-color: #10b981;
        border-radius: 50%;
        margin-right: 6px;
        box-shadow: 0 0 8px #10b981;
    }

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
        font-size: 0.71rem;
        font-weight: 600;
        color: #9ca3af;
        text-transform: uppercase;
        letter-spacing: 0.9px;
        margin-bottom: 6px;
        display: block;
    }
    .card-big-value {
        font-family: 'JetBrains Mono', monospace;
        font-size: 1.5rem;
        font-weight: 700;
        color: #ffffff;
        line-height: 1.2;
        margin: 4px 0 8px 0;
    }
    .card-sub-pill {
        display: inline-block;
        font-size: 0.75rem;
        font-weight: 600;
        padding: 3px 11px;
        border-radius: 999px;
        background: rgba(16, 185, 129, 0.14);
        color: #34d399;
        margin-bottom: 10px;
    }
    .card-sub-pill-warn {
        display: inline-block;
        font-size: 0.75rem;
        font-weight: 600;
        padding: 3px 11px;
        border-radius: 999px;
        background: rgba(244, 63, 94, 0.14);
        color: #fb7185;
        margin-bottom: 10px;
    }

    div[data-baseweb="input"] > div, div[data-baseweb="select"] > div {
        background-color: #0c0b12 !important;
        border: 1px solid rgba(255, 255, 255, 0.09) !important;
        border-radius: 12px !important;
        color: #ffffff !important;
        font-family: 'JetBrains Mono', monospace !important;
        font-weight: 600 !important;
    }

    div[data-testid="stPopover"] > button, button[kind="secondary"] {
        width: 100% !important;
        background: #1c1a29 !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 12px !important;
        color: #cbd5e1 !important;
        font-weight: 600 !important;
        font-size: 0.80rem !important;
        height: 42px !important;
        padding: 0 10px !important;
        transition: all 0.2s ease !important;
    }
    div[data-testid="stPopover"] > button:hover, button[kind="secondary"]:hover {
        background: #27243a !important;
        border-color: rgba(167, 139, 250, 0.45) !important;
        color: #ffffff !important;
    }

    button[kind="primary"] {
        width: 100% !important;
        background: linear-gradient(135deg, #7c3aed 0%, #5b21b6 100%) !important;
        border: 1px solid rgba(167, 139, 250, 0.55) !important;
        border-radius: 12px !important;
        color: #ffffff !important;
        font-weight: 700 !important;
        font-size: 0.81rem !important;
        height: 42px !important;
        box-shadow: 0 6px 20px rgba(124, 58, 237, 0.4) !important;
    }

    .advice-box {
        background: rgba(12, 11, 18, 0.75);
        border-left: 4px solid #7c3aed;
        padding: 12px 16px;
        border-radius: 10px;
        font-size: 0.88rem;
        line-height: 1.5;
        color: #e2e8f0;
    }

    .mono { font-family: 'JetBrains Mono', monospace; }
</style>
""", unsafe_allow_html=True)

# --- 1. FELSŐ FEJLÉC ---
now_str = datetime.now().strftime("%H:%M:%S")
st.markdown(f"""
<div class="top-nav-pill">
    <div style="display:flex; align-items:center; gap:16px;">
        <div style="width:38px; height:38px; border-radius:12px; background:linear-gradient(135deg,#7c3aed,#4f46e5); display:flex; align-items:center; justify-content:center; font-weight:800; font-size:0.95rem; color:#fff; letter-spacing:0.5px;">GL</div>
        <div>
            <span style="font-size:1.25rem; font-weight:700; letter-spacing:-0.3px;">Gazdag Leszek <span style="color:#a78bfa; font-weight:400;">Elemzői Iroda</span></span>
            <span style="display:block; font-size:0.73rem; color:#9ca3af;">Perzisztens ML Memória (.joblib) • 5x Visszacsatolási Tanulás • Portfóliókezelő</span>
        </div>
    </div>
    <div style="display:flex; align-items:center; gap:16px;">
        <span style="font-size:0.78rem; color:#9ca3af;"><span class="live-dot"></span>Utolsó szinkron: <b class="mono" style="color:#f3f4f6;">{now_str}</b></span>
        <span class="purple-badge">PERSISTENT AI BRAIN</span>
    </div>
</div>
""", unsafe_allow_html=True)

# --- 2. FELSŐ VEZÉRLŐPULT ---
top1, top2, top3, top4, top5 = st.columns(5)

with top1:
    with st.container(border=True):
        st.markdown('<span class="card-micro-label">Részvény Ticker</span>', unsafe_allow_html=True)
        ticker = st.text_input("Ticker", value="NVDA", label_visibility="collapsed").upper().strip()

with top2:
    with st.container(border=True):
        st.markdown('<span class="card-micro-label">Időtáv és Adatsűrűség</span>', unsafe_allow_html=True)
        strategy = st.selectbox(
            "Időtáv",
            [
                "Swing Trade (Napi chart • 2-6 hét)",
                "Daytrade Ultra (1 perces élő chart)",
                "Daytrade Pro (5 perces élő chart)",
                "Daytrade Normál (15 perces chart)",
                "Hosszú Táv (Napi/Heti • 1-3 év)"
            ],
            index=0,
            label_visibility="collapsed"
        )

with top3:
    with st.container(border=True):
        st.markdown('<span class="card-micro-label">ML Memória & Élő Adat</span>', unsafe_allow_html=True)
        with st.popover("ML Agy és Frissítés"):
            st.markdown("##### Perzisztens ML Memória Beállítások")
            auto_optimize = st.toggle("Grid Search + Perzisztens Random Forest", value=True)
            force_retrain = st.checkbox("ML Agy kényszerített újratanítása most", value=False)
            include_prepost = st.toggle("Pre-Market és After-Hours adatok", value=True)
            if st.button("Azonnali Piaci Frissítés", type="primary"):
                st.rerun()

with top4:
    with st.container(border=True):
        st.markdown(f'<span class="card-micro-label">Tőke (${portfolio_db.get("capital", 15000):,.0f})</span>', unsafe_allow_html=True)
        with st.popover("Tőke és Kockázat"):
            st.markdown("##### Pozícióméretező Kalkulátor")
            account_capital = st.number_input("Kereskedési tőke ($):", min_value=100.0, value=float(portfolio_db.get("capital", 15000.0)), step=500.0)
            risk_per_trade = st.slider("Max kockázat / kötés (%):", min_value=0.5, max_value=5.0, value=float(portfolio_db.get("risk_pct", 1.5)), step=0.25)
            portfolio_db["capital"] = account_capital
            portfolio_db["risk_pct"] = risk_per_trade

with top5:
    with st.container(border=True):
        st.markdown('<span class="card-micro-label">Elemző Motor</span>', unsafe_allow_html=True)
        with st.popover("AI Kulcs Beállítása"):
            st.markdown("##### Gemini API Kulcs")
            api_key = st.text_input("API Kulcs:", type="password")
            st.caption("[Ingyenes kulcs igénylése](https://aistudio.google.com/apikey)")

# --- 3. VALÓS IDEJŰ TŐZSDEI ADATLEKÉRŐ ---
def fetch_realtime_market_data(ticker_sym, period, interval, prepost_flag=True):
    stock = yf.Ticker(ticker_sym)
    use_prepost = prepost_flag if interval in ["1m", "5m", "15m"] else False
    df = stock.history(period=period, interval=interval, prepost=use_prepost)

    live_price = None
    try:
        fast = stock.fast_info
        live_price = float(fast['last_price'])
    except Exception:
        try:
            live_price = float(stock.info.get('regularMarketPrice') or stock.info.get('currentPrice'))
        except Exception:
            pass

    if not df.empty and live_price is not None and live_price > 0:
        last_idx = df.index[-1]
        df.loc[last_idx, 'Close'] = live_price
        if live_price > df.loc[last_idx, 'High']:
            df.loc[last_idx, 'High'] = live_price
        if live_price < df.loc[last_idx, 'Low']:
            df.loc[last_idx, 'Low'] = live_price

    try:
        info = stock.info
    except Exception:
        info = {}

    try:
        spy_df = yf.Ticker("SPY").history(period=period, interval=interval, prepost=use_prepost)
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

# --- 4. TECHNIKAI INDIKÁTOROK ÉS ML FEATURE ENGINEERING ---
def calculate_metrics(df):
    df = df.copy()
    for w in [10, 15, 20, 30, 50, 200]:
        df[f'SMA_{w}'] = df['Close'].rolling(window=w, min_periods=max(3, w//4)).mean()

    df['EMA_9'] = df['Close'].ewm(span=9, adjust=False).mean()
    df['EMA_12'] = df['Close'].ewm(span=12, adjust=False).mean()
    df['EMA_21'] = df['Close'].ewm(span=21, adjust=False).mean()
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

    rsi_min = df['RSI'].rolling(window=14, min_periods=5).min()
    rsi_max = df['RSI'].rolling(window=14, min_periods=5).max()
    stoch_denom = (rsi_max - rsi_min).replace(0, 1e-9)
    df['Stoch_RSI'] = (((df['RSI'] - rsi_min) / stoch_denom) * 100).fillna(50.0)

    std_20 = df['Close'].rolling(window=20, min_periods=5).std().fillna(0)
    df['BB_Upper'] = df['SMA_20'] + (std_20 * 2)
    df['BB_Lower'] = df['SMA_20'] - (std_20 * 2)
    df['BB_Width'] = ((df['BB_Upper'] - df['BB_Lower']) / df['SMA_20'].replace(0, 1e-9)) * 100

    high_diff = df['High'].diff()
    low_diff = -df['Low'].diff()
    plus_dm = np.where((high_diff > low_diff) & (high_diff > 0), high_diff, 0.0)
    minus_dm = np.where((low_diff > high_diff) & (low_diff > 0), low_diff, 0.0)

    tr = pd.concat([
        df['High'] - df['Low'],
        np.abs(df['High'] - df['Close'].shift()),
        np.abs(df['Low'] - df['Close'].shift())
    ], axis=1).max(axis=1)
    df['ATR'] = tr.rolling(window=14, min_periods=3).mean().bfill()

    atr_smooth = tr.ewm(alpha=1/14, min_periods=5, adjust=False).mean().replace(0, 1e-9)
    plus_di = 100 * (pd.Series(plus_dm, index=df.index).ewm(alpha=1/14, min_periods=5, adjust=False).mean() / atr_smooth)
    minus_di = 100 * (pd.Series(minus_dm, index=df.index).ewm(alpha=1/14, min_periods=5, adjust=False).mean() / atr_smooth)
    dx = (np.abs(plus_di - minus_di) / (plus_di + minus_di).replace(0, 1e-9)) * 100
    df['ADX'] = dx.ewm(alpha=1/14, min_periods=5, adjust=False).mean().fillna(20.0)

    obv_dir = np.where(df['Close'] > df['Close'].shift(1), df['Volume'], np.where(df['Close'] < df['Close'].shift(1), -df['Volume'], 0))
    df['OBV'] = pd.Series(obv_dir, index=df.index).cumsum()
    df['OBV_SMA_20'] = df['OBV'].rolling(window=20, min_periods=5).mean()
    df['Vol_SMA_20'] = df['Volume'].rolling(window=20, min_periods=3).mean().replace(0, 1).bfill()

    df['Dist_SMA20_Pct'] = ((df['Close'] - df['SMA_20']) / df['SMA_20'].replace(0, 1)) * 100
    df['Dist_SMA50_Pct'] = ((df['Close'] - df['SMA_50']) / df['SMA_50'].replace(0, 1)) * 100
    df['Vol_Ratio'] = df['Volume'] / df['Vol_SMA_20']
    df['Ret_5'] = df['Close'].pct_change(5).fillna(0) * 100

    if len(df) > 1 and (df.index[1] - df.index[0]).total_seconds() < 86400:
        df['TimeLabel'] = df.index.strftime('%m.%d %H:%M')
    else:
        df['TimeLabel'] = df.index.strftime('%Y-%m-%d')

    return df

# --- 5. PERZISZTENS ML MEMÓRIA (.JOBLIB) + VISSZACSATOLÁSI TANULÁS ---
def train_or_load_ml_brain(df, ticker_sym, interval_str, journal_list, horizon=5, force_retrain_flag=False):
    """
    1. Megnézi, van-e már mai, elmentett `.joblib` agy a lemezen. Ha van, betölti és azonnal jósol vele.
    2. Ha nincs (vagy újratanítást kértél), kombinálja a historikus gyertyákat a `prediction_journal.json`-ban
       rögzített valódi lezárt kötések tapasztalataival (5x-ös súllyal!), és elmenti az új agyat a lemezre.
    """
    ml_df = df.dropna(subset=FEATURE_COLS).copy()
    if len(ml_df) < 40:
        return {"prob_up": 50.0, "accuracy": 50.0, "importances": {}, "trained_samples": 0, "feedback_samples": 0, "horizon": horizon, "brain_file": "N/A"}

    brain_path = os.path.join(MODELS_DIR, f"{ticker_sym}_{interval_str}_brain.joblib")
    today_prefix = datetime.now().strftime("%Y-%m-%d")
    latest_features = ml_df[FEATURE_COLS].iloc[-1:].values

    # Ha létezik már mai betanított agy a lemezen és nem kértünk kényszerített újratanítást, betöltjük!
    if os.path.exists(brain_path) and not force_retrain_flag:
        try:
            saved_brain = joblib.load(brain_path)
            if str(saved_brain.get("updated_at", "")).startswith(today_prefix):
                clf = saved_brain["model"]
                prob_up = float(clf.predict_proba(latest_features)[0][1] * 100.0)
                return {
                    "prob_up": prob_up,
                    "accuracy": saved_brain.get("accuracy", 55.0),
                    "importances": saved_brain.get("importances", {}),
                    "trained_samples": saved_brain.get("trained_samples", len(ml_df)),
                    "feedback_samples": saved_brain.get("feedback_samples", 0),
                    "horizon": horizon,
                    "brain_file": os.path.basename(brain_path),
                    "updated_at": saved_brain.get("updated_at", "")
                }
        except Exception:
            pass

    # Újratanítás historikus adatokon + Napló visszacsatoláson (Feedback Loop)
    ml_df['Future_Close'] = ml_df['Close'].shift(-horizon)
    train_data = ml_df.dropna(subset=['Future_Close']).copy()
    train_data['Target'] = (train_data['Future_Close'] > train_data['Close']).astype(int)

    X_hist = train_data[FEATURE_COLS].values
    y_hist = train_data['Target'].values
    weights = np.ones(len(X_hist))

    # Naplózott valós tapasztalatok beolvasása 5x-ös tanulási súllyal
    feedback_X, feedback_y = [], []
    for entry in journal_list:
        if entry.get("Ticker") == ticker_sym and "Features" in entry and "Target_Outcome" in entry:
            feat_vec = [entry["Features"].get(c, 0.0) for c in FEATURE_COLS]
            feedback_X.append(feat_vec)
            feedback_y.append(int(entry["Target_Outcome"]))

    if feedback_X:
        X_all = np.vstack([X_hist, np.array(feedback_X)])
        y_all = np.concatenate([y_hist, np.array(feedback_y)])
        w_all = np.concatenate([weights, np.full(len(feedback_y), 5.0)])
    else:
        X_all, y_all, w_all = X_hist, y_hist, weights

    split_idx = int(len(X_hist) * 0.8)
    clf_eval = RandomForestClassifier(n_estimators=140, max_depth=6, min_samples_leaf=4, random_state=42)
    clf_eval.fit(X_hist[:split_idx], y_hist[:split_idx])
    test_acc = float(clf_eval.score(X_hist[split_idx:], y_hist[split_idx:]) * 100.0) if len(X_hist) > split_idx else 55.0

    clf_final = RandomForestClassifier(n_estimators=140, max_depth=6, min_samples_leaf=4, random_state=42)
    clf_final.fit(X_all, y_all, sample_weight=w_all)

    prob_up = float(clf_final.predict_proba(latest_features)[0][1] * 100.0)
    importances = {col: round(float(imp * 100), 1) for col, imp in zip(FEATURE_COLS, clf_final.feature_importances_)}
    importances = dict(sorted(importances.items(), key=lambda item: item[1], reverse=True))

    updated_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    try:
        joblib.dump({
            "model": clf_final,
            "accuracy": test_acc,
            "importances": importances,
            "trained_samples": len(X_all),
            "feedback_samples": len(feedback_y),
            "updated_at": updated_str
        }, brain_path)
    except Exception:
        pass

    return {
        "prob_up": prob_up,
        "accuracy": test_acc,
        "importances": importances,
        "trained_samples": len(X_all),
        "feedback_samples": len(feedback_y),
        "horizon": horizon,
        "brain_file": os.path.basename(brain_path),
        "updated_at": updated_str
    }

# --- 6. GRID SEARCH BACKTEST MOTOR ---
def simulate_single_strategy(bt, fast_sma_col, rsi_dip_buy, rsi_overbought_sell, stop_atr_mult, initial_cap=10000.0):
    closes = bt['Close'].values
    smas = bt[fast_sma_col].values
    macds = bt['MACD'].values
    sigs = bt['MACD_Signal'].values
    rsis = bt['RSI'].values
    atrs = bt['ATR'].values

    n = len(bt)
    positions = np.zeros(n)
    pos = 0
    entry_p = 0.0
    stop_p = 0.0
    trades = []

    for i in range(n):
        c_p = closes[i]
        if pos == 0:
            trend_buy = (c_p > smas[i]) and (macds[i] > sigs[i]) and (rsis[i] < (rsi_overbought_sell - 4))
            dip_buy = (rsis[i] < rsi_dip_buy)
            if trend_buy or dip_buy:
                pos = 1
                entry_p = c_p
                stop_p = c_p - (stop_atr_mult * atrs[i])
        else:
            new_stop = c_p - (stop_atr_mult * atrs[i])
            if new_stop > stop_p:
                stop_p = new_stop
            trend_sell = (c_p < smas[i]) and (macds[i] < sigs[i])
            ob_sell = (rsis[i] > rsi_overbought_sell)
            stop_hit = (c_p <= stop_p)
            if trend_sell or ob_sell or stop_hit:
                pos = 0
                trades.append((c_p - entry_p) / entry_p * 100.0)
        positions[i] = pos

    if pos == 1:
        trades.append((closes[-1] - entry_p) / entry_p * 100.0)

    mkt_ret = pd.Series(closes).pct_change().fillna(0).values
    pos_shifted = np.roll(positions, 1)
    pos_shifted[0] = 0
    strat_ret = pos_shifted * mkt_ret

    strat_eq = initial_cap * np.cumprod(1.0 + strat_ret)
    bh_eq = initial_cap * np.cumprod(1.0 + mkt_ret)

    strat_pct = ((strat_eq[-1] / initial_cap) - 1.0) * 100.0
    bh_pct = ((bh_eq[-1] / initial_cap) - 1.0) * 100.0
    win_rate = (sum(1 for t in trades if t > 0) / len(trades) * 100.0) if trades else 0.0

    roll_max = np.maximum.accumulate(strat_eq)
    dd = (strat_eq - roll_max) / roll_max * 100.0
    max_dd = float(np.min(dd))

    fitness = strat_pct + (win_rate * 0.15) - (abs(max_dd) * 0.6)
    if len(trades) == 0:
        fitness = -999.0

    curr_signal = "VÉTEL (Aktív Long)" if positions[-1] == 1 else "KIVÁRÁS / CASH"

    return {
        "strat_eq": strat_eq, "bh_eq": bh_eq, "strat_pct": float(strat_pct), "bh_pct": float(bh_pct),
        "win_rate": float(win_rate), "total_trades": len(trades), "max_dd": float(max_dd),
        "final_equity": float(strat_eq[-1]), "fitness": float(fitness), "curr_signal": curr_signal,
        "params": {"fast_sma": fast_sma_col, "rsi_buy": rsi_dip_buy, "rsi_sell": rsi_overbought_sell, "atr_stop": stop_atr_mult}
    }

def auto_learn_optimal_strategy(df, initial_cap=10000.0, run_grid=True):
    bt = df.dropna(subset=['SMA_20', 'RSI', 'MACD', 'MACD_Signal', 'ATR']).copy()
    if len(bt) < 25:
        return None

    baseline_res = simulate_single_strategy(bt, 'SMA_20', 32, 74, 2.0, initial_cap)
    if not run_grid:
        baseline_res['bt_df'] = bt
        baseline_res['baseline_pct'] = baseline_res['strat_pct']
        baseline_res['tested_combinations'] = 1
        baseline_res['leaderboard'] = []
        return baseline_res

    best_res = baseline_res
    leaderboard = []
    tested_count = 0

    for sma_c in ['SMA_10', 'SMA_15', 'SMA_20', 'SMA_30']:
        for rb in [28, 33, 38]:
            for rs in [70, 75, 80]:
                for atr_s in [1.6, 2.4]:
                    tested_count += 1
                    res = simulate_single_strategy(bt, sma_c, rb, rs, atr_s, initial_cap)
                    leaderboard.append({
                        "Trend Mozgóátlag": sma_c, "RSI Vétel (<)": rb, "RSI Kiszálló (>)": rs,
                        "ATR Stop": f"{atr_s}x", "Hozam (%)": round(res["strat_pct"], 2),
                        "Win Rate (%)": round(res["win_rate"], 1), "Max DD (%)": round(res["max_dd"], 2),
                        "Kötések": res["total_trades"], "Fitness": round(res["fitness"], 1)
                    })
                    if res["fitness"] > best_res["fitness"]:
                        best_res = res

    best_res['bt_df'] = bt
    best_res['baseline_pct'] = baseline_res['strat_pct']
    best_res['baseline_eq'] = baseline_res['strat_eq']
    best_res['tested_combinations'] = tested_count
    best_res['leaderboard'] = sorted(leaderboard, key=lambda x: x["Fitness"], reverse=True)[:10]
    return best_res

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

# --- 7. HIBRID QUANT + PERZISZTENS RANDOM FOREST PONTOZÓ MOTOR ---
def evaluate_quant_model(df, spy_df, strategy_mode, learned_res=None, ml_res=None):
    curr = df.iloc[-1]
    score = 50
    reasons = []
    rel_strength_pct = 0.0

    if ml_res and ml_res.get("trained_samples", 0) > 0:
        prob_up = ml_res["prob_up"]
        ml_acc = ml_res["accuracy"]
        fb_cnt = ml_res.get("feedback_samples", 0)
        top_feat = list(ml_res["importances"].keys())[0] if ml_res["importances"] else "RSI"
        if prob_up >= 60:
            score += 12
            reasons.append(f"**Perzisztens Random Forest ML — BIKÁS ({prob_up:.1f}% emelkedési esély):** A `{ml_res['trained_samples']}` gyertyán és `{fb_cnt}` visszacsatolt valós kötésen tanult modell (`{ml_res.get('brain_file')}`, teszt-pontosság: `{ml_acc:.1f}%`) emelkedést vár. Fő döntési faktor: `{top_feat}`.")
        elif prob_up <= 42:
            score -= 12
            reasons.append(f"**Perzisztens Random Forest ML — MEDVÉS ({prob_up:.1f}% emelkedési esély):** A mentett gépi tanulási agy szerint `{100-prob_up:.1f}%` eséllyel korrekció következik.")
        else:
            reasons.append(f"**Perzisztens Random Forest ML — SEMLEGES ({prob_up:.1f}% esély):** A modell nem lát szignifikáns statisztikai aszimmetriát.")

    if learned_res and "params" in learned_res:
        lp = learned_res["params"]
        opt_sma_col = lp["fast_sma"]
        opt_rsi_buy = lp["rsi_buy"]
        opt_rsi_sell = lp["rsi_sell"]
        atr_mult_stop = lp["atr_stop"]
        atr_mult_tp = round(atr_mult_stop * 1.8, 1)
        if learned_res["curr_signal"].startswith("VÉTEL"):
            score += 10
            reasons.append(f"**Grid Search Backtest Szabály — AKTÍV VÉTEL:** A 72 tesztből győztes stratégia (`{opt_sma_col}`, Win Rate: `{learned_res['win_rate']:.1f}%`) vételi pozícióban van.")
        else:
            score -= 6
    else:
        opt_sma_col, opt_rsi_buy, opt_rsi_sell, atr_mult_stop, atr_mult_tp = 'SMA_20', 32, 72, 2.0, 3.6

    if not spy_df.empty and len(spy_df) >= 20 and len(df) >= 20:
        s_ret = ((df['Close'].iloc[-1] / df['Close'].iloc[-20]) - 1) * 100
        m_ret = ((spy_df['Close'].iloc[-1] / spy_df['Close'].iloc[-20]) - 1) * 100
        rel_strength_pct = float(s_ret - m_ret)
        if rel_strength_pct > 2.0:
            score += 8
            reasons.append(f"**Intézményi Relatív Erő (Alpha: {rel_strength_pct:+.2f}%):** Felülteljesíti az S&P 500 indexet.")
        elif rel_strength_pct < -2.0:
            score -= 8
            reasons.append(f"**Relatív Alulteljesítés (Alpha: {rel_strength_pct:+.2f}%):** Gyengébb a piaci átlagnál.")

    opt_sma_val = float(curr[opt_sma_col])
    if curr['Close'] > opt_sma_val and curr['Close'] > curr['SMA_50']:
        score += 10
        reasons.append(f"**Adaptív Trend Pozitív:** Árfolyam a tanult `{opt_sma_col}` (`{opt_sma_val:.2f}`) és az `SMA_50` (`{curr['SMA_50']:.2f}`) felett.")
    elif curr['Close'] < opt_sma_val:
        score -= 10
        reasons.append(f"**Adaptív Trend Törés:** Árfolyam a tanult `{opt_sma_col}` (`{opt_sma_val:.2f}`) alatt.")

    if curr['MACD'] > curr['MACD_Signal']:
        score += 8
        reasons.append(f"**Pozitív MACD Momentum:** MACD (`{curr['MACD']:.3f}`) a szignálvonal felett.")
    else:
        score -= 8
        reasons.append("**Negatív MACD Momentum:** MACD a szignálvonal alatt.")

    rsi = float(curr['RSI'])
    if rsi <= opt_rsi_buy:
        score += 12
        reasons.append(f"**Adaptív Vételi Zóna (RSI: {rsi:.1f} <= {opt_rsi_buy}):** Túladott fordulózóna.")
    elif rsi >= opt_rsi_sell:
        score -= 12
        reasons.append(f"**Adaptív Profitrealizálási Zóna (RSI: {rsi:.1f} >= {opt_rsi_sell}):** Túlhevült zóna.")

    score = max(0, min(100, int(round(score))))
    if score >= 75: verdict = "ERŐS VÉTEL"
    elif score >= 60: verdict = "VÉTEL"
    elif score >= 45: verdict = "TARTÁS"
    elif score >= 30: verdict = "ÓVATOSSÁG"
    else: verdict = "ELADÁS"

    return score, verdict, reasons, atr_mult_stop, atr_mult_tp, rel_strength_pct

def generate_short_portfolio_advice(curr_price, buy_price, score, verdict, support, resistance, stop_loss, take_profit, ml_prob=50.0):
    pnl_pct = ((curr_price - buy_price) / buy_price) * 100
    ml_tag = f" [ML Emelkedési Esély: {ml_prob:.0f}%]"

    if pnl_pct >= 15:
        if score < 50 or ml_prob < 45:
            return f"RÉSZPROFIT KIVÉTEL: Szép nyereség ({pnl_pct:+.1f}%), de a modell lassulást lát ({score}/100){ml_tag}. Zárd le a 30-50%-át, Stop-Loss felhúzása ${max(buy_price*1.04, support):.2f}-ra!"
        return f"NYERESÉG FUTTATÁSA: Erős trend ({score}/100) és komoly profit ({pnl_pct:+.1f}%){ml_tag}. Célár: ${take_profit:.2f}, csúszó Stop-Loss: ${max(buy_price*1.02, support):.2f}."
    elif 0 <= pnl_pct < 15:
        if score >= 60 and ml_prob >= 52:
            return f"TARTÁS / BŐVÍTÉS: Pluszban a kötés ({pnl_pct:+.1f}%) és a gépi tanulás is bikás ({score}/100){ml_tag}. Célár: ${take_profit:.2f}, Stop: ${stop_loss:.2f}."
        return f"NULLSZALDÓ VÉDELME: Enyhe plusz ({pnl_pct:+.1f}%), de vegyes kilátások ({score}/100){ml_tag}. Védő Stop-Loss a bekerülési árra (${buy_price:.2f})!"
    elif -8 <= pnl_pct < 0:
        if score >= 60 or ml_prob >= 60:
            return f"KITARTÁS / RÁVÁSÁRLÁSI ZÓNA: Kis mínusz ({pnl_pct:+.1f}%), de az ML modell felpattanást vár ({score}/100){ml_tag}. Támasz: ${support:.2f}."
        return f"SZOROS KOCKÁZATKEZELÉS: Enyhe mínusz ({pnl_pct:+.1f}%) gyenge momentummal ({score}/100){ml_tag}. Kritikus támasz: ${support:.2f}!"
    else:
        if score < 45:
            return f"VESZTESÉGVÁGÁS / TILOS RÁÁTLAGOLNI: Jelentős mínusz ({pnl_pct:+.1f}%) és medvés kép ({score}/100){ml_tag}. Ne átlagolj lefelé ${resistance:.2f} alatt!"
        return f"STABILIZÁCIÓRA VÁRVA: Mélyebb mínusz ({pnl_pct:+.1f}%), de javuló mutatók ({score}/100){ml_tag}. Várj megerősítésre!"

# --- FŐ FUTTATÁS ---
if ticker:
    is_daytrade = "Daytrade" in strategy
    if "1 perces" in strategy:
        yf_period, yf_interval = "5d", "1m"
    elif "5 perces" in strategy:
        yf_period, yf_interval = "1mo", "5m"
    elif "15 perces" in strategy:
        yf_period, yf_interval = "1mo", "15m"
    elif "Swing" in strategy:
        yf_period, yf_interval = "1y", "1d"
    else:
        yf_period, yf_interval = "2y", "1d"

    with st.spinner(f"Valós idejű adatok és Perzisztens ML Agy ({ticker}) betöltése..."):
        df, fundamentals, spy_df, vix_val = fetch_realtime_market_data(ticker, yf_period, yf_interval, include_prepost)

        if df.empty or len(df) < 25:
            st.error(f"Nem található elegendő adat a(z) '{ticker}' szimbólumhoz.")
        else:
            df = calculate_metrics(df)
            learned_bt = auto_learn_optimal_strategy(df, initial_cap=account_capital, run_grid=auto_optimize)
            ml_model_res = train_or_load_ml_brain(df, ticker, yf_interval, journal_db, horizon=5, force_retrain_flag=force_retrain)

            plot_df = df.tail(120).copy()
            curr = df.iloc[-1]
            prev = df.iloc[-2]
            change_pct = float(((curr['Close'] - prev['Close']) / prev['Close']) * 100)

            support_1 = float(df['Low'].tail(25).min())
            resistance_1 = float(df['High'].tail(25).max())
            vp_df, poc_price = calculate_volume_profile(df)

            score, verdict, reasons, mult_stop, mult_tp, alpha_pct = evaluate_quant_model(df, spy_df, strategy, learned_bt, ml_model_res)
            atr = float(curr['ATR']) if not np.isnan(curr['ATR']) and curr['ATR'] > 0 else float(curr['Close'] * 0.015)
            stop_loss = float(curr['Close'] - (mult_stop * atr))
            take_profit = float(curr['Close'] + (mult_tp * atr))

            max_risk_money = account_capital * (risk_per_trade / 100.0)
            risk_per_share = max(0.01, curr['Close'] - stop_loss)
            recommended_shares = int(max_risk_money // risk_per_share)

            active_holding = portfolio_db.get("holdings", {}).get(ticker)
            has_position = active_holding is not None
            avg_buy_price = float(active_holding["price"]) if has_position else 0.0
            shares_qty = float(active_holding["qty"]) if has_position else 0.0

            # --- MÁSODIK SOR: 5 BENTO METRIKA KÁRTYA ---
            k1, k2, k3, k4, k5 = st.columns(5)

            with k1:
                with st.container(border=True):
                    pill_cls = "card-sub-pill" if change_pct >= 0 else "card-sub-pill-warn"
                    st.markdown(f"""
                        <span class="card-micro-label"><span class="live-dot"></span>Élő Árfolyam ({yf_interval})</span>
                        <div class="card-big-value">${curr['Close']:.2f}</div>
                        <span class="{pill_cls}">{change_pct:+.2f}% | ATR: {atr:.2f}</span>
                    """, unsafe_allow_html=True)
                    with st.popover("Ár és Volatilitás"):
                        st.markdown(f"**Valós idejű ár:** `${curr['Close']:.2f}`\n\n**Utolsó gyertya:** `{curr['TimeLabel']}`\n\n**ATR (14):** `${atr:.2f}` | **VIX:** `{vix_val:.1f}`")

            with k2:
                with st.container(border=True):
                    pill_cls = "card-sub-pill" if score >= 50 else "card-sub-pill-warn"
                    st.markdown(f"""
                        <span class="card-micro-label">Hibrid ML + Quant Index</span>
                        <div class="card-big-value">{score} / 100</div>
                        <span class="{pill_cls}">{verdict} • ML Esély: {ml_model_res['prob_up']:.0f}%</span>
                    """, unsafe_allow_html=True)
                    with st.popover("Perzisztens ML Agy"):
                        st.markdown(f"""
                        **Mentett ML Agy (`{ml_model_res.get('brain_file')}`)**
                        - **Utolsó tanítás:** `{ml_model_res.get('updated_at', 'Most')}`
                        - **Tanított minták:** `{ml_model_res['trained_samples']} gyertya` + `{ml_model_res.get('feedback_samples', 0)} valós visszacsatolt kötés (5x súllyal)`
                        - **Out-of-Sample pontosság:** `{ml_model_res['accuracy']:.1f}%`
                        """)

            with k3:
                with st.container(border=True):
                    pill_cls = "card-sub-pill" if alpha_pct >= 0 else "card-sub-pill-warn"
                    st.markdown(f"""
                        <span class="card-micro-label">Alpha vs S&P 500</span>
                        <div class="card-big-value">{alpha_pct:+.1f}%</div>
                        <span class="{pill_cls}">RSI: {curr['RSI']:.1f} | ADX: {curr['ADX']:.0f}</span>
                    """, unsafe_allow_html=True)
                    with st.popover("Relatív Erő és Oszcillátor"):
                        st.markdown(f"**Alpha (`{alpha_pct:+.2f}%`):** S&P 500-hoz mért felülteljesítés.\n\n**RSI (`{curr['RSI']:.1f}`)** | **StochRSI (`{curr['Stoch_RSI']:.0f}%`)**")

            with k4:
                with st.container(border=True):
                    st.markdown(f"""
                        <span class="card-micro-label">Okos Pénz POC / Szintek</span>
                        <div class="card-big-value">${poc_price:.2f}</div>
                        <span class="card-sub-pill">S1: {support_1:.1f} | R1: {resistance_1:.1f}</span>
                    """, unsafe_allow_html=True)
                    with st.popover("POC és Támaszok"):
                        st.markdown(f"**Point of Control (`${poc_price:.2f}`):** Legmagasabb intézményi kötési zóna.\n\n**Támasz:** `${support_1:.2f}` | **Ellenállás:** `${resistance_1:.2f}`")

            with k5:
                with st.container(border=True):
                    if has_position:
                        pnl_tot = (curr['Close'] - avg_buy_price) * shares_qty
                        pnl_pct = ((curr['Close'] - avg_buy_price) / avg_buy_price) * 100
                        pill_cls = "card-sub-pill" if pnl_pct >= 0 else "card-sub-pill-warn"
                        st.markdown(f"""
                            <span class="card-micro-label">Saját {ticker} Pozíció</span>
                            <div class="card-big-value">${pnl_tot:+.1f}</div>
                            <span class="{pill_cls}">{pnl_pct:+.2f}% ({shares_qty:g} db)</span>
                        """, unsafe_allow_html=True)
                        with st.popover("Pozícióm Terve"):
                            st.markdown(f"**Pozíció:** `{shares_qty:g} db` @ `${avg_buy_price:.2f}`\n\n**Tanult Stop-Loss:** `${max(stop_loss, support_1):.2f}`\n\n**Célár:** `${take_profit:.2f}`")
                    else:
                        st.markdown(f"""
                            <span class="card-micro-label">Optimális Méret</span>
                            <div class="card-big-value">{recommended_shares} db</div>
                            <span class="card-sub-pill">Cél: {take_profit:.1f} | Stop: {stop_loss:.1f}</span>
                        """, unsafe_allow_html=True)
                        with st.popover("Pozícióméretező"):
                            st.markdown(f"**{risk_per_trade}% kockázat (`${max_risk_money:.0f}`) mellett:**\n\n`{recommended_shares} db` részvény vehető `${stop_loss:.2f}` Stop-Loss mellett.")

            st.write("")
            # --- 6 OSZLOPOS FALTÓL FALIG NAVIGÁCIÓS SÁV ---
            nav_options = [
                "Szétválasztott Chartok",
                "Saját Portfólió",
                "Önfejlesztő Backtest",
                "ML Öntanuló Labor",
                "Watchlist Radar",
                "AI Elemző és Hírek"
            ]
            nav_cols = st.columns(6)
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
                opt_sma_name = learned_bt["params"]["fast_sma"]

                with st.container(border=True):
                    st.markdown(f"#### 1. Valós Idejű Árfolyam és Tanult Trendvonal ({ticker} • {yf_interval} • Győztes SMA: {opt_sma_name})")
                    fig_price = go.Figure()
                    fig_price.add_trace(go.Candlestick(
                        x=x_vals, open=plot_df['Open'], high=plot_df['High'], low=plot_df['Low'], close=plot_df['Close'],
                        name="Árfolyam", increasing_line_color='#10b981', decreasing_line_color='#f43f5e'
                    ))
                    fig_price.add_trace(go.Scatter(x=x_vals, y=plot_df[opt_sma_name], line=dict(color='#38bdf8', width=2.2), name=f"Tanult {opt_sma_name}"))
                    fig_price.add_trace(go.Scatter(x=x_vals, y=plot_df['SMA_50'], line=dict(color='#a855f7', width=1.8), name="SMA 50"))
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
                        rb_lvl = learned_bt["params"]["rsi_buy"]
                        rs_lvl = learned_bt["params"]["rsi_sell"]
                        st.markdown(f"##### 2. Különálló RSI (Tanult küszöbök: {rb_lvl} / {rs_lvl}) és StochRSI")
                        fig_rsi = go.Figure()
                        fig_rsi.add_trace(go.Scatter(
                            x=x_vals, y=plot_df['RSI'], line=dict(color='#a855f7', width=2.2),
                            fill='tozeroy', fillcolor='rgba(168, 85, 247, 0.09)', name="RSI (14)"
                        ))
                        fig_rsi.add_trace(go.Scatter(x=x_vals, y=plot_df['Stoch_RSI'], line=dict(color='#38bdf8', width=1.2, dash='dot'), name="Stoch RSI"))
                        fig_rsi.add_hline(y=rs_lvl, line_dash="dash", line_color="#f43f5e", annotation_text=f"Tanult Kiszálló ({rs_lvl})")
                        fig_rsi.add_hline(y=rb_lvl, line_dash="dash", line_color="#10b981", annotation_text=f"Tanult Vétel ({rb_lvl})")
                        fig_rsi.update_layout(
                            height=250, template="plotly_dark", xaxis=dict(type='category', nticks=8),
                            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(17,16,25,0.6)",
                            margin=dict(l=10, r=10, t=10, b=10), yaxis=dict(range=[0, 100]),
                            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
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

            # =========================================================================
            # 2. NÉZET: SAJÁT PORTFÓLIÓ
            # =========================================================================
            elif active_view == "Saját Portfólió":
                p_left, p_right = st.columns([1.25, 2.75])

                with p_left:
                    with st.container(border=True):
                        st.markdown("#### Pozíció Hozzáadása / Frissítése")
                        new_sym = st.text_input("Ticker szimbólum:", value=ticker).upper().strip()
                        default_p = float(portfolio_db["holdings"].get(new_sym, {}).get("price", curr['Close']))
                        default_q = float(portfolio_db["holdings"].get(new_sym, {}).get("qty", 10.0))
                        new_price = st.number_input("Átlagos bekerülési ár ($):", min_value=0.01, value=default_p, step=0.5)
                        new_qty = st.number_input("Darabszám (db):", min_value=0.01, value=default_q, step=1.0)

                        btn_c1, btn_c2 = st.columns(2)
                        with btn_c1:
                            if st.button("Mentés a Portfólióba", type="primary"):
                                portfolio_db["holdings"][new_sym] = {"price": new_price, "qty": new_qty}
                                save_portfolio(portfolio_db)
                                st.success(f"{new_sym} elmentve!")
                                st.rerun()
                        with btn_c2:
                            if st.button("Törlés a listából"):
                                if new_sym in portfolio_db["holdings"]:
                                    del portfolio_db["holdings"][new_sym]
                                    save_portfolio(portfolio_db)
                                    st.rerun()

                        st.markdown("---")
                        st.download_button(
                            label="Portfólió Letöltése (JSON)",
                            data=json.dumps(portfolio_db, indent=2),
                            file_name="gazdag_leszek_portfolio.json",
                            mime="application/json",
                            use_container_width=True
                        )

                with p_right:
                    holdings = portfolio_db.get("holdings", {})
                    if not holdings:
                        with st.container(border=True):
                            st.info("Még nincs elmentett részvény a portfóliódban.")
                    else:
                        pf_rows = []
                        tot_invested = 0.0
                        tot_current = 0.0

                        with st.spinner("Portfólió pozíciók élő árazása és Perzisztens ML Agyak futtatása..."):
                            for sym_h, h_data in holdings.items():
                                try:
                                    h_df, _, _, _ = fetch_realtime_market_data(sym_h, "1y", "1d", prepost_flag=True)
                                    if not h_df.empty and len(h_df) >= 35:
                                        h_df = calculate_metrics(h_df)
                                        h_learned = auto_learn_optimal_strategy(h_df, initial_cap=account_capital, run_grid=True)
                                        h_ml = train_or_load_ml_brain(h_df, sym_h, "1d", journal_db, horizon=5, force_retrain_flag=False)
                                        h_curr = h_df.iloc[-1]
                                        live_p = float(h_curr['Close'])
                                        b_price = float(h_data['price'])
                                        q_val = float(h_data['qty'])

                                        inv_val = b_price * q_val
                                        cur_val = live_p * q_val
                                        pnl_d = cur_val - inv_val
                                        pnl_p = ((live_p - b_price) / b_price) * 100

                                        tot_invested += inv_val
                                        tot_current += cur_val

                                        h_sup = float(h_df['Low'].tail(20).min())
                                        h_res = float(h_df['High'].tail(20).max())
                                        h_atr = float(h_curr['ATR'])
                                        h_sc, h_verd, _, m_st, m_tp, _ = evaluate_quant_model(h_df, spy_df, "Swing", h_learned, h_ml)
                                        h_stop = live_p - (m_st * h_atr)
                                        h_tp = live_p + (m_tp * h_atr)

                                        short_adv = generate_short_portfolio_advice(
                                            live_p, b_price, h_sc, h_verd, h_sup, h_res, h_stop, h_tp, h_ml["prob_up"]
                                        )

                                        pf_rows.append({
                                            "sym": sym_h, "qty": q_val, "buy": b_price, "live": live_p,
                                            "cur_val": cur_val, "pnl_d": pnl_d, "pnl_p": pnl_p,
                                            "score": h_sc, "verdict": h_verd, "ml_prob": h_ml["prob_up"],
                                            "stop": h_stop, "tp": h_tp, "advice": short_adv
                                        })
                                except Exception:
                                    pass

                        tot_pnl = tot_current - tot_invested
                        tot_pnl_pct = ((tot_current - tot_invested) / tot_invested * 100) if tot_invested > 0 else 0.0

                        s1, s2, s3 = st.columns(3)
                        with s1:
                            with st.container(border=True):
                                st.markdown(f'<span class="card-micro-label">Portfólió Élő Értéke</span><div class="card-big-value">${tot_current:,.2f}</div><span class="card-sub-pill">Befektetve: ${tot_invested:,.2f}</span>', unsafe_allow_html=True)
                        with s2:
                            with st.container(border=True):
                                p_cls = "card-sub-pill" if tot_pnl >= 0 else "card-sub-pill-warn"
                                st.markdown(f'<span class="card-micro-label">Összesített P&L Eredmény</span><div class="card-big-value">${tot_pnl:+,.2f}</div><span class="{p_cls}">{tot_pnl_pct:+.2f}% hozam</span>', unsafe_allow_html=True)
                        with s3:
                            with st.container(border=True):
                                st.markdown(f'<span class="card-micro-label">Aktív Pozíciók Száma</span><div class="card-big-value">{len(pf_rows)} db</div><span class="card-sub-pill">Perzisztens ML kontroll</span>', unsafe_allow_html=True)

                        for item in pf_rows:
                            with st.container(border=True):
                                top_r1, top_r2, top_r3, top_r4 = st.columns([1.2, 1.3, 1.3, 1.2])
                                p_badge = "card-sub-pill" if item['pnl_p'] >= 0 else "card-sub-pill-warn"
                                q_badge = "card-sub-pill" if item['score'] >= 55 else "card-sub-pill-warn"

                                with top_r1:
                                    st.markdown(f"<span class='card-micro-label'>Ticker & Mennyiség</span><div class='card-big-value' style='font-size:1.3rem;'>{item['sym']} <span style='font-size:0.85rem; color:#9ca3af;'>({item['qty']:g} db)</span></div>", unsafe_allow_html=True)
                                with top_r2:
                                    st.markdown(f"<span class='card-micro-label'>Bekerülési vs Élő Ár</span><div class='card-big-value' style='font-size:1.25rem;'>${item['buy']:.2f} → ${item['live']:.2f}</div>", unsafe_allow_html=True)
                                with top_r3:
                                    st.markdown(f"<span class='card-micro-label'>Saját Eredmény (P&L)</span><div><span class='{p_badge}' style='font-size:0.9rem;'>${item['pnl_d']:+,.2f} ({item['pnl_p']:+.2f}%)</span></div>", unsafe_allow_html=True)
                                with top_r4:
                                    st.markdown(f"<span class='card-micro-label'>Hibrid ML + Quant</span><div><span class='{q_badge}' style='font-size:0.85rem;'>{item['score']}/100 • {item['verdict']}</span></div>", unsafe_allow_html=True)

                                st.markdown(f"""
                                <div class="advice-box">
                                    <b>Közvetlen Pozíciójavaslat:</b> {item['advice']}<br>
                                    <span style="font-size:0.8rem; color:#9ca3af;">Tanult Stop-Loss: <b class="mono" style="color:#fb7185;">${item['stop']:.2f}</b> &nbsp;|&nbsp; Célár: <b class="mono" style="color:#34d399;">${item['tp']:.2f}</b> &nbsp;|&nbsp; Pozíció értéke: <b class="mono">${item['cur_val']:,.2f}</b></span>
                                </div>
                                """, unsafe_allow_html=True)

            # =========================================================================
            # 3. NÉZET: ÖNFEJLESZTŐ BACKTEST
            # =========================================================================
            elif active_view == "Önfejlesztő Backtest":
                lp = learned_bt["params"]
                improvement = learned_bt["strat_pct"] - learned_bt["baseline_pct"]

                b1, b2, b3, b4 = st.columns(4)
                with b1:
                    with st.container(border=True):
                        st.markdown(f'<span class="card-micro-label">Tanult Modell Hozama</span><div class="card-big-value">{learned_bt["strat_pct"]:+.2f}%</div><span class="card-sub-pill">Alap modell felett: {improvement:+.2f}%</span>', unsafe_allow_html=True)
                with b2:
                    with st.container(border=True):
                        st.markdown(f'<span class="card-micro-label">Buy & Hold Hozam</span><div class="card-big-value">{learned_bt["bh_pct"]:+.2f}%</div><span class="card-sub-pill">Végtőke: ${learned_bt["final_equity"]:,.0f}</span>', unsafe_allow_html=True)
                with b3:
                    with st.container(border=True):
                        st.markdown(f'<span class="card-micro-label">Tanult Találati Arány</span><div class="card-big-value">{learned_bt["win_rate"]:.1f}%</div><span class="card-sub-pill">{learned_bt["total_trades"]} kötés ({learned_bt["tested_combinations"]} tesztből)</span>', unsafe_allow_html=True)
                with b4:
                    with st.container(border=True):
                        st.markdown(f'<span class="card-micro-label">Megtanult Optimális Szabály</span><div class="card-big-value" style="font-size:1.15rem;">{lp["fast_sma"]} • RSI {lp["rsi_buy"]}/{lp["rsi_sell"]}</div><span class="card-sub-pill">Stop: {lp["atr_stop"]}x ATR | DD: {learned_bt["max_dd"]:.1f}%</span>', unsafe_allow_html=True)

                with st.container(border=True):
                    st.markdown(f"#### Önfejlesztő Tőkegörbe: Tanult Stratégia vs. Alap Stratégia vs. Buy & Hold (${account_capital:,.0f})")
                    bt_df = learned_bt['bt_df']
                    fig_bt = go.Figure()
                    fig_bt.add_trace(go.Scatter(
                        x=bt_df['TimeLabel'], y=learned_bt['strat_eq'], line=dict(color='#10b981', width=2.6),
                        fill='tozeroy', fillcolor='rgba(16,185,129,0.08)', name="1. Önfejlesztő (Tanult) Modell"
                    ))
                    if 'baseline_eq' in learned_bt:
                        fig_bt.add_trace(go.Scatter(
                            x=bt_df['TimeLabel'], y=learned_bt['baseline_eq'], line=dict(color='#a855f7', width=1.8, dash='dash'),
                            name="2. Fix Alapmodell (SMA20 / RSI 32-74)"
                        ))
                    fig_bt.add_trace(go.Scatter(
                        x=bt_df['TimeLabel'], y=learned_bt['bh_eq'], line=dict(color='#6b7280', width=1.6, dash='dot'),
                        name="3. Buy & Hold (Sima Tartás)"
                    ))
                    fig_bt.update_layout(
                        height=400, template="plotly_dark", xaxis=dict(type='category', nticks=10),
                        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(17,16,25,0.6)",
                        margin=dict(l=10, r=10, t=15, b=10), yaxis_title="Portfólió Érték ($)", hovermode="x unified",
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                    )
                    st.plotly_chart(fig_bt, use_container_width=True)

            # =========================================================================
            # 4. NÉZET: ML ÖNTANULÓ LABOR & VISSZACSATOLÁSI NAPLÓ
            # =========================================================================
            elif active_view == "ML Öntanuló Labor":
                ml_c1, ml_c2 = st.columns([1.4, 2.2])

                with ml_c1:
                    with st.container(border=True):
                        st.markdown(f"#### Perzisztens ML Agy (`{ml_model_res.get('brain_file')}`)")
                        st.caption(f"Tanított gyertyák: `{ml_model_res['trained_samples']}` | Visszacsatolt valós kötések (5x súllyal): `{ml_model_res.get('feedback_samples', 0)}` | Utolsó mentés: `{ml_model_res.get('updated_at', 'Most')}`")
                        imp_df = pd.DataFrame({
                            "Indikátor": list(ml_model_res["importances"].keys()),
                            "Súly (%)": list(ml_model_res["importances"].values())
                        })
                        fig_imp = go.Figure(go.Bar(
                            x=imp_df["Súly (%)"], y=imp_df["Indikátor"], orientation='h',
                            marker=dict(color='#7c3aed', line=dict(color='#a78bfa', width=1))
                        ))
                        fig_imp.update_layout(
                            height=270, template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
                            plot_bgcolor="rgba(17,16,25,0.6)", margin=dict(l=10, r=10, t=10, b=10),
                            yaxis=dict(autorange="reversed"), xaxis_title="Döntési Fontosság (%)"
                        )
                        st.plotly_chart(fig_imp, use_container_width=True)

                        st.markdown("---")
                        st.markdown("##### Élő Előrejelzés Rögzítése (Feature Vektorral)")
                        if st.button(f"Mai {ticker} Jelzés és Indikátorok Naplózása", type="primary"):
                            journal_db.append({
                                "Dátum": datetime.now().strftime("%Y-%m-%d %H:%M"),
                                "Ticker": ticker,
                                "Időtáv": yf_interval,
                                "Rögzített Ár": round(float(curr['Close']), 2),
                                "Quant Pont": score,
                                "ML Esély (%)": round(ml_model_res["prob_up"], 1),
                                "Ajánlás": verdict,
                                "Célár": round(take_profit, 2),
                                "Stop-Loss": round(stop_loss, 2),
                                "Aktuális Ár": round(float(curr['Close']), 2),
                                "Valós Hozam (%)": 0.0,
                                "Státusz": "Folyamatban",
                                "Features": {c: round(float(curr[c]), 4) for c in FEATURE_COLS}
                            })
                            save_journal(journal_db)
                            st.success("Előrejelzés és a 9 indikátor-állapot rögzítve a tanuló naplóba!")
                            st.rerun()

                with ml_c2:
                    with st.container(border=True):
                        st.markdown("#### Visszacsatolt Forward-Test Napló (Feedback Loop)")
                        st.caption("Amikor rákattintasz a kiértékelésre, a rendszer ellenőrzi az árakat, a lezárt kötésekből pedig 5-szörös súllyal újratanítja a `.joblib` agyakat!")

                        j_btn1, j_btn2 = st.columns(2)
                        with j_btn1:
                            if st.button("Napló Kiértékelése és ML Agyak Újratanítása Most", type="primary"):
                                for entry in journal_db:
                                    try:
                                        chk_df, _, _, _ = fetch_realtime_market_data(entry["Ticker"], "5d", "1d", True)
                                        if not chk_df.empty:
                                            now_p = float(chk_df['Close'].iloc[-1])
                                            entry["Aktuális Ár"] = round(now_p, 2)
                                            ret_p = ((now_p - entry["Rögzített Ár"]) / entry["Rögzített Ár"]) * 100.0
                                            entry["Valós Hozam (%)"] = round(ret_p, 2)
                                            if now_p >= entry["Célár"]:
                                                entry["Státusz"] = "SIKERES (Célár elérve)"
                                                entry["Target_Outcome"] = 1
                                            elif now_p <= entry["Stop-Loss"]:
                                                entry["Státusz"] = "SIKERTELEN (Stop-Loss)"
                                                entry["Target_Outcome"] = 0
                                            else:
                                                entry["Státusz"] = "Nyitott (+)" if ret_p >= 0 else "Nyitott (-)"
                                    except Exception:
                                        pass
                                save_journal(journal_db)
                                train_or_load_ml_brain(df, ticker, yf_interval, journal_db, horizon=5, force_retrain_flag=True)
                                st.rerun()

                        with j_btn2:
                            st.download_button(
                                label="Tanuló Napló Mentése (JSON)",
                                data=json.dumps(journal_db, indent=2),
                                file_name="ml_prediction_journal.json",
                                mime="application/json",
                                use_container_width=True
                            )

                        if journal_db:
                            display_cols = [c for c in pd.DataFrame(journal_db).columns if c not in ["Features", "Target_Outcome"]]
                            j_df = pd.DataFrame(journal_db)[display_cols]
                            avg_real_ret = j_df["Valós Hozam (%)"].mean()
                            pos_count = sum(1 for r in journal_db if r["Valós Hozam (%)"] > 0)
                            live_wr = (pos_count / len(journal_db)) * 100.0
                            st.markdown(f"**Naplózott kötések:** `{len(journal_db)} db` &nbsp;|&nbsp; **Élő találati arány:** `{live_wr:.1f}%` &nbsp;|&nbsp; **Átlagos valós hozam:** `{avg_real_ret:+.2f}%`")
                            st.dataframe(j_df[::-1], use_container_width=True, hide_index=True)
                        else:
                            st.info("Még nincs rögzített előrejelzés.")

            # =========================================================================
            # 5. NÉZET: WATCHLIST RADAR
            # =========================================================================
            elif active_view == "Watchlist Radar":
                with st.container(border=True):
                    st.markdown("#### Többrészvényes Watchlist Szkenner (Perzisztens ML + Quant)")
                    wl_col1, wl_col2 = st.columns([3.5, 1.2])
                    with wl_col1:
                        wl_input = st.text_input("Figyelt Tickerek:", value="NVDA, AAPL, MSFT, TSLA, META, AMZN, GOOGL, AMD", label_visibility="collapsed")
                    with wl_col2:
                        run_wl = st.button("Watchlist Szkennelése", type="primary")

                    if run_wl:
                        tickers_list = [t.strip().upper() for t in wl_input.split(",") if t.strip()]
                        rows = []
                        prog = st.progress(0)
                        for idx_t, sym in enumerate(tickers_list):
                            try:
                                w_df, _, _, _ = fetch_realtime_market_data(sym, "1y", "1d", prepost_flag=True)
                                if not w_df.empty and len(w_df) >= 40:
                                    w_df = calculate_metrics(w_df)
                                    w_learn = auto_learn_optimal_strategy(w_df, initial_cap=account_capital, run_grid=True)
                                    w_ml = train_or_load_ml_brain(w_df, sym, "1d", journal_db, horizon=5, force_retrain_flag=False)
                                    sc, verd, _, _, _, alp = evaluate_quant_model(w_df, spy_df, "Swing", w_learn, w_ml)
                                    c_row = w_df.iloc[-1]
                                    p_row = w_df.iloc[-2]
                                    chg = ((c_row['Close'] - p_row['Close']) / p_row['Close']) * 100
                                    rows.append({
                                        "Ticker": sym, "Ár": float(c_row['Close']), "Napi %": float(chg),
                                        "Quant Pont": int(sc), "Ajánlás": verd, "ML Esély": float(w_ml['prob_up']),
                                        "Win Rate": float(w_learn['win_rate'])
                                    })
                            except Exception:
                                pass
                            prog.progress((idx_t + 1) / len(tickers_list))

                        if rows:
                            rows = sorted(rows, key=lambda x: x["Quant Pont"], reverse=True)
                            grid_cols = st.columns(4)
                            for i, r_item in enumerate(rows):
                                with grid_cols[i % 4]:
                                    with st.container(border=True):
                                        p_cls = "card-sub-pill" if r_item["Quant Pont"] >= 55 else "card-sub-pill-warn"
                                        st.markdown(f"""
                                            <span class="card-micro-label">{r_item['Ticker']} • ML Esély: {r_item['ML Esély']:.0f}%</span>
                                            <div class="card-big-value">${r_item['Ár']:.2f} <span style="font-size:0.9rem; color:#9ca3af;">({r_item['Napi %']:+.1f}%)</span></div>
                                            <span class="{p_cls}">Pont: {r_item['Quant Pont']}/100 • {r_item['Ajánlás']}</span>
                                            <div style="font-size:0.76rem; color:#9ca3af; margin-top:4px;">Backtest Win Rate: {r_item['Win Rate']:.0f}%</div>
                                        """, unsafe_allow_html=True)

            # =========================================================================
            # 6. NÉZET: AI ELEMZŐ ÉS HÍREK
            # =========================================================================
            elif active_view == "AI Elemző és Hírek":
                a1, a2 = st.columns([1.45, 1])
                with a1:
                    with st.container(border=True):
                        st.markdown(f"<h4>Hibrid ML + Kvantitatív Elemzés ({score}/100 • {verdict})</h4>", unsafe_allow_html=True)
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
                        st.info("Kattints a jobb felső 'AI Kulcs Beállítása' kártyára, és add meg a Gemini API kulcsodat.")
                    else:
                        try:
                            client = genai.Client(api_key=api_key.strip())
                            lp = learned_bt["params"]
                            prompt = f"""
                            Te a Gazdag Leszek Elemzői Iroda vezető intézményi portfóliómenedzsere vagy. Elemezd a(z) {ticker} részvényt magyar nyelven, emojik nélkül!
                            - Élő ár: {curr['Close']:.2f}, POC szint: {poc_price:.2f}, Alpha vs SPY: {alpha_pct:+.2f}%
                            - Perzisztens Random Forest ML modell emelkedési valószínűsége: {ml_model_res['prob_up']:.1f}% (Teszt-pontosság: {ml_model_res['accuracy']:.1f}%, Legfontosabb indikátorok: {ml_model_res['importances']})
                            - Grid Search Backtest eredménye: Trend={lp['fast_sma']}, RSI vételi küszöb={lp['rsi_buy']}, RSI eladási küszöb={lp['rsi_sell']}, Találati arány={learned_bt['win_rate']:.1f}%.
                            - Quant Pontszám: {score}/100 ({verdict}), Javasolt Stop: {stop_loss:.2f}, Célár: {take_profit:.2f}
                            - Hírek: {headlines}

                            Fejtsd ki 3 pontban:
                            1. Mit mutat a Perzisztens Random Forest gépi tanulási modell és az önfejlesztő backtest összhangja?
                            2. Hírek és katalizátorok értékelése
                            3. Konkrét kereskedési terv pontos árszintekkel.
                            """
                            with st.spinner("Elemzés generálása..."):
                                resp = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
                                st.markdown(resp.text)
                        except Exception as e:
                            st.error(f"API Hiba: {e}")
