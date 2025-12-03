import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime, timedelta

# --- 1. Page Configuration ---
st.set_page_config(
    page_title="My Stock Portfolio",
    layout="wide",
    page_icon ="📈"
)

st.title("My Stock Portfolio")
st.markdown("---")

# Define the path to the Excel file
file_path = "תיק מניות.xlsx"

# --- 2. Data Loading and Cleaning ---
@st.cache_data
def load_portfolio():
    """
    Loads and cleans the portfolio data from the Excel file.
    Finds the header dynamically by searching for a keyword.
    """
    try:
        # Read the raw Excel file without a specific header
        df_raw = pd.read_excel(file_path, header=None)
    except FileNotFoundError:
        st.error(f"Error: The file '{file_path}' was not found. Please ensure the Excel file is in the correct directory.")
        return None
        
    # Find the actual header row by searching for a specific keyword ('שינוי מצטבר')
    header_row_idx = None
    for i, row in df_raw.iterrows():
        if row.astype(str).str.strip().str.contains("שינוי מצטבר", regex=False).any():
            header_row_idx = i
            break
            
    if header_row_idx is None:
        return None

    # Re-read the Excel file using the correct header row
    df = pd.read_excel(file_path, header=header_row_idx)
    # Clean column names (strip whitespace)
    df.columns = [str(col).strip() for col in df.columns]
    
    # Ensure all necessary columns are present in the file
    required_cols = ["טיקר", "מחיר עלות", "כמות מניות"]
    if not all(col in df.columns for col in required_cols):
        st.error(f"Error: The Excel file must contain the columns: {', '.join(required_cols)}")
        return None
        
    # Filter out rows that are missing essential data
    df = df.dropna(subset=required_cols)
    
    # Clean and convert 'Cost Price' to a numeric type
    df["מחיר עלות"] = df["מחיר עלות"].astype(str).str.replace(r'[^\d\.\-]', '', regex=True)
    df["מחיר עלות"] = pd.to_numeric(df["מחיר עלות"], errors='coerce')
    
    # Clean and convert 'Stock Quantity' to a numeric type
    df["כמות מניות"] = df["כמות מניות"].astype(str).str.replace(r'[^\d\.]', '', regex=True)
    df["כמות מניות"] = pd.to_numeric(df["כמות מניות"], errors='coerce')

    df = df.dropna(subset=required_cols)
    return df

# --- 3. Ticker Conversion ---
def convert_ticker(t):
    """Converts ticker formats from the Excel file to yfinance-compatible tickers."""
    t_str = str(t).strip()

    # Map specific numeric IDs (from Excel) to yfinance-compatible tickers
    if t_str == "1183441":
        return "1183441"
    elif t_str == "1159250":
        return "1159250" 
    
    # Handle other known formats (e.g., XNAS:, XLON:)
    elif t_str.startswith("XNAS:"):
        return t_str.split(":")[1]
    elif t_str.startswith("XLON:"):
        return t_str.split(":")[1] + ".L"
    else:
        return t_str

# --- 4. Load Portfolio Data ---
with st.spinner("Loading portfolio stocks..."):
    df = load_portfolio()
    
    if df is None:
        st.error("Could not find a header row containing 'שינוי מצטבר' (Cumulative Change) in the Excel file, or the file is missing/invalid.")
        st.stop()
        
    df["yfinance_ticker"] = df["טיקר"].apply(convert_ticker)
    st.success(f"Loaded {len(df)} stocks from the portfolio.")

# --- 5. Session State Initialization ---
# Initialize session state variables to store the selected stock's details
if "selected_ticker" not in st.session_state:
    st.session_state.selected_ticker = None
if "selected_cost_price" not in st.session_state:
    st.session_state.selected_cost_price = None
if "selected_name" not in st.session_state:
    st.session_state.selected_name = None
if "selected_quantity" not in st.session_state:
    st.session_state.selected_quantity = None 
if "current_period" not in st.session_state:
    st.session_state.current_period = '1y' # Set default chart period

# --- 6. Helper Functions ---
def format_large_number(num):
    """Converts large numbers to a readable format (e.g., 1.5T, 500B, 1.2M)."""
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
        return f'{num:,.2f}'

@st.cache_data(ttl=3600) 
def get_forex_rate(currency_pair="ILS=X"):
    """Fetches the current USD to ILS exchange rate."""
    try:
        forex = yf.Ticker(currency_pair)
        rate = forex.history(period="1d")["Close"].iloc[-1]
        
        # Ensure the rate is USD -> ILS (which should be > 1)
        if rate < 1:
            rate = 1 / rate
            
        return rate
    except Exception:
        return 3.7 # Fallback rate in case of API failure

@st.cache_data(ttl=300)
def get_stock_data(ticker, period="1y"):
    """Fetches historical data, info, and recommendations from yfinance."""
    
    # Manually map local tickers to their yfinance equivalents
    if ticker == "1183441":
        yf_ticker = "SPXS.L" # Invesco S&P 500 UCITS ETF
    elif ticker == "1159250":
        yf_ticker = "CSPX.L" # iShares Core S&P 500 UCITS ETF
    else:
        yf_ticker = ticker
        
    # Adjust period syntax for yfinance (e.g., '1w' -> '1mo')
    yf_period = '1mo' if period == '1w' else ('max' if period == 'all' else period)
    
    try:
        stock = yf.Ticker(yf_ticker)
        # Fetch historical data, info, and recommendations
        data = stock.history(period=yf_period)
        info = stock.info
        recommendations = stock.get_recommendations_summary() 
        quarterly_earnings = stock.quarterly_earnings
        
        if data.empty:
            return None, None, None, None, None
            
        # yfinance '1w' fix: fetch '1mo' and manually slice the last 7 days
        if period == "1w":
            data = data[data.index >= (data.index[-1] - pd.Timedelta(days=7))]

        # Try to get the fast_info price, fall back to the last close price
        try:
            current_price = stock.fast_info.get("last_price", data["Close"].iloc[-1])
        except:
            current_price = data["Close"].iloc[-1]

        return data, current_price, info, recommendations, quarterly_earnings
    except Exception as e:
        return None, None, None, None, None
        
# --- 7. Main Analysis and Plotting Function ---
def plot_advanced_stock_graph(ticker, cost_price_ils, stock_quantity, stock_name):
    
    st.subheader(f"Detailed Analysis: {stock_name}")
    
    # Define tickers whose cost price is originally in ILS (need conversion)
    ILS_COST_TICKERS = ["1159250", "1183441"]
    
    # Get the current selected period from session state
    current_period = st.session_state.current_period
    # Load stock data based on the selected period
    data_raw, current_price_raw, info, recommendations, quarterly_earnings = get_stock_data(ticker, current_period) 

    # Check for data validity
    if data_raw is None or data_raw.empty:
        st.error(f"No historical data found for {ticker}")
        return
        
    if current_price_raw is None:
        st.warning("Could not retrieve current price, using last closing price.")
        current_price_raw = data_raw["Close"].iloc[-1]

    
    # --- Price Conversion Logic ---
    
    if ticker in ILS_COST_TICKERS:
        # Case 1: Cost is in ILS (e.g., TASE stock)
        USD_TO_ILS_RATE = get_forex_rate("ILS=X")
        st.caption(f"Status: Cost Price in ILS | Exchange Rate (USD → ILS): $1 = ₪{USD_TO_ILS_RATE:.4f}")
        # Convert ILS cost to USD for comparison
        cost_price_usd = cost_price_ils / USD_TO_ILS_RATE
        current_price_usd = current_price_raw 
        
    else:
        # Case 2: Cost is already in USD (foreign stock)
        cost_price_usd = cost_price_ils # The raw 'cost price' is already USD
        current_price_usd = current_price_raw
    
    # --- Performance Calculations (USD) ---
    
    # 1. Per-Share Calculations
    change_abs_per_share = current_price_usd - cost_price_usd
    change_pct_per_share = (change_abs_per_share / cost_price_usd) * 100 if cost_price_usd != 0 else 0
    change_abs_per_share_rounded = round(change_abs_per_share, 2)
    
    # 2. Total Position Calculations
    total_cost_usd = cost_price_usd * stock_quantity
    total_current_value_usd = current_price_usd * stock_quantity
    total_profit_loss_usd = change_abs_per_share * stock_quantity
    total_profit_loss_pct = (total_profit_loss_usd / total_cost_usd) * 100 if total_cost_usd != 0 else 0

    
    # --- Display Performance Metrics ---
    
    st.markdown("### Portfolio Performance (USD $)")
    
    # --- 1. Calculate Data Period First (To avoid NameError) ---
    time_delta = data_raw.index[-1] - data_raw.index[0]
    if time_delta.days > 365:
        display_period = f"{time_delta.days // 365}Y"
    elif time_delta.days > 30:
        display_period = f"{time_delta.days // 30}M"
    elif time_delta.days >= 7:
        display_period = f"{time_delta.days // 7}W"
    else:
        display_period = f"{time_delta.days}D"

    # --- 2. Row 1: Per-Share Metrics ---
    col1, col2, col3, col4 = st.columns(4)
    
    # Column 1: Cost Price
    col1.metric("Cost Price (Per Share)", f"${cost_price_usd:,.2f}") 

    # Column 2: Current Price + FIX for Red Arrow
    # Check if the change is negative
    if change_abs_per_share < 0:
        # If negative: Put minus BEFORE dollar (e.g., -$1.50) -> Red Arrow
        delta_str = f"-${abs(change_abs_per_share):,.2f}"
    else:
        # If positive: Dollar then number (e.g., $1.50) -> Green Arrow
        delta_str = f"${change_abs_per_share:,.2f}"

    col2.metric("Current Price (Per Share)", f"${current_price_usd:,.2f}", delta=delta_str)

    # Column 3: Change Percentage
    if change_pct_per_share >= 0:
        delta_label_pct = f"+{change_pct_per_share:.2f}%"
    else:
        delta_label_pct = f"{change_pct_per_share:.2f}%"
        
    col3.metric("Change (%)", delta_label_pct, delta_color="normal")

    # Column 4: Data Period
    col4.metric("Data Period", display_period)

    # Row 2: Total Position Metrics (using custom HTML for styling)
    st.markdown("##### Total Position Value")
    col5, col6, col7, col8 = st.columns(4)

    # ---!!! START DARK MODE CHANGES !!!---

    # Define consistent CSS styles for custom metrics
    label_font_size = "0.875rem" 
    value_font_size = "1.75rem" 
    # Use Streamlit's theme variable for text color (black/white)
    label_style = f"font-size: {label_font_size}; color: var(--text-color); opacity: 0.6; line-height: 1.5;"
    value_style_default = f"font-size: {value_font_size}; color: var(--text-color); line-height: 1.5; font-weight: 600;"
    
    # Metric 1: Total Cost (default color)
    col5.markdown(f"""
    <div style="padding-top: 0.5rem; padding-bottom: 0.5rem;">
        <span style="{label_style}">Total Cost (USD)</span>
        <div style="{value_style_default}">
            ${total_cost_usd:,.2f}
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Metric 2: Total Current Value (default color)
    col6.markdown(f"""
    <div style="padding-top: 0.5rem; padding-bottom: 0.5rem;">
        <span style="{label_style}">Total Current Value (USD)</span>
        <div style="{value_style_default}">
            ${total_current_value_usd:,.2f}
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Metric 3: Total P/L (USD) (colored)
    # Use Streamlit's theme variables for green/red
    p_l_color = "var(--green-70)" if total_profit_loss_usd >= 0 else "var(--red-70)"
    p_l_sign = "+" if total_profit_loss_usd >= 0 else ""
    value_style_pl_usd = f"font-size: {value_font_size}; color: {p_l_color}; line-height: 1.5; font-weight: 600;"
    
    col7.markdown(f"""
    <div style="padding-top: 0.5rem; padding-bottom: 0.5rem;">
        <span style="{label_style}">Total P/L (USD)</span>
        <div style="{value_style_pl_usd}">
            {p_l_sign}${total_profit_loss_usd:,.2f}
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Metric 4: Total P/L (%) (colored)
    pct_color = "var(--green-70)" if total_profit_loss_pct >= 0 else "var(--red-70)"
    pct_sign = "+" if total_profit_loss_pct >= 0 else ""
    value_style_pl_pct = f"font-size: {value_font_size}; color: {pct_color}; line-height: 1.5; font-weight: 600;"

    col8.markdown(f"""
    <div style="padding-top: 0.5rem; padding-bottom: 0.5rem;">
        <span style="{label_style}">Total P/L (%)</span>
        <div style="{value_style_pl_pct}">
            {pct_sign}{total_profit_loss_pct:,.2f}%
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # ---!!! END DARK MODE CHANGES !!!---

    st.markdown("---")
    
    # --- Plotly Graph (USD) ---
    st.markdown("### Price Chart (Per Share, USD $)")
    
    # --- Period Selection Dropdown ---
    period_options = ["1w", "1mo", "3mo", "6mo", "1y", "2y", "5y", "all"]
    period_labels = {
        "1w": "1 Week", "1mo": "1 Month", "3mo": "3 Months", "6mo": "6 Months",
        "1y": "1 Year", "2y": "2 Years", "5y": "5 Years", "all": "All"
    }
    
    try:
        current_period_index = period_options.index(st.session_state.current_period)
    except ValueError:
        current_period_index = 4 # Default to 1y
        
    col1_select, col2_select = st.columns([1, 4])
    with col1_select:
        selected_period = st.selectbox(
            "Display Period:",
            options=period_options,
            index=current_period_index,
            key="period_selectbox", 
            format_func=lambda x: period_labels[x]
        )

    if st.session_state.current_period != selected_period:
        st.session_state.current_period = selected_period
        st.rerun() 

    
    # Create the Plotly figure
    fig = go.Figure()
    # These colors are fine for both modes
    color = '#34A853' if total_profit_loss_pct >= 0 else '#EA4335'
    
    # Closing Price (Uses data in USD)
    fig.add_trace(go.Scatter(
        x=data_raw.index, 
        y=data_raw["Close"],
        mode='lines',
        name='Closing Price (USD)',
        line=dict(color=color, width=2),
        fill='tozeroy',
        fillcolor=f'rgba({int(color[1:3],16)}, {int(color[3:5],16)}, {int(color[5:7],16)}, 0.15)',
        hoverinfo='x+y'
    ))
    
    # Cost Price Line (Converted to USD)
    fig.add_trace(go.Scatter(
        x=[data_raw.index[0], data_raw.index[-1]],
        y=[cost_price_usd, cost_price_usd], 
        mode='lines',
        name='Cost Price (USD)',
        line=dict(color='red', width=2, dash='dash'),
        hoverinfo='y'
    ))
    
    # Current Price Marker (in USD)
    fig.add_trace(go.Scatter(
        x=[data_raw.index[-1]],
        y=[current_price_usd],
        mode='markers',
        name='Current Price (USD)',
        marker=dict(size=12, color='orange', symbol='star'),
        hoverinfo='y'
    ))
    
    # Finalize graph layout
    fig.update_layout(
        title={'text': f"{ticker} - Performance Tracking", 'x':0.5, 'xanchor':'center'},
        xaxis_title="Date",
        yaxis_title="Price (USD $)",
        # ---!!! DARK MODE CHANGE !!!---
        template="streamlit", # This template syncs with Streamlit's theme
        height=600,
        hovermode='x unified',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    # Display the graph
    st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---") 
    
    # --- Price Statistics (in USD) ---
    st.markdown("### Price Statistics (USD $)")
    col1, col2, col3, col4 = st.columns(4)
    col1.info(f"**Minimum Price:**\n${data_raw['Close'].min():,.2f}")
    col2.info(f"**Maximum Price:**\n${data_raw['Close'].max():,.2f}")
    col3.info(f"**Average Price:**\n${data_raw['Close'].mean():,.2f}")
    col4.info(f"**Volatility (SD):**\n${data_raw['Close'].std():,.2f}")
    
    # Recent Data
    with st.expander("Recent Data (Last 10 Trading Days) - USD"):
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
        
        f2_col1.metric("**52 Week High**", f"${high_52w:,.2f}" if high_52w is not None and pd.notna(high_52w) else "N/A")
        f2_col2.metric("**52 Week Low**", f"${low_52w:,.2f}" if low_52w is not None and pd.notna(low_52w) else "N/A")
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
    
# --- 8. Stock Selection Interface ---
st.subheader("Select a Stock for Analysis")
cols_per_row = 6
# Dynamically create a grid of buttons for stock selection
for i in range(0, len(df), cols_per_row):
    cols = st.columns(cols_per_row)
    for j in range(min(cols_per_row, len(df) - i)):
        row = df.iloc[i+j]
        ticker = row["yfinance_ticker"]
        cost_price = row["מחיר עלות"]
        stock_quantity = row["כמות מניות"]
        button_label = str(row["טיקר"]).strip()
        
        if button_label == "" or button_label.lower() == "nan":
            continue
            
        with cols[j]:
            # When a button is clicked, store its data in session state
            if st.button(button_label, key=f"btn_{ticker}_{i}_{j}", use_container_width=True):
                st.session_state.selected_ticker = ticker
                st.session_state.selected_cost_price = cost_price
                st.session_state.selected_name = button_label
                st.session_state.selected_quantity = stock_quantity
                # Reset the period to default when a new stock is selected
                st.session_state.current_period = '1y' 
                st.rerun() 

st.markdown("---")

# --- 9. Main App Logic ---
# If a stock is selected, call the main plotting function
if st.session_state.selected_ticker is not None:
    
    plot_advanced_stock_graph(
        st.session_state.selected_ticker,
        st.session_state.selected_cost_price,
        st.session_state.selected_quantity, 
        st.session_state.selected_name
    )
    
    # Add a button to return to the main list
    if st.button("Back to Stock List", key="back_button"):
        # Clear session state to hide the analysis view
        st.session_state.selected_ticker = None
        st.session_state.selected_cost_price = None
        st.session_state.selected_name = None
        st.session_state.selected_quantity = None
        st.session_state.current_period = '1y'
        st.rerun()
else:
    # If no stock is selected, show a prompt
    st.info("Select a stock from the list above to see a detailed analysis.")

# --- 10. Footer ---
st.markdown("---")
st.caption(f"Data updated from Yahoo Finance | Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
