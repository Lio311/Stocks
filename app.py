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
    """מציג גרף מניה עם קו מחיר עלות וצביעה לפי רווח/הפסד, עם דגש על מראה נקי (כמו בתמונה)."""
    
    # הורדת נתונים לטווח של 5 שנים אחרונות כברירת מחדל
    # בחרתי ב-5 שנים כדי לאפשר איתור מחיר קנייה ישן, אך נציג רק את החודש האחרון.
    data = yf.download(ticker, period="5y", progress=False) 
    
    if data.empty:
        st.warning(f"לא נמצאו נתונים היסטוריים עבור הטיקר: {ticker}. נסה לוודא את נכונות הטיקר.")
        return

    # מציאת תאריך ההתחלה הרלוונטי לצורך חישובים
    dates_at_or_below_cost = data[data["Close"] <= cost_price].index
    
    # 1. מציאת תאריך ההתחלה הרלוונטי (התאריך המוקדם ביותר שבו המחיר היה <= מחיר העלות)
    entry_date_found = not dates_at_or_below_cost.empty
    
    if entry_date_found:
        # התאריך המוקדם ביותר שהמניה נסגרה בו במחיר הקנייה או נמוך ממנו
        calculation_start_date = dates_at_or_below_cost[0]
    else:
        # אם המחיר תמיד היה גבוה יותר, נשתמש ב-5 שנים לצורך החישוב
        calculation_start_date = datetime.now() - timedelta(days=5*365)
        
    # סינון הנתונים לצורך הצגה: נציג רק את החודש האחרון כדי לדמות "זום"
    display_start_date = datetime.now() - timedelta(days=30)
    data_to_plot = data[data.index >= display_start_date].copy()
    
    # *** בדיקה קפדנית יותר לאחר הסינון ***
    if data_to_plot.empty:
        st.error(f"לא נמצאו נתונים היסטוריים להצגה עבור הטיקר {ticker} בחודש האחרון. ייתכן ואין מסחר.")
        return

    # מחיר נוכחי בזמן אמת (ניסיון ראשון)
    try:
        current_price = yf.Ticker(ticker).fast_info["last_price"]
    except Exception:
        # אם אין מידע "מהיר", השתמש בשער הסגירה האחרון מתוך הנתונים שהורדו
        current_price = data_to_plot["Close"].iloc[-1] 
    
    # חישוב נתוני רווח/הפסד (באמצעות כלל הנתונים שנמצאו)
    data_for_calc = data[data.index >= calculation_start_date].copy()
    
    # מחיר כניסה משוער, לצורך חישובים:
    # נניח שזה מחיר העלות אם נמצא תאריך, או מחיר הסגירה ביום תחילת החישוב אם לא
    if entry_date_found:
        # אם מצאנו תאריך רלוונטי, נשתמש במחיר העלות שנתן המשתמש
        entry_price = cost_price
    else:
        # אם לא מצאנו, נשתמש במחיר העלות שהוזן, אך נציין שהרווח הוא מהתחלה
        entry_price = cost_price

    # חישוב שינוי מצטבר
    change_pct = ((current_price - entry_price) / entry_price) * 100
    
    # קביעת צבע קו המניה בהתאם לרווח/הפסד
    # צבע קו ומילוי: ירוק כהה / אדום כהה
    line_color = '#047857' if current_price >= cost_price else '#B91C1C' 
    fill_color = 'rgba(16, 185, 129, 0.4)' if current_price >= cost_price else 'rgba(239, 68, 68, 0.4)'

    fig = go.Figure()
    
    # הוספת קו שער הסגירה (גרף שטח נקי)
    fig.add_trace(go.Scatter(
        x=data_to_plot.index, 
        y=data_to_plot["Close"], 
        mode='lines', 
        name='שער סגירה',
        line=dict(color=line_color, width=3),
        fill='tozeroy', # מילוי עד ציר ה-Y=0
        fillcolor=fill_color # צבע המילוי
    ))

    # *** שינוי: הסרת קו מחיר עלות וסמנים מהגרף כדי לדמות מראה נקי יותר ***
    # הנתונים הללו עדיין מוצגים ב-Metrics.

    # עדכון פריסת הגרף
    st.markdown(f"### {ticker} - ניתוח ביצועים")
    
    # הצגת נתונים מרכזיים
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(label="מחיר נוכחי", value=f"{current_price:.2f}")
    with col2:
        st.metric(
            label="שינוי מצטבר (משער העלות)", 
            value=f"{change_pct:.2f}%", 
            delta=f"{current_price - cost_price:.2f}"
        )
    with col3:
         st.metric(label="מחיר עלות", value=f"{cost_price:.2f}")
    
    # הגדרת טווח Y דינמי עם מעט מרווח בטחון
    
    close_prices = data_to_plot["Close"].dropna()
    
    if close_prices.empty:
        # אם אין נתונים מספריים, נשתמש בטווח קטן סביב המחיר הנוכחי
        min_y = current_price * 0.98
        max_y = current_price * 1.02
    else:
        # שימוש בטוח ב min/max עבור הנתונים המוצגים
        min_y = close_prices.min() * 0.99
        max_y = close_prices.max() * 1.01


    fig.update_layout(
        title={
            'text': f"תנודת המניה {ticker} (30 יום אחרונים)",
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
        # הסרת קווי רשת אופקיים/אנכיים למראה נקי
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=False),
        # הגדרת טווח Y דינמי
        yaxis_range=[min_y, max_y], 
    )

    st.plotly_chart(fig, use_container_width=True)

# פונקציה להצגת גרף רגיל של מניית גוגל (GOOG)
def plot_standard_google_graph():
    """מציג גרף סטנדרטי של GOOG לחודש האחרון (כמו בתמונה)."""
    st.markdown("---")
    st.markdown("### 📈 גרף ייחוס סטנדרטי: Alphabet (GOOG) - 30 יום אחרונים")
    
    start_date = datetime.now() - timedelta(days=30) # טווח של 30 יום
    data = yf.download("GOOG", start=start_date, progress=False)
    
    if data.empty:
        st.warning("לא ניתן לטעון נתונים עבור GOOG.")
        return

    # צבע ירוק-כחול סטנדרטי לגרף הייחוס
    line_color = '#4285F4' 
    fill_color = 'rgba(66, 133, 244, 0.4)' # כחול גוגל שקוף

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=data.index, 
        y=data["Close"], 
        mode='lines', 
        name='שער סגירה',
        line=dict(color=line_color, width=3), 
        fill='tozeroy', # מילוי עד ציר ה-Y=0
        fillcolor=fill_color # צבע המילוי
    ))

    fig.update_layout(
        title='GOOG - שער סגירה לחודש האחרון',
        xaxis_title="תאריך",
        yaxis_title="שער",
        template="plotly_white",
        height=400,
        margin=dict(l=20, r=20, t=50, b=20),
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=False),
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

# הצגת גרף גוגל סטנדרטי (GOOG) תמיד
plot_standard_google_graph()
