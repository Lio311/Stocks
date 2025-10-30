import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime, timedelta

st.set_page_config(page_title="תיק מניות", layout="wide")
st.title("📊 תיק המניות שלי")

file_path = "תיק מניות.xlsx"

# קריאה של כל השורות ללא header
df_raw = pd.read_excel(file_path, header=None)

# חיפוש שורה שבה מופיעה המחרוזת "שינוי מצטבר" בכל אחד מהתאים
header_row_idx = None
for i, row in df_raw.iterrows():
    if row.astype(str).str.strip().str.contains("שינוי מצטבר").any():
        header_row_idx = i
        break

if header_row_idx is None:
    st.error("לא נמצא שורת כותרת עם 'שינוי מצטבר'")
    st.stop()

# קריאה מחדש עם השורה הנכונה ככותרת
df = pd.read_excel(file_path, header=header_row_idx)

# ניקוי רווחים בשמות העמודות
df.columns = [str(col).strip() for col in df.columns]

# הסרת שורות ריקות או לא רלוונטיות
df = df.dropna(subset=["טיקר"])

# ניקוי מתקדם של עמודות מספריות
for col in ["מחיר עלות", "מחיר זמן אמת"]:
    df[col] = df[col].astype(str).str.replace(r'[^\d\.-]', '', regex=True)
    df[col] = pd.to_numeric(df[col], errors='coerce')

# הסרת שורות עם ערכים לא חוקיים
df = df.dropna(subset=["מחיר עלות", "מחיר זמן אמת", "טיקר"])

# בדיקה שהעמודות הנדרשות קיימות
required_cols = {"טיקר", "מחיר עלות", "מחיר זמן אמת"}
if not required_cols.issubset(df.columns):
    st.error("יש לוודא שלקובץ יש עמודות: טיקר, מחיר עלות, מחיר זמן אמת")
    st.stop()

# שמירת מצב המניה שנבחרה
if "selected_ticker" not in st.session_state:
    st.session_state.selected_ticker = None

# פונקציה להצגת גרף עבור מניה מסוימת
def plot_stock_graph(ticker, cost_price, current_price):
    start_date = datetime.now() - timedelta(days=365)
    data = yf.download(ticker, start=start_date, progress=False)
    data.reset_index(inplace=True)

    if data.empty:
        st.warning(f"לא נמצאו נתונים עבור {ticker}")
        return

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=data["Date"], y=data["Close"], mode='lines', name='שער סגירה'))
    fig.add_hline(y=cost_price, line=dict(color='red', dash='dash'), name='מחיר עלות')
    fig.update_layout(
        title=f"{ticker} - מחיר עלות: {cost_price} | מחיר נוכחי: {current_price}",
        xaxis_title="תאריך",
        yaxis_title="שער",
        template="plotly_white",
        height=600
    )

    change_pct = ((current_price - cost_price) / cost_price) * 100
    st.write(f"**שינוי מצטבר:** {change_pct:.2f}%")
    st.plotly_chart(fig, use_container_width=True)

# יצירת כפתורים בראש העמוד
cols_per_row = 6
for i in range(0, len(df), cols_per_row):
    cols = st.columns(min(cols_per_row, len(df) - i))
    for j, col in enumerate(cols):
        row = df.iloc[i + j]
        ticker = str(row["טיקר"]).strip()
        cost_price = row["מחיר עלות"]
        current_price = row["מחיר זמן אמת"]

        if col.button(ticker):
            st.session_state.selected_ticker = ticker
            st.session_state.selected_cost_price = cost_price
            st.session_state.selected_current_price = current_price

# הצגת הגרף של המניה שנבחרה (מתחת לכל הכפתורים)
if st.session_state.selected_ticker:
    plot_stock_graph(
        st.session_state.selected_ticker,
        st.session_state.selected_cost_price,
        st.session_state.selected_current_price
    )
