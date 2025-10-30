import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go

st.set_page_config(page_title="תיק מניות", layout="wide")

st.title("📈 מעקב מניות אישיות")

uploaded_file = st.file_uploader("העלה את קובץ תיק המניות שלך (Excel)", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file)
    st.dataframe(df)

    # בדיקה לעמודות חיוניות
    required_cols = {"Symbol", "Buy Date", "Buy Price"}
    if not required_cols.issubset(df.columns):
        st.error("יש לוודא שלקובץ יש עמודות: Symbol, Buy Date, Buy Price")
    else:
        stock = st.selectbox("בחר מניה להצגה:", df["Symbol"].unique())

        if stock:
            # נתוני קנייה
            buy_row = df[df["Symbol"] == stock].iloc[0]
            buy_date = pd.to_datetime(buy_row["Buy Date"])
            buy_price = float(buy_row["Buy Price"])

            # הורדת נתוני שוק
            data = yf.download(stock, start=buy_date, progress=False)
            data.reset_index(inplace=True)

            if data.empty:
                st.error("לא נמצאו נתונים עבור המניה הזו.")
            else:
                # גרף
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=data["Date"], y=data["Close"], mode='lines', name='שער סגירה'))
                fig.add_hline(y=buy_price, line=dict(color='red', dash='dash'), name='שער קנייה')
                fig.update_layout(
                    title=f"{stock} - ממועד הקנייה ({buy_date.date()}) ועד היום",
                    xaxis_title="תאריך",
                    yaxis_title="שער",
                    template="plotly_white",
                    height=600
                )
                st.plotly_chart(fig, use_container_width=True)
else:
    st.info("העלה קובץ כדי להתחיל.")
