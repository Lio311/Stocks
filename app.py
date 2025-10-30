import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime, timedelta

st.title("גרף מניית Google - שנה אחרונה")

end_date = datetime.today()
start_date = end_date - timedelta(days=365)

ticker = "GOOGL"
data = yf.download(ticker, start=start_date, end=end_date)

st.subheader(f"נתוני {ticker} אחרונים")
st.dataframe(data.tail(10))

# גרף קו מחירים פשוט
fig = go.Figure()
fig.add_trace(go.Scatter(
    x=data.index,
    y=data['Close'],
    mode='lines',
    name='מחיר סגירה'
))

fig.update_layout(
    title=f"גרף מחירי סגירה של {ticker} - שנה אחרונה",
    xaxis_title="תאריך",
    yaxis_title="מחיר (USD)"
)

st.plotly_chart(fig)
