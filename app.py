import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime, timedelta

# --- App Configuration ---
st.set_page_config(
    page_title="My Stock Portfolio",
    page_icon="💼",
    layout="wide")

st.title("My Stock Portfolio")
st.markdown("---")

file_path = "תיק מניות.xlsx" # The file name remains the same as it's an external file reference

# --- Data Loading and Cleaning ---
@st.cache_data
def load_portfolio():
    # Read all rows without a header initially
    df_raw = pd.read_excel(file_path, header=None)
    
    # Search for the header row containing "שינוי מצטבר" (Cumulative Change)
    header_row_idx = None
    for i, row in df_raw.iterrows():
        if row.astype(str).str.strip().str.contains("שינוי מצטבר", regex=False).any():
            header_row_idx = i
            break
            
    if header_row_idx is None:
        return None
        
    df = pd.read_excel(file_path, header=header_row_idx)
    
    # Standardize column names (using original Hebrew names for DataFrame access)
    df.columns = [str(col).strip() for col in df.columns]
    
    # Drop rows where 'Ticker' or 'Cost Price' is missing
    df = df.dropna(subset=["טיקר", "מחיר עלות"]) # 'Ticker', 'Cost Price'
    
    # Clean up Cost Price (removing non-numeric characters except '.' and '-')
    df["מחיר עלות"] = df["מחיר עלות"].astype(str).str.replace(r'[^\d\.-]', '', regex=True)
    df["מחיר עלות"] = pd.to_numeric(df["מחיר עלות"], errors='coerce')
    df = df.dropna(subset=["מחיר עלות"])
    
    return df

# --- Ticker Conversion for yfinance ---
def convert_ticker(t):
    t = str(t).strip()
    if t.startswith("XNAS:"):
        return t.split(":")[1]  # NASDAQ
    elif t.startswith("XLON:"):
        return t.split(":")[1] + ".L"  # LSE
    else:
        return t

# --- Portfolio Load Execution ---
with st.spinner("Loading portfolio stocks..."):
    df = load_portfolio()
    
    if df is None:
        st.error("Could not find a header row containing 'Cumulative Change' in the Excel file.")
        st.stop()
        
    # Map 'Ticker' to a yfinance-compatible ticker
    df["yfinance_ticker"] = df["טיקר"].apply(convert_ticker) # 'Ticker' column
    st.success(f" Loaded {len(df)} stocks from the portfolio.")

# --- Session State Initialization ---
if "selected_ticker" not in st.session_state:
    st.session_state.selected_ticker = None
    st.session_state.selected_cost_price = None
    st.session_state.selected_name = None

# --- Data Fetching Function ---
@st.cache_data(ttl=300) # Cache data for 5 minutes
def get_stock_data(ticker, period="1y"):
    # If the requested period is 'all', yfinance uses 'max'
    yf_period = 'max' if period == 'all' else period
    try:
        stock = yf.Ticker(ticker)
        data = stock.history(period=yf_period)
        
        # Current Price
        try:
            current_price = stock.fast_info["last_price"]
        except:
            current_price = data["Close"].iloc[-1] if not data.empty else None
            
        return data, current_price
    except Exception as e:
        return None, None

# --- Advanced Plotting Function ---
def plot_advanced_stock_graph(ticker, cost_price, stock_name):
    st.subheader(f" Detailed Analysis: {stock_name}")
    
    # Period Selection
    col1, col2 = st.columns([1, 4])
    with col1:
        # **UPDATED: Added 'all' option**
        period = st.selectbox(
            "Display Period:",
            ["1mo", "3mo", "6mo", "1y", "2y", "5y", "all"],
            index=3,
            # English display mapping
            format_func=lambda x: {
                "1mo": "1 Month",
                "3mo": "3 Months",
                "6mo": "6 Months",
                "1y": "1 Year",
                "2y": "2 Years",
                "5y": "5 Years",
                "all": "All" # New option label
            }[x]
        )
        
    # Load Data
    data, current_price = get_stock_data(ticker, period)
    
    if data is None or data.empty:
        st.error(f" No data found for {ticker}")
        return
        
    if current_price is None:
        st.warning("Could not retrieve current price, using last closing price.")
        current_price = data["Close"].iloc[-1]
        
    # Calculate Changes
    change_abs = current_price - cost_price
    change_pct = (change_abs / cost_price) * 100
    
    # Metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Cost Price", f"${cost_price:.2f}")
    with col2:
        st.metric(
            "Current Price", 
            f"${current_price:.2f}",
            f"${change_abs:.2f}"
        )
    with col3:
        st.metric(
            "Cumulative Change",
            f"{change_pct:.2f}%",
            f"${change_abs:.2f}"
        )
    with col4:
        # Display the actual range of data
        time_delta = data.index[-1] - data.index[0]
        if time_delta.days > 365:
            display_period = f"{time_delta.days // 365} Years"
        else:
            display_period = f"{time_delta.days} Days"
        st.metric("Period Length", display_period)
        
    st.markdown("---")
    
    # Create the Plotly Graph
    fig = go.Figure()
    
    # Price Line
    color = '#34A853' if change_pct >= 0 else '#EA4335'
    fig.add_trace(go.Scatter(
        x=data.index,
        y=data["Close"],
        mode='lines',
        name='Closing Price',
        line=dict(color=color, width=2),
        fill='tozeroy',
        fillcolor=f'rgba({int(color[1:3], 16)}, {int(color[3:5], 16)}, {int(color[5:7], 16)}, 0.15)',
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
    
    # Update Layout
    fig.update_layout(
        title=f"{ticker} - Performance Tracking",
        xaxis_title="Date",
        yaxis_title="Price ($)",
        template="plotly_white",
        height=600,
        hovermode='x unified',
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Additional Statistics
    st.markdown("###  Statistics")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.info(f"**Minimum Price:**\n${data['Close'].min():.2f}")
    with col2:
        st.info(f"**Maximum Price:**\n${data['Close'].max():.2f}")
    with col3:
        avg_price = data['Close'].mean()
        st.info(f"**Average Price:**\n${avg_price:.2f}")
    with col4:
        volatility = data['Close'].std()
        st.info(f"**Volatility (SD):**\n${volatility:.2f}")
        
    # Recent Data
    with st.expander("📋 Recent Data (Last 10 Trading Days)"):
        recent_data = data[['Open', 'High', 'Low', 'Close', 'Volume']].tail(10).copy()
        # English column names for display
        recent_data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
        recent_data = recent_data.round(2)
        st.dataframe(recent_data, use_container_width=True)

# --- Stock Selection Buttons ---
st.subheader(" Select a Stock for Analysis")
cols_per_row = 6

# Loop to create buttons
for i in range(0, len(df), cols_per_row):
    cols = st.columns(cols_per_row)
    for j in range(min(cols_per_row, len(df) - i)):
        if i + j >= len(df):
            break
            
        row = df.iloc[i + j]
        ticker = row["yfinance_ticker"]
        cost_price = row["מחיר עלות"] # Use the internal Cost Price column
        
        # Prepare the clean button label (The Ticker itself)
        button_label = str(row["טיקר"]).strip() # Use the original Ticker
        if button_label == "" or button_label.lower() == "nan":
            continue
            
        with cols[j]:
            if st.button(button_label, key=f"btn_{ticker}_{i}_{j}", use_container_width=True):
                st.session_state.selected_ticker = ticker
                st.session_state.selected_cost_price = cost_price
                st.session_state.selected_name = button_label
                
st.markdown("---")

# --- Display Selected Stock Analysis ---
if st.session_state.selected_ticker is not None:
    plot_advanced_stock_graph(
        st.session_state.selected_ticker,
        st.session_state.selected_cost_price,
        st.session_state.selected_name
    )
    
    # Button to clear selection
    if st.button(" Back to Stock List", key="back_button"):
        st.session_state.selected_ticker = None
        st.session_state.selected_cost_price = None
        st.session_state.selected_name = None
        st.rerun()
else:
    st.info(" Select a stock from the list above to see a detailed analysis.")

# --- Footer ---
st.markdown("---")
st.caption(f" Data updated from Yahoo Finance | Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
