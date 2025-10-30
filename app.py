import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime, timedelta

# הגדרת הגדרות עמוד
st.set_page_config(page_title="גרף מניית גוגל", layout="wide")
st.title("📈 תנודת שער מניית Alphabet Inc. (GOOG)")

# --- הגדרות גרף ---

# הגדרות מניה
TICKER = "GOOG" # Alphabet Inc. Class C
PERIOD = "5d"   # חמישה ימים אחרונים (כדי לדמות מבט קרוב)
INTERVAL = "1h" # תדירות שעתית (כדי לדמות רציפות תוך-יומית)

# צבעי גרף
LINE_COLOR = '#047857' # ירוק כהה
FILL_COLOR = 'rgba(16, 185, 129, 0.4)' # ירוק שקוף

def plot_google_stock_graph():
    """מוריד ומציג גרף שטח (Area Chart) נקי של מניית גוגל (GOOG)."""
    
    # הורדת נתונים מ-Yahoo Finance
    st.subheader(f"נתונים ל-{PERIOD} אחרונים, בתדירות {INTERVAL}")
    data = yf.download(TICKER, period=PERIOD, interval=INTERVAL, progress=False) 
    
    if data.empty:
        st.error(f"לא ניתן לטעון נתונים עבור הטיקר {TICKER} בטווח הנדרש.")
        return

    data_to_plot = data["Close"].dropna()
    
    if data_to_plot.empty:
        st.error(f"אין נתוני סגירה זמינים עבור הטיקר {TICKER} לאחר ניקוי.")
        return

    # מחיר נוכחי בזמן אמת
    try:
        current_price = yf.Ticker(TICKER).fast_info["last_price"]
    except Exception:
        current_price = data_to_plot.iloc[-1] 
    
    # שער הסגירה היומי הקודם (משמש כקו ייחוס סטנדרטי)
    # ננסה למצוא את שער הסגירה האחרון לפני הנתונים המוצגים (אחרי סינון NaN)
    try:
        data_daily = yf.download(TICKER, period="6d", interval="1d", progress=False)
        previous_close = data_daily["Close"].iloc[-2]
    except Exception:
        previous_close = None # אם לא נמצא, לא נציג את הקו

    # --- יצירת הגרף (Area Chart) ---
    
    fig = go.Figure()
    
    # טרייס ראשי: גרף שטח עם קו
    fig.add_trace(go.Scatter(
        x=data_to_plot.index, 
        y=data_to_plot, 
        mode='lines', 
        name='שער סגירה',
        line=dict(color=LINE_COLOR, width=3),
        fill='tozeroy', # מילוי עד ציר ה-Y=0
        fillcolor=FILL_COLOR 
    ))

    # הוספת קו שער הסגירה הקודם (כמו Prev. close בתמונה)
    if previous_close is not None:
        fig.add_hline(
            y=previous_close, 
            line=dict(color='gray', dash='dot', width=1), 
            name='שער סגירה קודם'
        )
        fig.add_annotation(
            x=data_to_plot.index[-1],
            y=previous_close,
            text=f"Prev. close: {previous_close:.2f}",
            showarrow=False,
            xshift=70,
            yshift=0,
            font=dict(size=12, color="gray"),
        )


    # --- הגדרת טווח Y דינמי ---
    min_y = data_to_plot.min() * 0.99
    max_y = data_to_plot.max() * 1.01

    # --- עדכון פריסת הגרף ---
    fig.update_layout(
        title={
            'text': f"תנועת שער {TICKER} - מחיר נוכחי: {current_price:.2f}",
            'y':0.95,
            'x':0.5,
            'xanchor': 'center',
            'yanchor': 'top'
        },
        xaxis_title="זמן",
        yaxis_title="שער ($)",
        template="plotly_white",
        height=600,
        margin=dict(l=20, r=20, t=50, b=20),
        # מראה נקי (הסרת קווי רשת)
        xaxis=dict(
            showgrid=False, 
            tickformat="%H:%M\n%b %d", 
            rangeselector=dict(
                buttons=list([
                    dict(count=1, label="1D", step="day", stepmode="backward"),
                    dict(count=5, label="5D", step="day", stepmode="backward"),
                    dict(count=1, label="1M", step="month", stepmode="backward"),
                    dict(step="all")
                ])
            )
        ),
        yaxis=dict(showgrid=False),
        yaxis_range=[min_y, max_y],
        hovermode="x unified" # אופטימיזציה ל-Hovering
    )

    st.plotly_chart(fig, use_container_width=True)

# --- קריאה לפונקציה הראשית ---
plot_google_stock_graph()
