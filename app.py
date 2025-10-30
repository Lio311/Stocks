import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime, timedelta

# כותרת האפליקציה
st.title("גרף מניית Google - שנה אחרונה")

# הגדרת טווח התאריכים
end_date = datetime.today()
start_date = end_date - timedelta(days=365)

# הורדת נתוני מניה
ticker = "GOOGL"
data = yf.download(ticker, start=start_date, end=end_date)

# הצגת הנתונים בטבלה
st.subheader(f"נתונים אחרונים של {ticker}")
st.dataframe(data.tail(10))

# גרף מחירים
fig = go.Figure()
fig.add_trace(go.Candlestick(
    x=data.index,
    open=data['Open'],
    high=data['High'],
    low=data['Low'],
    close=data['Close'],
    name='מחיר מניה'
))
fig.update_layout(
    title=f"גרף מניית {ticker} - שנה אחרונה",
    xaxis_title="תאריך",
    yaxis_title="מחיר (USD)",
    xaxis_rangeslider_visible=False
)

st.plotly_chart(fig)
