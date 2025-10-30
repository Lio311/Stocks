def plot_advanced_stock_graph(ticker, cost_price, stock_name):
    st.subheader(f"Detailed Analysis: {stock_name}")
    
    # --- Period Selection ---
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
    
    # --- Load Data ---
    data, current_price = get_stock_data(ticker, period)
    
    if data is None or data.empty:
        st.error(f"No data found for {ticker}")
        return
        
    if current_price is None:
        st.warning("Could not retrieve current price, using last closing price.")
        current_price = data["Close"].iloc[-1]
        
    # --- Calculate Changes ---
    change_abs = current_price - cost_price
    change_pct = (change_abs / cost_price) * 100
    change_abs_rounded = round(change_abs, 3)  # ערך מעוגל להצגה
    
    # --- Metrics Display ---
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
    
    # --- Create Plotly Graph ---
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
        fillcolor=f'rgba({int(color[1:3], 16)}, {int(color[3:5], 16)}, {int(color[5:7], 16)}, 0.15)',
        hovertemplate='<b>Date:</b> %{x}<br><b>Price:</b> $%{y:.2f}<extra></extra>'
    ))
    
    # Cost Price
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
    
    # Layout
    fig.update_layout(
        title={'text': f"{ticker} - Performance Tracking", 'x': 0.5, 'xanchor': 'center'},
        xaxis_title="Date",
        yaxis_title="Price ($)",
        template="plotly_white",
        height=600,
        hovermode='x unified',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # --- Statistics ---
    st.markdown("### Statistics")
    col1, col2, col3, col4 = st.columns(4)
    col1.info(f"**Minimum Price:**\n${data['Close'].min():.2f}")
    col2.info(f"**Maximum Price:**\n${data['Close'].max():.2f}")
    col3.info(f"**Average Price:**\n${data['Close'].mean():.2f}")
    col4.info(f"**Volatility (SD):**\n${data['Close'].std():.2f}")
    
    # --- Recent Data Table ---
    with st.expander("Recent Data (Last 10 Trading Days)"):
        recent_data = data[['Open', 'High', 'Low', 'Close', 'Volume']].tail(10).copy()
        recent_data = recent_data.round(2)
        st.dataframe(recent_data, use_container_width=True)
