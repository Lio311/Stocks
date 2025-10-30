import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime, timedelta

# הגדרת הגדרות עמוד
st.set_page_config(page_title="תיק מניות", layout="wide")
st.title("📊 תיק המניות שלי")

# שם קובץ האקסל
file_path = "תיק מניות.xlsx"

# --- שלב 1: קריאה וניקוי נתונים ---

# קריאה של כל השורות ללא header כדי למצוא את שורת הכותרת האמיתית
try:
    df_raw = pd.read_excel(file_path, header=None)
except FileNotFoundError:
    st.error(f"שגיאה: הקובץ '{file_path}' לא נמצא. אנא ודא שהוא קיים באותה תיקיה.")
    st.stop()

# חיפוש שורה עם "שינוי מצטבר" כדי לזהות את הכותרות
header_row_idx = None
for i, row in df_raw.iterrows():
    # בדיקה אם אחת מהתאים בשורה מכילה את הטקסט 'שינוי מצטבר' (בצורה גמישה)
    if row.astype(str).str.strip().str.contains("שינוי מצטבר|מצטבר", case=False, na=False).any():
        header_row_idx = i
        break

if header_row_idx is None:
    st.error("לא נמצא שורת כותרת מתאימה (חפש 'שינוי מצטבר') בקובץ האקסל.")
    st.stop()

# קריאה מחדש של הקובץ עם שורת הכותרת הנכונה (האינדקס הוא 0-בסיס)
df = pd.read_excel(file_path, header=header_row_idx)

# ניקוי שמות העמודות
df.columns = [str(col).strip() for col in df.columns]

# סינון שורות ללא נתונים חיוניים
df = df.dropna(subset=["טיקר", "מחיר עלות"])

# ניקוי מחיר עלות והמרה למספר
# מסיר תווים שאינם ספרות, נקודה או סימן מינוס
df["מחיר עלות"] = df["מחיר עלות"].astype(str).str.replace(r'[^\d\.-]', '', regex=True)
df["מחיר עלות"] = pd.to_numeric(df["מחיר עלות"], errors='coerce')
df = df.dropna(subset=["מחיר עלות"])

# המרת טיקרים לפורמט yfinance
def convert_ticker(t):
    """ממיר פורמטים של טיקרים (כגון XNAS:, XLON:) לפורמט הנתמך על ידי yfinance."""
    t = str(t).strip()
    if t.startswith("XNAS:"):
        return t.split(":")[1]  # NASDAQ
    elif t.startswith("XLON:"):
        return t.split(":")[1] + ".L"  # LSE
    else:
        return t

df["yfinance_ticker"] = df["טיקר"].apply(convert_ticker)

# --- שלב 2: הגדרת מצב ומחולל גרף ---

# מצב המניה שנבחרה
if "selected_ticker" not in st.session_state:
    st.session_state.selected_ticker = None

# פונקציה להצגת גרף משופר
def plot_stock_graph(ticker, cost_price):
    """מציג גרף מניה עם קו מחיר עלות וצביעה לפי רווח/הפסד, החל מהתאריך הקרוב ביותר למחיר העלות."""
    
    # הורדת נתונים לטווח מקסימלי כדי לכסות את כל האפשרויות
    data = yf.download(ticker, period="max", progress=False) 
    
    if data.empty:
        st.warning(f"לא נמצאו נתונים היסטוריים עבור הטיקר: {ticker}. נסה לוודא את נכונות הטיקר.")
        return

    # 1. מציאת תאריך ההתחלה הרלוונטי (התאריך המוקדם ביותר שבו המחיר היה <= מחיר העלות)
    dates_at_or_below_cost = data[data["Close"] <= cost_price].index
    
    entry_date_found = not dates_at_or_below_cost.empty
    
    if entry_date_found:
        # התאריך המוקדם ביותר שהמניה נסגרה בו במחיר הקנייה או נמוך ממנו
        relevant_start_date = dates_at_or_below_cost[0]
    else:
        # אם המחיר תמיד היה גבוה יותר (בכל ההיסטוריה), נציג את ה-5 השנים האחרונות כברירת מחדל
        st.info("שימו לב: המחיר הנוכחי תמיד היה מעל מחיר העלות (בכל ההיסטוריה הזמינה). מציג את הגרף ל-5 שנים אחרונות.")
        relevant_start_date = datetime.now() - timedelta(days=5*365)
        
    # סינון הנתונים שיוצגו בגרף
    data_to_plot = data[data.index >= relevant_start_date].copy()
    
    # *** בדיקה קפדנית יותר לאחר הסינון ***
    if data_to_plot.empty:
        st.error(f"לא נמצאו נתונים היסטוריים להצגה עבור הטיקר {ticker} בטווח הרלוונטי. בדוק את הטיקר או את מחיר העלות.")
        # במקרה של נתונים ריקים, אין מה להציג
        return


    # מחיר נוכחי בזמן אמת (ניסיון ראשון)
    try:
        current_price = yf.Ticker(ticker).fast_info["last_price"]
    except Exception:
        # אם אין מידע "מהיר", השתמש בשער הסגירה האחרון מתוך הנתונים שהורדו
        current_price = data_to_plot["Close"].iloc[-1] 
    
    # חישוב שינוי מצטבר
    change_pct = ((current_price - cost_price) / cost_price) * 100
    
    # קביעת צבע קו המניה בהתאם לרווח/הפסד
    line_color = '#10B981' if current_price >= cost_price else '#EF4444' # ירוק לרווח, אדום להפסד

    fig = go.Figure()
    
    # הוספת קו שער הסגירה (צבוע לפי סטטוס רווח/הפסד)
    fig.add_trace(go.Scatter(
        x=data_to_plot.index, 
        y=data_to_plot["Close"], 
        mode='lines', 
        name='שער סגירה',
        line=dict(color=line_color, width=3)
    ))

    # --- הוספת סמן לנקודת הכניסה המשוערת (המחיר והתאריך בו המחיר היה ≤ מחיר העלות) ---
    if entry_date_found:
        fig.add_trace(go.Scatter(
            x=[relevant_start_date], 
            y=[cost_price], 
            mode='markers', 
            name='נקודת קנייה משוערת',
            marker=dict(size=16, color='Blue', symbol='star', line=dict(width=2, color='White'))
        ))
    
    # --- הוספת סמן למחיר הנוכחי (הנקודה האחרונה על הקו) ---
    fig.add_trace(go.Scatter(
        x=[data_to_plot.index[-1]], 
        y=[current_price], 
        mode='markers', 
        name='מחיר נוכחי',
        # צבע הסמן יהיה זהה לצבע הקו (ירוק/אדום)
        marker=dict(size=14, color=line_color, symbol='circle', line=dict(width=2, color='white')) 
    ))
    
    # הוספת קו מחיר העלות (בולט יותר)
    fig.add_hline(
        y=cost_price, 
        line=dict(color='orange', dash='dot', width=2), 
        name='מחיר עלות'
    )
    
    # הוספת הערה (Annotation) למחיר העלות על הגרף
    fig.add_annotation(
        x=data_to_plot.index[-1], # תאריך אחרון בנתונים
        y=cost_price, 
        text=f"מחיר עלות: {cost_price:.2f}",
        showarrow=False,
        xshift=50, # הזזה קלה ימינה
        font=dict(size=14, color="orange"),
        bgcolor="rgba(255, 255, 255, 0.9)",
        bordercolor="orange",
        borderpad=4
    )

    # עדכון פריסת הגרף
    st.markdown(f"### {ticker} - ניתוח ביצועים")
    
    # הצגת נתונים מרכזיים
    col1, col2 = st.columns(2)
    with col1:
        st.metric(label="מחיר נוכחי", value=f"{current_price:.2f}")
    with col2:
        st.metric(
            label="שינוי מצטבר", 
            value=f"{change_pct:.2f}%", 
            delta=f"{current_price - cost_price:.2f}"
        )
    
    # הגדרת טווח Y דינמי עם מעט מרווח בטחון
    
    # *** התיקון לטיפול ב-NaN ובסדרות חסרות נתונים בטווח Y ***
    # .dropna() מבטיח שלא נכשל על NaN, ו-data_to_plot.empty כבר מטפל בסדרה ריקה לחלוטין.
    close_prices = data_to_plot["Close"].dropna()
    
    if close_prices.empty:
        # אם אין נתונים מספריים, נשתמש רק במחיר העלות לטווח ה-Y
        min_y = cost_price * 0.98
        max_y = cost_price * 1.02
    else:
        min_y = min(close_prices.min(), cost_price) * 0.98
        max_y = max(close_prices.max(), cost_price) * 1.02


    fig.update_layout(
        title={
            'text': f"תנודת המניה {ticker} (החל מהתאריך בו המחיר היה ≤ {cost_price:.2f})",
            'y':0.95,
            'x':0.5,
            'xanchor': 'center',
            'yanchor': 'top'
        },
        xaxis_title="תאריך",
        yaxis_title="שער",
        template="plotly_white",
        height=600,
        margin=dict(l=20, r=20, t=50, b=20),
        # הגדרת טווח Y דינמי
        yaxis_range=[min_y, max_y], 
    )

    st.plotly_chart(fig, use_container_width=True)

# --- שלב 3: יצירת כפתורי הניווט והצגת הגרף ---

st.markdown("---")
st.subheader("בחר מניה להצגת גרף:")

# יצירת כפתורים בראש העמוד
cols_per_row = 6
for i in range(0, len(df), cols_per_row):
    cols = st.columns(min(cols_per_row, len(df) - i))
    for j, col in enumerate(cols):
        row = df.iloc[i + j]
        ticker = row["yfinance_ticker"]
        cost_price = row["מחיר עלות"]

        # הכנה של label נקי
        button_label = str(row["טיקר"]).strip()
        
        if button_label == "" or button_label.lower() == "nan":
            continue  # דילוג על שורות ריקות

        # עיצוב כפתורים פשוט
        button_key = f"btn_{ticker}_{i+j}"
        
        # שימוש במתקן כדי לאפשר לחיצה על הכפתור ועדכון ה-state
        with col:
            if st.button(button_label, key=button_key):
                st.session_state.selected_ticker = ticker
                st.session_state.selected_cost_price = cost_price


# הצגת הגרף של המניה שנבחרה
if st.session_state.selected_ticker:
    st.markdown("---")
    plot_stock_graph(
        st.session_state.selected_ticker,
        st.session_state.selected_cost_price
    )
else:
    st.info("אנא בחר מניה מהכפתורים שלמעלה כדי לראות את הגרף שלה.")
