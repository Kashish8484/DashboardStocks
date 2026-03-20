import streamlit as st  
import yfinance as yf
import pandas as pd
import ta
import winsound
from datetime import datetime
import time

# =========================
# EXACT 5-MIN CANDLE REFRESH
# =========================
now = datetime.now()
next_minute = (now.minute // 5 + 1) * 5
if next_minute == 60:
    next_run = now.replace(hour=now.hour+1, minute=0, second=2, microsecond=0)
else:
    next_run = now.replace(minute=next_minute, second=2, microsecond=0)

wait_ms = int((next_run - now).total_seconds() * 1000)
st_autorefresh(interval=wait_ms, key="refresh")

st.set_page_config(page_title="PRO Intraday Scanner", layout="wide")

# =========================
# STYLE
# =========================
st.markdown("""
<style>
body {background-color:#0f172a; color:white;}
.stButton>button {background-color:#00ffcc;color:black;font-weight:bold;border-radius:10px;}
</style>
""", unsafe_allow_html=True)

# =========================
# HEADER
# =========================
st.markdown("<h2 style='text-align:center; margin-top:-125px;'>🚀 ChartArt Intraday Directional Scanner</h2>", unsafe_allow_html=True)

st.markdown(
    f"<p style='text-align:center; color:gray; margin-top:-90px;'>Last Update: {datetime.now().strftime('%H:%M:%S')} &nbsp;&nbsp; | &nbsp;&nbsp; Next Candle Run: {next_run.strftime('%H:%M:%S')}</p>",
    unsafe_allow_html=True
)

# =========================
# ALERT SOUND
# =========================
def strong_alert():
    for _ in range(5):
        winsound.Beep(2500, 500)

# =========================
# GET YESTERDAY CLOSE
# =========================
def get_yesterday_close(ticker):
    try:
        df = yf.download(ticker, period="2d", interval="1d", progress=False)
        if df is not None and len(df) >= 2:
            return float(df["Close"].iloc[-2])
    except:
        pass
    return 0

# =========================
# SAFE DOWNLOAD
# =========================
def safe_download(ticker):
    try:
        df = yf.download(ticker, period="1d", interval="5m", progress=False)
        if df is None or df.empty:
            return None
        return df
    except:
        return None

# =========================
# MARKET DIRECTION
# =========================
def get_market_direction(n_p, n_y, b_p, b_y):
    if n_p > n_y and b_p > b_y:
        return "BULLISH"
    elif n_p < n_y and b_p < b_y:
        return "BEARISH"
    else:
        return "SIDEWAYS"

# =========================
# INDEX DATA (FIXED ERROR HERE)
# =========================
nifty = safe_download("^NSEI")
if nifty is None:
    nifty = safe_download("NSEI.NS")

bank = safe_download("^NSEBANK")
gold = safe_download("GC=F")
crude = safe_download("CL=F")
vix = safe_download("^INDIAVIX")

n_p = float(nifty["Close"].iloc[-1]) if nifty is not None else 0
b_p = float(bank["Close"].iloc[-1]) if bank is not None else 0
g_p = float(gold["Close"].iloc[-1]) if gold is not None else 0
c_p = float(crude["Close"].iloc[-1]) if crude is not None else 0
v_p = float(vix["Close"].iloc[-1]) if vix is not None else 0

n_y = get_yesterday_close("^NSEI")
b_y = get_yesterday_close("^NSEBANK")
g_y = get_yesterday_close("GC=F")
c_y = get_yesterday_close("CL=F")
v_y = get_yesterday_close("^INDIAVIX")

market = get_market_direction(n_p, n_y, b_p, b_y)

# =========================
# INDEX DISPLAY
# =========================
def index_display(price, y_close, name):
    if price > y_close:
        color = "#2CFF05"; arrow = "⬆️"
    elif price < y_close:
        color = "#FF46A2"; arrow = "⬇️"
    else:
        color = "#FDBE02"; arrow = "➡️"

    return f"<div style='background:#1e293b;padding:10px;border-radius:10px;text-align:center; margin-top:-70px;'><b style='color:{color}'>{name}</b><br><span style='color:{color}'>{price:.2f}</span><br>{arrow}</div>"

cols = st.columns(5)
cols[0].markdown(index_display(n_p, n_y, "Nifty"), unsafe_allow_html=True)
cols[1].markdown(index_display(b_p, b_y, "BankNifty"), unsafe_allow_html=True)
cols[2].markdown(index_display(g_p, g_y, "Gold"), unsafe_allow_html=True)
cols[3].markdown(index_display(c_p, c_y, "Crude"), unsafe_allow_html=True)
cols[4].markdown(index_display(v_p, v_y, "VIX"), unsafe_allow_html=True)

st.subheader(f"Market Direction: {market}")

# =========================
# STOCK LIST
# =========================
stocks = { 
    "ABCAPITAL.NS": "ADITYA BIRLA CAPITAL LIMITED",
    "ABFRL.NS": "ADITYA BIRLA FASHION AND RETAIL LIMITED",
    "ACC.NS": "ACC LIMITED",
    "ZYDUSLIFE.NS": "ZYDUS LIFESCIENCES LIMITED"
}

data = yf.download(
    tickers=" ".join(stocks),
    period="1d",
    interval="5m",
    group_by="ticker",
    progress=False
)

# =========================
# SQUEEZE
# =========================
def is_squeeze(df):
    bb = ta.volatility.BollingerBands(df["Close"], window=20)
    bandwidth = (bb.bollinger_hband() - bb.bollinger_lband()) / bb.bollinger_mavg()
    return bandwidth.rolling(20).mean().iloc[-1] < 0.05

# =========================
# SESSION STATE
# =========================
if 'all_signals' not in st.session_state:
    st.session_state.all_signals = pd.DataFrame(columns=["Time","Stock","Signal","Target","SL","Status"])

# =========================
# UPDATE STATUS
# =========================
for i in range(len(st.session_state.all_signals)):
    row = st.session_state.all_signals.iloc[i]

    if row["Status"] != "IN PROGRESS":
        continue

    try:
        live = yf.download(row["Stock"], period="1d", interval="5m", progress=False)
        if live.empty:
            continue

        price = float(live["Close"].iloc[-1])

        if row["Signal"] == "BUY":
            if price >= row["Target"]:
                st.session_state.all_signals.at[i,"Status"] = "TARGET HIT"
            elif price <= row["SL"]:
                st.session_state.all_signals.at[i,"Status"] = "SL HIT"

        elif row["Signal"] == "SELL":
            if price <= row["Target"]:
                st.session_state.all_signals.at[i,"Status"] = "TARGET HIT"
            elif price >= row["SL"]:
                st.session_state.all_signals.at[i,"Status"] = "SL HIT"

    except:
        continue

# =========================
# SCAN (UNCHANGED)
# =========================
new_signals = []

if market != "SIDEWAYS":
    for stock in stocks:
        try:
            df = data[stock].dropna()
            if len(df) < 50:
                continue

            df["rsi"] = ta.momentum.RSIIndicator(df["Close"], window=14).rsi()
            bb = ta.volatility.BollingerBands(df["Close"], window=20)

            last = df.iloc[-1]
            prev = df.iloc[-2]
            avg_vol = df["Volume"].rolling(20).mean().iloc[-1]

            if not is_squeeze(df):
                continue

            if market == "BULLISH":
                if (last["Close"] > bb.bollinger_hband().iloc[-1]
                    and prev["rsi"] < 60
                    and last["rsi"] > 60
                    and 60 < last["rsi"] < 65
                    and last["Volume"] > 1.5 * avg_vol):

                    new_signals.append({"Time":datetime.now().strftime("%H:%M:%S"),
                                        "Stock":stock,
                                        "Signal":"BUY",
                                        "Target":round(last["Close"]*1.005,2),
                                        "SL":round(last["Close"]*0.995,2),
                                        "Status":"IN PROGRESS"})

            elif market == "BEARISH":
                if (last["Close"] < bb.bollinger_lband().iloc[-1]
                    and prev["rsi"] > 40
                    and last["rsi"] < 40
                    and 35 < last["rsi"] < 40
                    and last["Volume"] > 1.5 * avg_vol):

                    new_signals.append({"Time":datetime.now().strftime("%H:%M:%S"),
                                        "Stock":stock,
                                        "Signal":"SELL",
                                        "Target":round(last["Close"]*0.995,2),
                                        "SL":round(last["Close"]*1.005,2),
                                        "Status":"IN PROGRESS"})

        except:
            continue

# =========================
# APPEND SIGNALS
# =========================
if new_signals:
    strong_alert()
    df_new = pd.DataFrame(new_signals)
    st.session_state.all_signals = pd.concat([df_new, st.session_state.all_signals], ignore_index=True)

# =========================
# OUTPUT
# =========================
st.subheader("📊 Signals")
st.dataframe(st.session_state.all_signals)

# =========================
# WIN RATE
# =========================
if datetime.now().strftime("%H:%M") >= "15:30":
    df = st.session_state.all_signals
    closed = df[df["Status"] != "IN PROGRESS"]
    if len(closed) > 0:
        win = len(closed[closed["Status"] == "TARGET HIT"])
        total = len(closed)
        st.success(f"Winning Rate: {round((win/total)*100,2)}%")

# =========================
# BREATHING
# =========================
st.markdown("---")
st.subheader("🧘 One Breathing Cycle")

placeholder = st.empty()
phases = ["Breathe In","Hold","Breathe Out","Hold"]

for phase in phases:
    for i in range(7,0,-1):
        placeholder.markdown(f"<div style='text-align:center;'><h2>{phase}</h2><h1>{i}</h1></div>", unsafe_allow_html=True)
        time.sleep(1)
