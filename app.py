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

# פונקציה להצגת גרף בסיסי
def plot_stock_graph(ticker):
    start_date = datetime.now() - timedelta(days=30)  # חודש אחורה
    data = yf.download(ticker, start=start_date, progress=False)
    if data.empty:
        st.warning(f"לא נמצאו נתונים עבור {ticker}")
        return

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=data.index, y=data["Close"], mode='lines', name='שער סגירה'))
    fig.update_layout(
        title=f"{ticker} - חודש אחרון",
        xaxis_title="תאריך",
        yaxis_title="שער",
        template="plotly_white",
        height=600
    )
    st.plotly_chart(fig, use_container_width=True)

# יצירת כפתורים בראש העמוד
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
    plot_stock_graph(st.session_state.selected_ticker)
