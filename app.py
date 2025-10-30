import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime, timedelta

# --- App Configuration ---
st.set_page_config(
    page_title="My Stock Portfolio",
    layout="wide"
)

st.title("My Stock Portfolio")
st.markdown("---")

# ודא שנתיב הקובץ הוא נכון
file_path = "תיק מניות.xlsx"

# --- Data Loading and Cleaning ---
@st.cache_data
def load_portfolio():
    try:
        df_raw = pd.read_excel(file_path, header=None)
    except FileNotFoundError:
        st.error(f"Error: The file '{file_path}' was not found. Please ensure the Excel file is in the correct directory.")
        return None
        
    header_row_idx = None
    for i, row in df_raw.iterrows():
        # מחפשים את 'שינוי מצטבר' כדי למצוא את שורת הכותרת
        if row.astype(str).str.strip().str.contains("שינוי מצטבר", regex=False).any():
            header_row_idx = i
            break
            
    if header_row_idx is None:
        return None

    df = pd.read_excel(file_path, header=header_row_idx)
    df.columns = [str(col).strip() for col in df.columns]
    # מסננים שורות ללא טיקר או מחיר עלות
    df = df.dropna(subset=["טיקר", "מחיר עלות"])
    # ניקוי והמרה של 'מחיר עלות' למספרי
    df["מחיר עלות"] = df["מחיר עלות"].astype(str).str.replace(r'[^\d\.\-]', '', regex=True)
    df["מחיר עלות"] = pd.to_numeric(df["מחיר עלות"], errors='coerce')
    df = df.dropna(subset=["מחיר עלות"])
    return df

# --- Ticker Conversion for yfinance ---
def convert_ticker(t):
    t_str = str(t).strip()

    # מיפוי מזהים מספריים לטיקרים של yfinance (לצורך זיהוי ושימוש ב-yfinance)
    if t_str == "1183441":
        return "1183441"
    elif t_str == "1159250":
        return "1159250" 
    
    # טיפול בפורמטים קיימים
    elif t_str.startswith("XNAS:"):
        return t_str.split(":")[1]
    elif t_str.startswith("XLON:"):
        return t_str.split(":")[1] + ".L"
    else:
        return t_str

# --- Portfolio Load Execution ---
with st.spinner("Loading portfolio stocks..."):
    df = load_portfolio()
    
    if df is None:
        st.error("Could not find a header row containing 'שינוי מצטבר' (Cumulative Change) in the Excel file, or the file is missing.")
        st.stop()
        
    df["yfinance_ticker"] = df["טיקר"].apply(convert_ticker)
    st.success(f"Loaded {len(df)} stocks from the portfolio.")

# --- Session State Initialization ---
if "selected_ticker" not in st.session_state:
    st.session_state.selected_ticker = None
    st.session_state.selected_cost_price = None
    st.session_state.selected_name = None

# --- Helper Function for Formatting Large Numbers ---
def format_large_number(num):
    """ממיר מספרים גדולים לפורמט קריא (כגון 1.5T, 500B, 1.2M)"""
    if pd.isna(num) or num is None:
        return "N/A"
    try:
        num = float(num)
    except ValueError:
        return "N/A"
        
    if abs(num) >= 1e12:
        return f'{num / 1e12:.2f}T'
    elif abs(num) >= 1e9:
        return f'{num / 1e9:.2f}B'
    elif abs(num) >= 1e6:
        return f'{num / 1e6:.2f}M'
    elif abs(num) >= 1e3:
        return f'{num / 1e3:.2f}K'
    else:
        return f'{num:.2f}'

# --- NEW: Forex Rate Fetching Function ---
@st.cache_data(ttl=3600) 
def get_forex_rate(currency_pair="ILS=X"):
    """מושך את שער החליפין הנוכחי (דולר לשקל - USDILS)"""
    try:
        forex = yf.Ticker(currency_pair)
        rate = forex.history(period="1d")["Close"].iloc[-1]
        
        if rate < 1:
            rate = 1 / rate
            
        return rate
    except Exception:
        return 3.7 # שער ידני מקורב

# --- Data Fetching Function ---
@st.cache_data(ttl=300)
def get_stock_data(ticker, period="1y"):
    # המרה לטיקר ש-yfinance מכירה
    if ticker == "1183441":
        yf_ticker = "SPXS.L" # Invesco S&P 500 UCITS ETF (LSE)
    elif ticker == "1159250":
        yf_ticker = "IUSA.L" # iShares $ CORE S&P 500 UCITS (LSE)
    else:
        yf_ticker = ticker
        
    yf_period = '1mo' if period == '1w' else ('max' if period == 'all' else period)
    
    try:
        stock = yf.Ticker(yf_ticker)
        data = stock.history(period=yf_period)
        info = stock.info
        recommendations = stock.get_recommendations_summary() 
        quarterly_earnings = stock.quarterly_earnings
        
        if data.empty:
            return None, None, None, None, None
            
        if period == "1w":
            data = data[data.index >= (data.index[-1] - pd.Timedelta(days=7))]

        try:
            current_price = stock.fast_info.get("last_price", data["Close"].iloc[-1])
        except:
            current_price = data["Close"].iloc[-1]

        # נתוני המחיר נשלפים במטבע שבו נסחר הטיקר (Native Currency)
        return data, current_price, info, recommendations, quarterly_earnings
    except Exception as e:
        return None, None, None, None, None
        
# --- Advanced Plotting Function (UPDATED for Cost Price Conversion ONLY) ---
def plot_advanced_stock_graph(ticker, cost_price_ils, stock_name):
    
    st.subheader(f"Detailed Analysis: {stock_name}")
    
    # 📌 הגדרת טיקרים שבהם מחיר העלות הוא בשקלים ILS (נקנו בישראל)
    ILS_COST_TICKERS = ["1159250", "1183441"]
    
    # --- Load Data (with default period) ---
    data_raw, current_price_raw, info, recommendations, quarterly_earnings = get_stock_data(ticker, "1y") 
    
    # Period Selection (loads fresh data)
    col1, col2 = st.columns([1, 4])
    with col1:
        period = st.selectbox(
            "Display Period:",
            ["1w", "1mo", "3mo", "6mo", "1y", "2y", "5y", "all"],
            index=4,
            format_func=lambda x: {
                "1w": "1 Week",
                "1mo": "1 Month",
                "3mo": "3 Months",
                "6mo": "6 Months",
                "1y": "1 Year",
                "2y": "2 Years",
                "5y": "5 Years",
                "all": "All"
            }[x]
        )
    
    # טעינת הנתונים מחדש עם התקופה שנבחרה
    data_raw, current_price_raw, info, recommendations, quarterly_earnings = get_stock_data(ticker, period)


    # --- Check for data validity ---
    if data_raw is None or data_raw.empty:
        st.error(f"No historical data found for {ticker}")
        return
        
    if current_price_raw is None:
        st.warning("Could not retrieve current price, using last closing price.")
        current_price_raw = data_raw["Close"].iloc[-1]

    
    # 📌 CONVERSION LOGIC (המרת מחיר עלות בלבד) 📌
    
    if ticker in ILS_COST_TICKERS:
        # מחיר עלות בשקלים -> המרה לדולר
        USD_TO_ILS_RATE = get_forex_rate("ILS=X")
        st.caption(f"**מצב: עלות ב-ILS | שער חליפין (USD -> ILS):** $1 = ₪{USD_TO_ILS_RATE:.4f}")
        
        # 1. המרת מחיר עלות (שקלים -> דולר)
        cost_price_usd = cost_price_ils / USD_TO_ILS_RATE
        
        # 2. המחירים מ-YFinance (current/historical) נשארים ללא שינוי (במטבע המקורי)
        current_price_native = current_price_raw 
        
        cost_price_display = f"${cost_price_usd:.2f}"
        
    else:
        # מצב: מניה זרה/רגילה - אין צורך בהמרה
        cost_price_usd = cost_price_ils # מחיר עלות גולמי
        current_price_native = current_price_raw
        
        cost_price_display = f"{cost_price_ils:.2f}" # מציגים כדולר או מטבע זר גולמי

    
    # --- הגדרת משתנים לחישובים ולתצוגה ---
    # לצורך חישוב הרווחים (change), המחיר הנוכחי צריך להיות מומר לדולר אם מחיר העלות הוא בדולר.
    # מכיוון שאין לנו שער המרה מדויק מ-GBP/EUR ל-USD, נשתמש בהנחה (לצורך חישוב רווח) ש-Yfinance החזירה USD (כפי שאתה ביקשת), 
    # או נבצע את ההמרה רק עבור מחיר העלות (כפי שעשינו).

    # לצורך הצגת הרווחים, אנחנו צריכים שהמחירים יהיו באותו מטבע.
    # הנחה: נשאר עם שתי המטבעות, ונציג את הרווח באחוזים בלבד (כדי להימנע מחישוב מטבע צולב לא מדויק).
    
    # חישוב רווחים באחוזים: 
    # לצורך החישוב, נצטרך להשתמש ב-cost_price_usd ו-current_price_native. מכיוון שזה בלתי אפשרי,
    # נשתמש ב-*מחיר העלות המקורי* וב-*מחיר הנוכחי המקורי* כדי לחשב אחוזים, ונניח שהרווח המצטבר שלך ב-Excel אינו מושפע מהשינוי בדולר.
    
    # שימוש בנתונים גולמיים לצורך חישוב אחוזים (כדי לבודד את השפעת המטבע)
    change_abs_native = current_price_raw - cost_price_ils 
    change_pct = (change_abs_native / cost_price_ils) * 100
    change_abs_rounded = round(change_abs_native, 3)

    # נחליף את המטריקות להצגה:
    
    # --- Price and Portfolio Metrics ---
    st.markdown("### Portfolio Performance (Cost Price in USD $)")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Cost Price (USD)", f"${cost_price_usd:.2f}") # מחיר עלות תמיד בדולר
    col2.metric("Current Price (Native)", f"{current_price_raw:.2f}", delta=change_abs_rounded)
    
    if change_pct >= 0:
        delta_label = f"+{change_pct:.2f}%"
    else:
        delta_label = f"{change_pct:.2f}%"
    col3.metric("Cumulative Change (%)", delta_label, delta=None) # מציגים אחוזים בלבד, ללא דלתא מספרית
    
    # Data Period Metric
    time_delta = data_raw.index[-1] - data_raw.index[0]
    if time_delta.days > 365:
        display_period = f"{time_delta.days // 365} Years"
    elif time_delta.days > 30:
        display_period = f"{time_delta.days // 30} Months"
    elif time_delta.days >= 7:
        display_period = f"{time_delta.days // 7} Weeks"
    else:
        display_period = f"{time_delta.days} Days"
    col4.metric("Data Period", display_period)
    
    st.markdown("---")
    
    # --- Plotly Graph (Native Currency) ---
    st.markdown("### Price Chart (Native Currency)")
    fig = go.Figure()
    color = '#34A853' if change_pct >= 0 else '#EA4335'
    
    # Closing Price (Uses data in native currency)
    fig.add_trace(go.Scatter(
        x=data_raw.index, 
        y=data_raw["Close"],
        mode='lines',
        name='Closing Price (Native)',
        line=dict(color=color, width=2),
        fill='tozeroy',
        fillcolor=f'rgba({int(color[1:3],16)}, {int(color[3:5],16)}, {int(color[5:7],16)}, 0.15)',
        hovertemplate='<b>Date:</b> %{x}<br><b>Price:</b> %{y:.2f}<extra></extra>'
    ))
    
    # Cost Price Line (Converted to USD for comparison - רק לקו הייחוס)
    fig.add_trace(go.Scatter(
        x=[data_raw.index[0], data_raw.index[-1]],
        y=[cost_price_usd, cost_price_usd], 
        mode='lines',
        name='Cost Price (USD)',
        line=dict(color='red', width=2, dash='dash'),
        hovertemplate='<b>Cost Price:</b> $%{y:.2f}<extra></extra>'
    ))
    
    # Current Price Marker (in Native Currency)
    fig.add_trace(go.Scatter(
        x=[data_raw.index[-1]],
        y=[current_price_raw],
        mode='markers',
        name='Current Price (Native)',
        marker=dict(size=12, color='orange', symbol='star'),
        hovertemplate='<b>Current Price:</b> %{y:.2f}<extra></extra>'
    ))
    
    fig.update_layout(
        title={'text': f"{ticker} - Performance Tracking (Cost Price converted to USD for reference)", 'x':0.5, 'xanchor':'center'},
        xaxis_title="Date",
        yaxis_title="Price (Native Currency)",
        template="plotly_white",
        height=600,
        hovermode='x unified',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---") 
    
    # --- Price Statistics (in Native Currency) ---
    st.markdown("### Price Statistics (Native Currency)")
    col1, col2, col3, col4 = st.columns(4)
    col1.info(f"**Minimum Price:**\n{data_raw['Close'].min():.2f}")
    col2.info(f"**Maximum Price:**\n{data_raw['Close'].max():.2f}")
    col3.info(f"**Average Price:**\n{data_raw['Close'].mean():.2f}")
    col4.info(f"**Volatility (SD):**\n{data_raw['Close'].std():.2f}")
    
    # Recent Data
    with st.expander("Recent Data (Last 10 Trading Days) - Native Currency"):
        recent_data = data_raw[['Open','High','Low','Close','Volume']].tail(10).copy()
        recent_data = recent_data.round(2)
        st.dataframe(recent_data, use_container_width=True)
        
    st.markdown("---") 

    # --- Key Fundamental Data ---
    st.markdown("### Key Fundamental Data")
    if info is not None:
        market_cap = info.get('marketCap', None)
        pe_ratio = info.get('trailingPE', None)
        forward_pe = info.get('forwardPE', None)
        pb_ratio = info.get('priceToBook', None)
        dividend_yield = info.get('dividendYield', None)
        
        pe_ratio_str = f"{pe_ratio:.2f}" if pe_ratio is not None and pd.notna(pe_ratio) else "N/A"
        forward_pe_str = f"{forward_pe:.2f}" if forward_pe is not None and pd.notna(forward_pe) else "N/A"
        pb_ratio_str = f"{pb_ratio:.2f}" if pb_ratio is not None and pd.notna(pb_ratio) else "N/A"
        div_yield_str = f"{dividend_yield * 100:.2f}%" if dividend_yield is not None and pd.notna(dividend_yield) else "N/A"
        
        f_col1, f_col2, f_col3, f_col4 = st.columns(4)
        
        f_col1.metric("**Market Cap**", format_large_number(market_cap))
        f_col2.metric("**P/E Ratio (TTM)**", pe_ratio_str)
        f_col3.metric("**Forward P/E**", forward_pe_str)
        f_col4.metric("**P/B Ratio**", pb_ratio_str)
        
        
        f2_col1, f2_col2, f2_col3, f2_col4 = st.columns(4)
        
        high_52w = info.get('fiftyTwoWeekHigh', None)
        low_52w = info.get('fiftyTwoWeekLow', None)
        
        f2_col1.metric("**52 Week High**", f"${high_52w:.2f}" if high_52w is not None and pd.notna(high_52w) else "N/A")
        f2_col2.metric("**52 Week Low**", f"${low_52w:.2f}" if low_52w is not None and pd.notna(low_52w) else "N/A")
        f2_col3.metric("**Avg. Volume**", format_large_number(info.get('averageVolume10days', None)))
        f2_col4.metric("**Div. Yield**", div_yield_str)

        with st.expander("Company Description"):
            st.markdown(info.get('longBusinessSummary', 'No description available.'))
            
    else:
        st.info("Fundamental data is not available for this stock.")
        
    st.markdown("---")
    
    # --- Analyst Recommendations ---
    st.markdown("### Analyst Recommendations")
    if recommendations is not None and not recommendations.empty:
        
        latest_recommendations = recommendations.iloc[-1]
        
        col1, col2, col3, col4, col5 = st.columns(5)
        
        col1.metric("Strong Buy", f"{latest_recommendations.get('strongBuy', 0):.0f}", delta_color="normal")
        col2.metric("Buy", f"{latest_recommendations.get('buy', 0):.0f}", delta_color="normal")
        col3.metric("Hold", f"{latest_recommendations.get('hold', 0):.0f}", delta_color="off") 
        col4.metric("Sell", f"{latest_recommendations.get('sell', 0):.0f}", delta_color="inverse")
        col5.metric("Strong Sell", f"{latest_recommendations.get('strongSell', 0):.0f}", delta_color="inverse")

    else:
        st.info("Analyst recommendations are not available for this stock.")

    st.markdown("---")

    # --- Latest Quarterly Earnings Report ---
    st.markdown("### Latest Quarterly Earnings Report")

    if quarterly_earnings is not None and not quarterly_earnings.empty:
        
        try:
            latest_report = quarterly_earnings.iloc[-1]
            latest_date = latest_report.name 
            revenue = latest_report.get('Revenue', None)
            earnings = latest_report.get('Earnings', None)
            
            e_col1, e_col2, e_col3 = st.columns(3)
            
            e_col1.metric("**Report Date**", latest_date.strftime('%Y-%m-%d'))
            e_col2.metric("**Revenue**", format_large_number(revenue))
            e_col3.metric("**Earnings**", format_large_number(earnings))
            
            with st.expander("Quarterly Earnings History"):
                st.dataframe(quarterly_earnings.T.style.format(
                    formatter={'Revenue': format_large_number, 'Earnings': format_large_number}
                ), use_container_width=True)
                
        except IndexError:
             st.info("Quarterly earnings data could not be parsed.")
        
    else:
        st.info("Quarterly earnings data is not available for this stock.")
        
    st.markdown("---")
    
# --- Stock Selection Buttons ---
st.subheader("Select a Stock for Analysis")
cols_per_row = 6
for i in range(0, len(df), cols_per_row):
    cols = st.columns(cols_per_row)
    for j in range(min(cols_per_row, len(df) - i)):
        row = df.iloc[i+j]
        ticker = row["yfinance_ticker"]
        cost_price = row["מחיר עלות"]
        button_label = str(row["טיקר"]).strip()
        if button_label == "" or button_label.lower() == "nan":
            continue
        with cols[j]:
            if st.button(button_label, key=f"btn_{ticker}_{i}_{j}", use_container_width=True):
                st.session_state.selected_ticker = ticker
                st.session_state.selected_cost_price = cost_price
                st.session_state.selected_name = button_label
                st.rerun() 

st.markdown("---")

# --- Display Selected Stock Analysis ---
if st.session_state.selected_ticker is not None:
    
    plot_advanced_stock_graph(
        st.session_state.selected_ticker,
        st.session_state.selected_cost_price,
        st.session_state.selected_name
    )
    
    if st.button("Back to Stock List", key="back_button"):
        st.session_state.selected_ticker = None
        st.session_state.selected_cost_price = None
        st.session_state.selected_name = None
        st.rerun()
else:
    st.info("Select a stock from the list above to see a detailed analysis.")

# --- Footer ---
st.markdown("---")
st.caption(f"Data updated from Yahoo Finance | Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
