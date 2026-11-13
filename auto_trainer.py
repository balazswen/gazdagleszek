import os
import json
from datetime import datetime
import yfinance as yf
import pandas as pd
import numpy as np
import joblib
from sklearn.ensemble import RandomForestClassifier

JOURNAL_FILE = "prediction_journal.json"
PORTFOLIO_FILE = "user_portfolio.json"
MODELS_DIR = "ml_models"
FEATURE_COLS = ['RSI', 'Stoch_RSI', 'MACD_Hist', 'ADX', 'BB_Width', 'Dist_SMA20_Pct', 'Dist_SMA50_Pct', 'Vol_Ratio', 'Ret_5']

os.makedirs(MODELS_DIR, exist_ok=True)

def load_json(path, default):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default
    return default

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def compute_features(df):
    df = df.copy()
    df['SMA_20'] = df['Close'].rolling(20, min_periods=5).mean()
    df['SMA_50'] = df['Close'].rolling(50, min_periods=10).mean()
    df['EMA_12'] = df['Close'].ewm(span=12, adjust=False).mean()
    df['EMA_26'] = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = df['EMA_12'] - df['EMA_26']
    df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    df['MACD_Hist'] = df['MACD'] - df['MACD_Signal']

    delta = df['Close'].diff()
    gain = delta.clip(lower=0).ewm(alpha=1/14, min_periods=5, adjust=False).mean()
    loss = (-1 * delta.clip(upper=0)).ewm(alpha=1/14, min_periods=5, adjust=False).mean().replace(0, 1e-9)
    df['RSI'] = (100 - (100 / (1 + (gain / loss)))).fillna(50.0)

    r_min = df['RSI'].rolling(14, min_periods=5).min()
    r_max = df['RSI'].rolling(14, min_periods=5).max()
    df['Stoch_RSI'] = (((df['RSI'] - r_min) / (r_max - r_min).replace(0, 1e-9)) * 100).fillna(50.0)

    std_20 = df['Close'].rolling(20, min_periods=5).std().fillna(0)
    df['BB_Width'] = (((df['SMA_20'] + std_20 * 2) - (df['SMA_20'] - std_20 * 2)) / df['SMA_20'].replace(0, 1e-9)) * 100

    high_diff = df['High'].diff()
    low_diff = -df['Low'].diff()
    plus_dm = np.where((high_diff > low_diff) & (high_diff > 0), high_diff, 0.0)
    minus_dm = np.where((low_diff > high_diff) & (low_diff > 0), low_diff, 0.0)
    tr = pd.concat([
        df['High'] - df['Low'],
        np.abs(df['High'] - df['Close'].shift()),
        np.abs(df['Low'] - df['Close'].shift())
    ], axis=1).max(axis=1)
    df['ATR'] = tr.rolling(14, min_periods=3).mean().bfill()
    atr_s = tr.ewm(alpha=1/14, min_periods=5, adjust=False).mean().replace(0, 1e-9)
    p_di = 100 * (pd.Series(plus_dm, index=df.index).ewm(alpha=1/14, min_periods=5, adjust=False).mean() / atr_s)
    m_di = 100 * (pd.Series(minus_dm, index=df.index).ewm(alpha=1/14, min_periods=5, adjust=False).mean() / atr_s)
    dx = (np.abs(p_di - m_di) / (p_di + m_di).replace(0, 1e-9)) * 100
    df['ADX'] = dx.ewm(alpha=1/14, min_periods=5, adjust=False).mean().fillna(20.0)

    vol_sma = df['Volume'].rolling(20, min_periods=3).mean().replace(0, 1).bfill()
    df['Dist_SMA20_Pct'] = ((df['Close'] - df['SMA_20']) / df['SMA_20'].replace(0, 1)) * 100
    df['Dist_SMA50_Pct'] = ((df['Close'] - df['SMA_50']) / df['SMA_50'].replace(0, 1)) * 100
    df['Vol_Ratio'] = df['Volume'] / vol_sma
    df['Ret_5'] = df['Close'].pct_change(5).fillna(0) * 100
    return df

def evaluate_and_train():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Öntanuló ciklus indítása...")
    journal = load_json(JOURNAL_FILE, [])
    portfolio = load_json(PORTFOLIO_FILE, {"holdings": {}})

    # Figyelt részvények összegyűjtése (Alap Watchlist + Saját Portfólió)
    watchlist = {"NVDA", "AAPL", "MSFT", "TSLA", "META", "AMZN", "GOOGL", "AMD", "SKHY", "INTC", "RHM", "TSM", "ORCL", "BASF"}
    for sym in portfolio.get("holdings", {}).keys():
        watchlist.add(sym.upper())

    # 1. LÉPÉS: Korábbi naplózott előrejelzések kiértékelése valós piaci árakkal
    for entry in journal:
        sym = entry.get("Ticker")
        if not sym:
            continue
        try:
            hist = yf.Ticker(sym).history(period="5d", interval="1d")
            if not hist.empty:
                now_p = float(hist['Close'].iloc[-1])
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
        except Exception as e:
            print(f"Hiba a napló frissítésekor ({sym}): {e}")

    # 2. LÉPÉS: Modellek újratanítása (Historikus adatok + 5x súlyozott Napló Visszacsatolás)
    for sym in sorted(watchlist):
        try:
            df = yf.Ticker(sym).history(period="2y", interval="1d")
            if df.empty or len(df) < 60:
                continue
            df = compute_features(df)
            ml_df = df.dropna(subset=FEATURE_COLS).copy()
            ml_df['Future_Close'] = ml_df['Close'].shift(-5)
            train_df = ml_df.dropna(subset=['Future_Close']).copy()
            train_df['Target'] = (train_df['Future_Close'] > train_df['Close']).astype(int)

            X_hist = train_df[FEATURE_COLS].values
            y_hist = train_df['Target'].values
            weights = np.ones(len(X_hist))

            # Visszacsatolás (Feedback Loop): A naplózott lezárt kötések hozzáadása 5x-ös tanulási súllyal!
            feedback_X, feedback_y = [], []
            for entry in journal:
                if entry.get("Ticker") == sym and "Features" in entry and "Target_Outcome" in entry:
                    feat_vec = [entry["Features"].get(c, 0.0) for c in FEATURE_COLS]
                    feedback_X.append(feat_vec)
                    feedback_y.append(int(entry["Target_Outcome"]))

            if feedback_X:
                X_all = np.vstack([X_hist, np.array(feedback_X)])
                y_all = np.concatenate([y_hist, np.array(feedback_y)])
                w_all = np.concatenate([weights, np.full(len(feedback_y), 5.0)])
            else:
                X_all, y_all, w_all = X_hist, y_hist, weights

            split = int(len(X_hist) * 0.8)
            clf_eval = RandomForestClassifier(n_estimators=150, max_depth=6, min_samples_leaf=4, random_state=42)
            clf_eval.fit(X_hist[:split], y_hist[:split])
            test_acc = float(clf_eval.score(X_hist[split:], y_hist[split:]) * 100.0)

            # Végső modell betanítása a kombinált (historikus + visszacsatolt) adatokon
            clf_final = RandomForestClassifier(n_estimators=150, max_depth=6, min_samples_leaf=4, random_state=42)
            clf_final.fit(X_all, y_all, sample_weight=w_all)

            latest_row = ml_df.iloc[-1]
            latest_X = ml_df[FEATURE_COLS].iloc[-1:].values
            prob_up = float(clf_final.predict_proba(latest_X)[0][1] * 100.0)

            importances = {col: round(float(imp * 100), 1) for col, imp in zip(FEATURE_COLS, clf_final.feature_importances_)}
            importances = dict(sorted(importances.items(), key=lambda x: x[1], reverse=True))

            # Modell agy kimentése lemezre (.joblib)
            brain_path = os.path.join(MODELS_DIR, f"{sym}_1d_brain.joblib")
            joblib.dump({
                "model": clf_final,
                "accuracy": test_acc,
                "importances": importances,
                "trained_samples": len(X_all),
                "feedback_samples": len(feedback_y),
                "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M")
            }, brain_path)

            # 3. LÉPÉS: Automatikus napi előrejelzés naplózása (ha ma még nem volt erre a tickerre)
            today_str = datetime.now().strftime("%Y-%m-%d")
            already_logged = any(e.get("Ticker") == sym and str(e.get("Dátum", "")).startswith(today_str) for e in journal)

            if not already_logged:
                curr_p = float(latest_row['Close'])
                atr_v = float(latest_row['ATR'])
                verdict = "ERŐS VÉTEL" if prob_up >= 62 else ("VÉTEL" if prob_up >= 53 else ("ELADÁS" if prob_up < 42 else "TARTÁS"))
                journal.append({
                    "Dátum": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "Ticker": sym,
                    "Időtáv": "1d",
                    "Rögzített Ár": round(curr_p, 2),
                    "Quant Pont": int(round(prob_up)),
                    "ML Esély (%)": round(prob_up, 1),
                    "Ajánlás": verdict,
                    "Célár": round(curr_p + 3.2 * atr_v, 2),
                    "Stop-Loss": round(curr_p - 1.8 * atr_v, 2),
                    "Aktuális Ár": round(curr_p, 2),
                    "Valós Hozam (%)": 0.0,
                    "Státusz": "Folyamatban (Auto)",
                    "Features": {c: round(float(latest_row[c]), 4) for c in FEATURE_COLS}
                })

            print(f" -> {sym}: Modell frissítve ({len(X_all)} minta, {len(feedback_y)} visszacsatolás) | ML Esély: {prob_up:.1f}%")
        except Exception as e:
            print(f"Hiba ({sym}): {e}")

    save_json(JOURNAL_FILE, journal)
    print("Öntanuló ciklus sikeresen befejeződött!")

if __name__ == "__main__":
    evaluate_and_train()
