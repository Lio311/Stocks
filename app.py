import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime

st.set_page_config(page_title="תיק מניות", layout="wide")

# קריאת הקובץ מקומית
file_path = "תיק מניות.xlsx"
df = pd.read_excel(file_path)

# בדיקה לעמודות הנדרשות
required_cols = {"Symbol", "Buy Date", "Buy Price"}
if not required_cols.issubset(df.columns):
    st.error("יש לוודא שלקובץ יש עמודות: Symbol, Buy Date, Buy Price")
    st.stop()

st.title("📊 תיק המניות שלי")

# יצירת כפתור לכל מניה
for _, row in df.iterrows():
    symbol = row["Symbol"]
    buy_date = pd.to_datetime(row["Buy Date"])
    buy_price = float(row["Buy Price"])

    if st.button(symbol):
        st.subheader(f"{symbol} - גרף מהמועד {buy_date.date()} ועד היום")

        # הורדת הנתונים
        data = yf.download(symbol, start=buy_date, progress=False)
        data.reset_index(inplace=True)

        if data.empty:
            st.warning(f"לא נמצאו נתונים עבור {symbol}")
            continue

        # יצירת גרף
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=data["Date"], y=data["Close"], mode='lines', name='שער סגירה'))
        fig.add_hline(y=buy_price, line=dict(color='red', dash='dash'), name='שער קנייה')
        fig.update_layout(
            title=f"{symbol}: שינוי משער הקנייה עד היום",
            xaxis_title="תאריך",
            yaxis_title="שער",
            template="plotly_white",
            height=600
        )

        st.plotly_chart(fig, use_container_width=True)
