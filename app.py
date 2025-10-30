import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime, timedelta

st.set_page_config(page_title="תיק מניות", layout="wide")
st.title("📊 תיק המניות שלי")

file_path = "תיק מניות.xlsx"

# קריאה של הקובץ עם header
df_raw = pd.read_excel(file_path, header=None)

# חיפוש שורת כותרת
header_row_idx = None
for i, row in df_raw.iterrows():
    if row.astype(str).str.contains("שינוי מצטבר").any():
        header_row_idx = i
        break

if header_row_idx is None:
    st.error("לא נמצא שורת כותרת עם 'שינוי מצטבר'")
    st.stop()

df = pd.read_excel(file_path, header=header_row_idx)
df.columns = [str(col).strip() for col in df.columns]
df = df.dropna(subset=["טיקר"])

# המרת טיקרים לפורמט yfinance
def convert_ticker(t):
    t = str(t).strip()
    if t.startswith("XNAS:") or t.startswith("XTAE:"):
        return t.split(":")[1]  # NASDAQ
    elif t.startswith("XLON:"):
        return t.split(":")[1] + ".L"  # LSE
    else:
        return t

df["yfinance_ticker"] = df["טיקר"].apply(convert_ticker)

# מצב המניה שנבחרה
if "selected_ticker" not in st.session_state:
    st.session_state.selected_ticker = None

# מצב טווח זמן
if "selected_range" not in st.session_state:
    st.session_state.selected_range = "1M"  # חודש כברירת מחדל

# פונקציה להצגת גרף סטנדרטי
def plot_stock_graph(ticker, period):
    # הורדת נתונים לפי טווח
    if period == "1M":
        start_date = datetime.now() - timedelta(days=30)
    elif period == "1W":
        start_date = datetime.now() - timedelta(days=7)
    elif period == "1Y":
        start_date = datetime.now() - timedelta(days=365)
    else:
        start_date = datetime.now() - timedelta(days=30)

    data = yf.download(ticker, start=start_date, progress=False)
    if data.empty:
        st.warning(f"לא נמצאו נתונים עבור {ticker}")
        return

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=data.index, y=data["Close"], mode='lines', name='שער סגירה'))
    fig.update_layout(
        title=f"{ticker} - טווח {period}",
        xaxis_title="תאריך",
        yaxis_title="שער",
        template="plotly_white",
        height=600
    )
    st.plotly_chart(fig, use_container_width=True)

# כפתורי טווח זמן מעל הגרף
st.write("**בחר טווח זמן לגרף:**")
time_cols = st.columns(4)
ranges = ["1W", "1M", "1Y", "ALL"]
for i, r in enumerate(ranges):
    if time_cols[i].button(r):
        st.session_state.selected_range = r

# יצירת כפתורים למניות בראש העמוד
cols_per_row = 6
for i in range(0, len(df), cols_per_row):
    cols = st.columns(min(cols_per_row, len(df) - i))
    for j, col in enumerate(cols):
        row = df.iloc[i + j]
        ticker = row["yfinance_ticker"]
        button_label = str(row["טיקר"]).strip()
        if button_label != "" and col.button(button_label):
            st.session_state.selected_ticker = ticker

# הצגת הגרף של המניה שנבחרה
if st.session_state.selected_ticker:
    plot_stock_graph(st.session_state.selected_ticker, st.session_state.selected_range)
