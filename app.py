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

file_path = "תיק מניות.xlsx"

# --- Data Loading and Cleaning ---
@st.cache_data
def load_portfolio():
    df_raw = pd.read_excel(file_path, header=None)
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
    df["מחיר עלות"] = df["מחיר עלות"].astype(str).str.replace(r'[^\d\.-]', '', regex=True)
    df["מחיר עלות"] = pd.to_numeric(df["מחיר עלות"], errors='coerce')
    df = df.dropna(subset=["מחיר עלות"])
    return df

# --- Ticker Conversion for yfinance ---
def convert_ticker(t):
    t = str(t).strip()
    if t.startswith("XNAS:"):
        return t.split(":")[1]
    elif t.startswith("XLON:"):
        return t.split(":")[1] + ".L"
    else:
        return t

# --- Portfolio Load Execution ---
with st.spinner("Loading portfolio stocks..."):
    df = load_portfolio()
    
    if df is None:
        st.error("Could not find a header row containing 'Cumulative Change' in the Excel file.")
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
    num = float(num)
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

# --- Data Fetching Function ---
@st.cache_data(ttl=300)
def get_stock_data(ticker, period="1y"):
    # אם period=1w הורד חודש נתונים כדי לוודא שיש מספיק נקודות
    yf_period = '1mo' if period == '1w' else ('max' if period == 'all' else period)
    
    try:
        stock = yf.Ticker(ticker)
        # משיכת נתונים היסטוריים
        data = stock.history(period=yf_period)
        
        # משיכת נתונים פונדמנטליים
        info = stock.info
        
        if data.empty:
            return None, None, None
        
        # חתוך ל-7 הימים האחרונים אם period=1w
        if period == "1w":
            data = data[data.index >= (data.index[-1] - pd.Timedelta(days=7))]

        try:
            current_price = stock.fast_info["last_price"]
        except:
            current_price = data["Close"].iloc[-1]

        return data, current_price, info
    except Exception as e:
        return None, None, None
        
# --- Advanced Plotting Function ---
def plot_advanced_stock_graph(ticker, cost_price, stock_name):
    
    st.subheader(f"Detailed Analysis: {stock_name}")
    
    # Period Selection
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

    # Load Data 
    data, current_price, info = get_stock_data(ticker, period)
    
    if data is None or data.empty:
        st.error(f"No historical data found for {ticker}")
        return
        
    if current_price is None:
        st.warning("Could not retrieve current price, using last closing price.")
        current_price = data["Close"].iloc[-1]
        
    if info is None:
        st.warning("Could not retrieve fundamental information.")
        
    # Calculate Changes
    change_abs = current_price - cost_price
    change_pct = (change_abs / cost_price) * 100
    change_abs_rounded = round(change_abs, 3)
    
    # --- Price and Portfolio Metrics ---
    st.markdown("### Portfolio Performance")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Cost Price", f"${cost_price:.2f}")
    col2.metric("Current Price", f"${current_price:.2f}", delta=change_abs_rounded)
    col3.metric("Cumulative Change", f"{change_pct:.2f}%", delta=change_abs_rounded)
    
    # Data Period Metric
    time_delta = data.index[-1] - data.index[0]
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
    
    # --- Plotly Graph (Original Plotting Logic) ---
    st.markdown("### Price Chart")
    fig = go.Figure()
    color = '#34A853' if change_pct >= 0 else '#EA4335'
    
    # Closing Price
    fig.add_trace(go.Scatter(
        x=data.index,
        y=data["Close"],
        mode='lines',
        name='Closing Price',
        line=dict(color=color, width=2),
        fill='tozeroy',
        fillcolor=f'rgba({int(color[1:3],16)}, {int(color[3:5],16)}, {int(color[5:7],16)}, 0.15)',
        hovertemplate='<b>Date:</b> %{x}<br><b>Price:</b> $%{y:.2f}<extra></extra>'
    ))
    
    # Cost Price Line
    fig.add_trace(go.Scatter(
        x=[data.index[0], data.index[-1]],
        y=[cost_price, cost_price],
        mode='lines',
        name='Cost Price',
        line=dict(color='red', width=2, dash='dash'),
        hovertemplate='<b>Cost Price:</b> $%{y:.2f}<extra></extra>'
    ))
    
    # Current Price Marker
    fig.add_trace(go.Scatter(
        x=[data.index[-1]],
        y=[current_price],
        mode='markers',
        name='Current Price',
        marker=dict(size=12, color='orange', symbol='star'),
        hovertemplate='<b>Current Price:</b> $%{y:.2f}<extra></extra>'
    ))
    
    fig.update_layout(
        title={'text': f"{ticker} - Performance Tracking", 'x':0.5, 'xanchor':'center'},
        xaxis_title="Date",
        yaxis_title="Price ($)",
        template="plotly_white",
        height=600,
        hovermode='x unified',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---") # מפריד אחרי הגרף
    
    # --- Key Fundamental Data ---
    st.markdown("### Key Fundamental Data")
    if info is not None:
        market_cap = info.get('marketCap', None)
        pe_ratio = info.get('trailingPE', None)
        forward_pe = info.get('forwardPE', None)
        pb_ratio = info.get('priceToBook', None)
        dividend_yield = info.get('dividendYield', None)
        
        # מציגים את הנתונים העיקריים בשורה הראשונה
        f_col1, f_col2, f_col3, f_col4 = st.columns(4)
        
        f_col1.metric("**Market Cap**", format_large_number(market_cap))
        f_col2.metric("**P/E Ratio (TTM)**", f"{pe_ratio:.2f}" if pe_ratio else "N/A")
        f_col3.metric("**Forward P/E**", f"{forward_pe:.2f}" if forward_pe else "N/A")
        f_col4.metric("**P/B Ratio**", f"{pb_ratio:.2f}" if pb_ratio else "N/A")
        
        
        # נתונים נוספים בשורה שנייה
        f2_col1, f2_col2, f2_col3, f2_col4 = st.columns(4)
        
        f2_col1.metric("**52 Week High**", f"${info.get('fiftyTwoWeekHigh', 'N/A'):.2f}")
        f2_col2.metric("**52 Week Low**", f"${info.get('fiftyTwoWeekLow', 'N/A'):.2f}")
        f2_col3.metric("**Avg. Volume**", format_large_number(info.get('averageVolume10days', None)))
        f2_col4.metric("**Div. Yield**", f"{dividend_yield*100:.2f}%" if dividend_yield else "N/A")

        # הוספת תיאור החברה
        with st.expander("Company Description"):
            st.markdown(info.get('longBusinessSummary', 'No description available.'))
            
    else:
        st.info("Fundamental data is not available for this stock.")
        
    st.markdown("---")
    
    # Statistics
    st.markdown("### Price Statistics")
    col1, col2, col3, col4 = st.columns(4)
    col1.info(f"**Minimum Price:**\n${data['Close'].min():.2f}")
    col2.info(f"**Maximum Price:**\n${data['Close'].max():.2f}")
    col3.info(f"**Average Price:**\n${data['Close'].mean():.2f}")
    col4.info(f"**Volatility (SD):\n${data['Close'].std():.2f}")
    
    # Recent Data
    with st.expander("Recent Data (Last 10 Trading Days)"):
        recent_data = data[['Open','High','Low','Close','Volume']].tail(10).copy()
        recent_data = recent_data.round(2)
        st.dataframe(recent_data, use_container_width=True)


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
                # לאחר לחיצה, מעדכנים את ה-session_state
                st.session_state.selected_ticker = ticker
                st.session_state.selected_cost_price = cost_price
                st.session_state.selected_name = button_label
                
                # הגלילה האוטומטית בוטלה כאן

st.markdown("---")

# --- Display Selected Stock Analysis ---
if st.session_state.selected_ticker is not None:
    
    # 🌟 הפקודה החדשה לגלילה אוטומטית לנקודה זו:
    st.markdown('<a id="analysis_anchor"></a>', unsafe_allow_html=True)
    
    # st.subheader(f"Detailed Analysis: {stock_name}")  <-- הכותרת מוצגת בפונקציה
    
    # מציג את הניתוח
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
