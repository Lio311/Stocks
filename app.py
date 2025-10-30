import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

# הגדרת העמוד
st.set_page_config(
    page_title="מניית Google - ניתוח",
    page_icon="📈",
    layout="wide"
)

# כותרת ראשית
st.title("📊 ניתוח מניית Google (Alphabet Inc.)")
st.markdown("---")

# סמל המניה
ticker = "GOOGL"

# פונקציה לטעינת נתונים עם cache
@st.cache_data(ttl=300)  # cache למשך 5 דקות
def load_data(period):
    stock = yf.Ticker(ticker)
    data = stock.history(period=period)
    return data

# טעינת נתונים
with st.spinner("טוען נתונים..."):
    try:
        data_year = load_data("1y")
        data_month = load_data("1mo")
        data_week = load_data("5d")
        
        # מידע כללי על המניה
        stock_info = yf.Ticker(ticker).info
        
        st.success("✅ הנתונים נטענו בהצלחה!")
        
    except Exception as e:
        st.error(f"❌ שגיאה בטעינת הנתונים: {e}")
        st.stop()

# תצוגת מידע כללי
col1, col2, col3, col4 = st.columns(4)

with col1:
    current_price = data_year['Close'].iloc[-1]
    st.metric("מחיר נוכחי", f"${current_price:.2f}")

with col2:
    day_change = data_week['Close'].iloc[-1] - data_week['Close'].iloc[-2] if len(data_week) > 1 else 0
    day_change_pct = (day_change / data_week['Close'].iloc[-2] * 100) if len(data_week) > 1 else 0
    st.metric("שינוי יומי", f"${day_change:.2f}", f"{day_change_pct:.2f}%")

with col3:
    week_change_pct = ((data_week['Close'].iloc[-1] / data_week['Close'].iloc[0]) - 1) * 100
    st.metric("שינוי שבועי", f"{week_change_pct:.2f}%")

with col4:
    year_change_pct = ((data_year['Close'].iloc[-1] / data_year['Close'].iloc[0]) - 1) * 100
    st.metric("שינוי שנתי", f"{year_change_pct:.2f}%")

st.markdown("---")

# בחירת תקופה
st.subheader("🔍 בחר תקופת תצוגה")
period_option = st.radio(
    "תקופה:",
    ["שנה אחרונה", "חודש אחרון", "שבוע אחרון", "הכל"],
    horizontal=True
)

# בחירת נתונים לפי תקופה
if period_option == "שנה אחרונה":
    selected_data = data_year
    title = "מחיר מניית Google - שנה אחרונה"
    color = '#4285F4'
elif period_option == "חודש אחרון":
    selected_data = data_month
    title = "מחיר מניית Google - חודש אחרון"
    color = '#EA4335'
elif period_option == "שבוע אחרון":
    selected_data = data_week
    title = "מחיר מניית Google - שבוע אחרון"
    color = '#34A853'
else:  # הכל
    selected_data = None

# תצוגת גרפים
if selected_data is not None:
    # גרף בודד
    st.subheader(title)
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=selected_data.index,
        y=selected_data['Close'],
        mode='lines',
        name='מחיר סגירה',
        line=dict(color=color, width=2),
        fill='tonexty',
        fillcolor=color + '40'
    ))
    
    fig.update_layout(
        xaxis_title="תאריך",
        yaxis_title="מחיר ($)",
        hovermode='x unified',
        height=500,
        template='plotly_white'
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # סטטיסטיקות
    col1, col2, col3 = st.columns(3)
    with col1:
        st.info(f"**מחיר מינימלי:** ${selected_data['Close'].min():.2f}")
    with col2:
        st.info(f"**מחיר מקסימלי:** ${selected_data['Close'].max():.2f}")
    with col3:
        avg_price = selected_data['Close'].mean()
        st.info(f"**מחיר ממוצע:** ${avg_price:.2f}")

else:
    # תצוגת כל התקופות
    st.subheader("📈 השוואת כל התקופות")
    
    # גרף 1: שנה
    st.markdown("### שנה אחרונה")
    fig1 = go.Figure()
    fig1.add_trace(go.Scatter(
        x=data_year.index,
        y=data_year['Close'],
        mode='lines',
        line=dict(color='#4285F4', width=2),
        fill='tonexty'
    ))
    fig1.update_layout(
        xaxis_title="תאריך",
        yaxis_title="מחיר ($)",
        height=400,
        template='plotly_white'
    )
    st.plotly_chart(fig1, use_container_width=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        # גרף 2: חודש
        st.markdown("### חודש אחרון")
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(
            x=data_month.index,
            y=data_month['Close'],
            mode='lines',
            line=dict(color='#EA4335', width=2),
            fill='tonexty'
        ))
        fig2.update_layout(
            xaxis_title="תאריך",
            yaxis_title="מחיר ($)",
            height=350,
            template='plotly_white'
        )
        st.plotly_chart(fig2, use_container_width=True)
    
    with col2:
        # גרף 3: שבוע
        st.markdown("### שבוע אחרון")
        fig3 = go.Figure()
        fig3.add_trace(go.Scatter(
            x=data_week.index,
            y=data_week['Close'],
            mode='lines+markers',
            line=dict(color='#34A853', width=2),
            fill='tonexty'
        ))
        fig3.update_layout(
            xaxis_title="תאריך",
            yaxis_title="מחיר ($)",
            height=350,
            template='plotly_white'
        )
        st.plotly_chart(fig3, use_container_width=True)

# טבלת נתונים
st.markdown("---")
st.subheader("📋 נתונים גולמיים")

if selected_data is not None:
    display_data = selected_data[['Open', 'High', 'Low', 'Close', 'Volume']].copy()
    display_data.columns = ['פתיחה', 'גבוה', 'נמוך', 'סגירה', 'נפח']
    st.dataframe(display_data.tail(10), use_container_width=True)
else:
    tab1, tab2, tab3 = st.tabs(["שנה", "חודש", "שבוע"])
    
    with tab1:
        display_year = data_year[['Open', 'High', 'Low', 'Close', 'Volume']].copy()
        display_year.columns = ['פתיחה', 'גבוה', 'נמוך', 'סגירה', 'נפח']
        st.dataframe(display_year.tail(10), use_container_width=True)
    
    with tab2:
        display_month = data_month[['Open', 'High', 'Low', 'Close', 'Volume']].copy()
        display_month.columns = ['פתיחה', 'גבוה', 'נמוך', 'סגירה', 'נפח']
        st.dataframe(display_month.tail(10), use_container_width=True)
    
    with tab3:
        display_week = data_week[['Open', 'High', 'Low', 'Close', 'Volume']].copy()
        display_week.columns = ['פתיחה', 'גבוה', 'נמוך', 'סגירה', 'נפח']
        st.dataframe(display_week, use_container_width=True)

# כפתור רענון
st.markdown("---")
if st.button("🔄 רענן נתונים"):
    st.cache_data.clear()
    st.rerun()

# footer
st.markdown("---")
st.caption(f"נתונים מתעדכנים מ-Yahoo Finance | עודכן לאחרונה: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
