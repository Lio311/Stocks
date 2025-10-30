import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime, timedelta

# הגדרת העמוד - Ensure RTL context is respected by Streamlit and Plotly
st.set_page_config(
    page_title="תיק המניות שלי",
    page_icon="💼",
    layout="wide")

# **Headings and text need to be in RTL order**
st.title("💼 תיק המניות שלי")
st.markdown("---")

file_path = "תיק מניות.xlsx"

# קריאה וניקוי הנתונים
@st.cache_data
def load_portfolio():
    # קריאה של כל השורות ללא header
    df_raw = pd.read_excel(file_path, header=None)
    
    # חיפוש שורה עם "שינוי מצטבר"
    header_row_idx = None
    for i, row in df_raw.iterrows():
        # שימוש ב-str.contains וב-regex כדי להתאים באופן גמיש
        if row.astype(str).str.strip().str.contains("שינוי מצטבר", regex=False).any():
            header_row_idx = i
            break
            
    if header_row_idx is None:
        return None
        
    df = pd.read_excel(file_path, header=header_row_idx)
    df.columns = [str(col).strip() for col in df.columns]
    df = df.dropna(subset=["טיקר", "מחיר עלות"])
    
    # ניקוי מחיר עלות
    df["מחיר עלות"] = df["מחיר עלות"].astype(str).str.replace(r'[^\d\.-]', '', regex=True)
    df["מחיר עלות"] = pd.to_numeric(df["מחיר עלות"], errors='coerce')
    df = df.dropna(subset=["מחיר עלות"])
    
    return df

# המרת טיקרים לפורמט yfinance
def convert_ticker(t):
    t = str(t).strip()
    if t.startswith("XNAS:"):
        return t.split(":")[1]  # NASDAQ
    elif t.startswith("XLON:"):
        return t.split(":")[1] + ".L"  # LSE
    else:
        return t

# טעינת התיק
with st.spinner("טוען את תיק המניות..."):
    df = load_portfolio()
    
    if df is None:
        # הודעת שגיאה מימין לשמאל
        st.error("❌ לא נמצא שורת כותרת עם 'שינוי מצטבר' בקובץ האקסל")
        st.stop()
        
    df["yfinance_ticker"] = df["טיקר"].apply(convert_ticker)
    # הודעת הצלחה מימין לשמאל
    st.success(f"✅ נטענו {len(df)} מניות מהתיק")

# מצב המניה שנבחרה
if "selected_ticker" not in st.session_state:
    st.session_state.selected_ticker = None
    st.session_state.selected_cost_price = None
    st.session_state.selected_name = None

# פונקציה לקבלת נתונים
@st.cache_data(ttl=300)
def get_stock_data(ticker, period="1y"):
    try:
        stock = yf.Ticker(ticker)
        data = stock.history(period=period)
        
        # מחיר נוכחי
        try:
            current_price = stock.fast_info["last_price"]
        except:
            current_price = data["Close"].iloc[-1] if not data.empty else None
            
        return data, current_price
    except Exception as e:
        # ניתן להוסיף הדפסה של e ל-debug במידת הצורך
        return None, None

# פונקציה להצגת גרף משופר
def plot_advanced_stock_graph(ticker, cost_price, stock_name):
    # כותרת משנה מימין לשמאל
    st.subheader(f"📈 ניתוח מעמיק: {stock_name}")
    
    # בחירת תקופה - משתמשים בעמודות כדי לאפשר עיצוב טוב יותר
    # ה-selectbox עצמו יופיע כראוי
    col1, col2 = st.columns([1, 4])
    with col1:
        period = st.selectbox(
            "תקופת תצוגה:",
            ["1mo", "3mo", "6mo", "1y", "2y", "5y"],
            index=3,
            # שינוי שמות האפשרויות לעברית
            format_func=lambda x: {
                "1mo": "חודש",
                "3mo": "3 חודשים",
                "6mo": "6 חודשים",
                "1y": "שנה",
                "2y": "שנתיים",
                "5y": "5 שנים"
            }[x]
        )
        
    # טעינת נתונים
    data, current_price = get_stock_data(ticker, period)
    
    if data is None or data.empty:
        st.error(f"❌ לא נמצאו נתונים עבור {ticker}")
        return
        
    if current_price is None:
        st.warning("⚠️ לא ניתן לקבל מחיר נוכחי, משתמש במחיר סגירה אחרון")
        current_price = data["Close"].iloc[-1]
        
    # חישוב שינויים
    change_abs = current_price - cost_price
    change_pct = (change_abs / cost_price) * 100
    
    # מטריקות
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        # מחיר עלות
        st.metric("מחיר עלות", f"${cost_price:.2f}")
    with col2:
        # מחיר נוכחי
        st.metric(
            "מחיר נוכחי", 
            f"${current_price:.2f}",
            f"${change_abs:.2f}"
        )
    with col3:
        # שינוי מצטבר
        st.metric(
            "שינוי מצטבר",
            f"{change_pct:.2f}%",
            f"${change_abs:.2f}"
        )
    with col4:
        # תקופה
        total_days = (data.index[-1] - data.index[0]).days
        st.metric("תקופה", f"{total_days} ימים")
        
    st.markdown("---")
    
    # יצירת הגרף - Plotly
    fig = go.Figure()
    
    # קו המחיר
    color = '#34A853' if change_pct >= 0 else '#EA4335'
    fig.add_trace(go.Scatter(
        x=data.index,
        y=data["Close"],
        mode='lines',
        name='שער סגירה',
        line=dict(color=color, width=2),
        fill='tozeroy',
        # מילוי צבע מעורפל
        fillcolor=f'rgba({int(color[1:3], 16)}, {int(color[3:5], 16)}, {int(color[5:7], 16)}, 0.15)',
        hovertemplate='<b>תאריך:</b> %{x}<br><b>מחיר:</b> $%{y:.2f}<extra></extra>'
    ))
    
    # קו מחיר העלות
    fig.add_trace(go.Scatter(
        x=[data.index[0], data.index[-1]],
        y=[cost_price, cost_price],
        mode='lines',
        name='מחיר עלות',
        line=dict(color='red', width=2, dash='dash'),
        hovertemplate='<b>מחיר עלות:</b> $%{y:.2f}<extra></extra>'
    ))
    
    # קו מחיר נוכחי
    fig.add_trace(go.Scatter(
        x=[data.index[-1]],
        y=[current_price],
        mode='markers',
        name='מחיר נוכחי',
        marker=dict(size=12, color='orange', symbol='star'),
        hovertemplate='<b>מחיר נוכחי:</b> $%{y:.2f}<extra></extra>'
    ))
    
    # עדכון פריסה - שינוי כיוון הטקסט והמיקום של הרכיבים
    fig.update_layout(
        title={
            'text': f"{ticker} - מעקב ביצועים", 
            'x': 0.5, # ממורכז
            'xanchor': 'center'
        },
        xaxis_title="תאריך",
        yaxis_title="מחיר ($)",
        template="plotly_white",
        height=600,
        hovermode='x unified',
        # הגדרת כיוון הטקסט הכללי כ-RTL (עבור עברית)
        # ומיקום המקרא (legend) למעלה ומימין
        legend=dict(
            orientation="h",
            yanchor="top",
            y=1.08, # מעל הגרף
            xanchor="right",
            x=1,
            title_font=dict(family='Arial', size=12),
            font=dict(family='Arial', size=10)
        ),
        # חשוב: הגדרת כיוון הפריסה ל-RTL
        font=dict(family='Arial', size=12),
        # זה לא תמיד הכרחי ב-Plotly אך יכול לעזור במקרים מסוימים
        # direction='rtl' 
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # סטטיסטיקות נוספות
    st.markdown("### 📊 סטטיסטיקות")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.info(f"**מחיר מינימלי:**\n${data['Close'].min():.2f}")
    with col2:
        st.info(f"**מחיר מקסימלי:**\n${data['Close'].max():.2f}")
    with col3:
        avg_price = data['Close'].mean()
        st.info(f"**מחיר ממוצע:**\n${avg_price:.2f}")
    with col4:
        volatility = data['Close'].std()
        st.info(f"**תנודתיות (SD):**\n${volatility:.2f}")
    
    # נתונים אחרונים
    # האקספנדר וכל הטקסט יופיעו כראוי מימין לשמאל
    with st.expander("📋 נתונים אחרונים (10 ימי מסחר)"):
        recent_data = data[['Open', 'High', 'Low', 'Close', 'Volume']].tail(10).copy()
        recent_data.columns = ['פתיחה', 'גבוה', 'נמוך', 'סגירה', 'נפח']
        recent_data = recent_data.round(2)
        # ה-dataframe של Streamlit תומך ב-RTL (במידה ויש טקסט עברי)
        st.dataframe(recent_data, use_container_width=True)

# יצירת כפתורי מניות
st.subheader("🎯 בחר מניה לניתוח")
cols_per_row = 6

# לולאה ליצירת כפתורים בשורות ועמודות
for i in range(0, len(df), cols_per_row):
    # שימוש ב-st.columns כדי ליצור שורה של עמודות
    cols = st.columns(cols_per_row)
    # צריך לוודא שאינדקס הטורים (j) מתחיל מהסוף עבור RTL
    # אבל Streamlit מנהל את הפריסה אוטומטית, נשמור על הלוגיקה המקורית
    for j in range(min(cols_per_row, len(df) - i)):
        if i + j >= len(df):
            break
            
        row = df.iloc[i + j]
        ticker = row["yfinance_ticker"]
        cost_price = row["מחיר עלות"]
        
        # הכנה של label נקי
        button_label = str(row["טיקר"]).strip()
        if button_label == "" or button_label.lower() == "nan":
            continue
            
        with cols[j]:
            # הכפתורים יופיעו מימין לשמאל בתוך העמודות
            if st.button(button_label, key=f"btn_{ticker}_{i}_{j}", use_container_width=True):
                st.session_state.selected_ticker = ticker
                st.session_state.selected_cost_price = cost_price
                st.session_state.selected_name = button_label
                # st.rerun() # אין צורך ב-rerun כי הלוגיקה מחוץ ללולאה תפעיל את plot_advanced_stock_graph
                
st.markdown("---")

# הצגת הגרף של המניה שנבחרה
if st.session_state.selected_ticker is not None:
    plot_advanced_stock_graph(
        st.session_state.selected_ticker,
        st.session_state.selected_cost_price,
        st.session_state.selected_name
    )
    
    # כפתור לניקוי הבחירה
    if st.button("🔙 חזרה לרשימת המניות", key="back_button"):
        st.session_state.selected_ticker = None
        st.session_state.selected_cost_price = None
        st.session_state.selected_name = None
        st.rerun()
else:
    # הודעת אינפו מימין לשמאל
    st.info("👆 בחר מניה מהרשימה למעלה כדי לראות ניתוח מפורט")

# footer
st.markdown("---")
# כיתוב קטן מימין לשמאל
st.caption(f"💡 נתונים מתעדכנים מ-Yahoo Finance | עודכן: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
