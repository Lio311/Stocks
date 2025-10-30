import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime, timedelta

st.set_page_config(page_title="תיק מניות", layout="wide")
st.title("📊 תיק המניות שלי")

file_path = "תיק מניות.xlsx"

# קריאה של כל השורות ללא header כדי לא לפספס את הכותרת
df_raw = pd.read_excel(file_path, header=None)

# חיפוש השורה שבה מתחילות הכותרות האמיתיות
header_row_idx = df_raw[df_raw.iloc[:, 0] == "שינוי מצטבר(%)"].index[0]

# קריאה מחדש עם השורה הנכונה ככותרת
df = pd.read_excel(file_path, header=header_row_idx)

# הסרת שורות ריקות או שורות לא רלוונטיות
df = df.dropna(subset=["טיקר"])

# ניקוי רווחים בשמות העמודות
df.columns = [str(col).strip() for col in df.columns]

# בדיקה שהעמודות הנדרשות קיימות
required_cols = {"טיקר", "מחיר עלות", "מחיר זמן אמת"}
if not required_cols.issubset(df.columns):
    st.error("יש לוודא שלקובץ יש עמודות: טיקר, מחיר עלות, מחיר זמן אמת")
    st.stop()

# הצגת טבלה מצומצמת
st.dataframe(df[["טיקר", "מחיר עלות", "מחיר זמן אמת"]])

# טווח זמן לברירת מחדל (שנה אחורה)
start_date = datetime.now() - timedelta(days=365)

# יצירת כפתורים לכל מניה
for _, row in df.iterrows():
    ticker = str(row["טיקר"]).strip()
    cost_price = float(row["מחיר עלות"])
    current_price = float(row["מחיר זמן אמת"])

    if st.button(ticker):
        st.subheader(f"{ticker} - גרף מהשנה האחרונה")

        # הורדת נתוני שערים
        data = yf.download(ticker, start=start_date, progress=False)
        data.reset_index(inplace=True)

        if data.empty:
            st.warning(f"לא נמצאו נתונים עבור {ticker}")
            continue

        # יצירת גרף
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

        # הצגת נתונים מספריים
        change_pct = ((current_price - cost_price) / cost_price) * 100
        st.write(f"**שינוי מצטבר:** {change_pct:.2f}%")

        st.plotly_chart(fig, use_container_width=True)
