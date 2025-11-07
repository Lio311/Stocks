# --- UPDATED FUNCTION ---
def check_portfolio_and_report():
    # --- $$$$ FIX 1: Initialize variables to prevent NameError $$$$ ---
    portfolio_details = []
    general_market_losers = []
    general_market_gainers = []
    total_portfolio_daily_p_l_ils = 0.0 # Initialize total P/L in ILS
    
    try:
        df = pd.read_excel(PORTFOLIO_FILE, header=HEADER_ROW)
    except FileNotFoundError:
        print(f"Error: Could not find file {PORTFOLIO_FILE}")
        return
    except Exception as e:
        print(f"Error reading Excel file: {e}")
        return

    df.columns = [str(c).strip() for c in df.columns]

    required_cols = [TICKER_COLUMN, BUY_PRICE_COLUMN, SHARES_COLUMN]
    for col in required_cols:
        if col not in df.columns:
            print(f"Error: Missing column '{col}'. Found columns: {list(df.columns)}")
            return

    # Fetch USD/ILS Exchange Rate
    print("Fetching USD/ILS exchange rate...")
    usd_ils_rate = 0.0
    try:
        ils_ticker = yf.Ticker("ILS=X")
        ils_data = ils_ticker.history(period="1d")
        if not ils_data.empty:
            usd_ils_rate = ils_data['Close'].iloc[-1]
            print(f"Current USD/ILS rate: {usd_ils_rate:.4f}")
        else:
            print("Warning: Could not fetch USD/ILS rate. Defaulting to 0. P/L will be incorrect.")
    except Exception as e:
        print(f"Error fetching USD/ILS rate: {e}. Defaulting to 0. P/L will be incorrect.")
    
    if usd_ils_rate == 0.0:
        # Fallback in case the rate fetch fails
        print("Using a fallback rate of 3.7. THIS IS A FALLBACK.")
        usd_ils_rate = 3.7 # Hardcoded fallback

    print("Reading portfolio from Excel...")
    
    # portfolio_map now holds a dictionary
    portfolio_map = {}
    for index, row in df.iterrows():
        ticker_symbol = str(row[TICKER_COLUMN]).strip()
        buy_price_raw = row[BUY_PRICE_COLUMN]
        shares_raw = row[SHARES_COLUMN]

        if not ticker_symbol or ticker_symbol.lower() == 'nan' or pd.isna(buy_price_raw) or pd.isna(shares_raw):
            continue
            
        buy_price = clean_price(buy_price_raw)
        num_shares = clean_quantity(shares_raw)
        
        if buy_price and num_shares > 0:
            portfolio_map[ticker_symbol] = {
                "buy_price": buy_price,
                "shares": num_shares
            }
    
    if not portfolio_map:
        print("No valid tickers with shares found in portfolio file.")
    
    tickers_list = list(portfolio_map.keys())
    
    # Portfolio Data Processing
    # (Variables portfolio_details and total_portfolio_daily_p_l_ils are already initialized above)
    
    if tickers_list:
        print(f"Fetching data for {len(tickers_list)} tickers: {', '.join(tickers_list)}")
        try:
            # --- $$$$ FIX 2: Changed period back to "5d" for robustness $$$$ ---
            all_data = yf.download(tickers_list, period="5d", progress=False, auto_adjust=False)
            
            if all_data.empty or len(all_data) < 2:
                print("Could not download sufficient portfolio data from yfinance.")
            else:
                close_prices = all_data['Close']
                latest_prices = close_prices.iloc[-1]
                prev_prices = close_prices.iloc[-2] # Get second to last row for previous close

                for ticker, data in portfolio_map.items():
                    try:
                        buy_price = data['buy_price']
                        num_shares = data['shares']
                        
                        if len(tickers_list) == 1:
                            # Handle case of single ticker download
                            current_price = latest_prices
                            prev_close = prev_prices
                        else:
                            current_price = latest_prices.get(ticker)
                            prev_close = prev_prices.get(ticker)

                        if current_price is None or prev_close is None or pd.isna(current_price) or pd.isna(prev_close):
                            print(f"Skipping {ticker}: Missing current or previous price data.")
                            continue

                        # P/L Calculations (USD)
                        daily_change_per_share = current_price - prev_close
                        total_change_per_share = current_price - buy_price
                        
                        daily_p_l_usd = daily_change_per_share * num_shares
                        total_p_l_usd = total_change_per_share * num_shares
                        
                        # Convert P/L to ILS
                        daily_p_l_ils = daily_p_l_usd * usd_ils_rate
                        total_p_l_ils = total_p_l_usd * usd_ils_rate
                        
                        total_portfolio_daily_p_l_ils += daily_p_l_ils # Add to total
                        
                        # Standard % Calculations
                        total_change_pct = (total_change_per_share / buy_price) * 100 if buy_price != 0 else 0
                        daily_change_pct = (daily_change_per_share / prev_close) * 100 if prev_close != 0 else 0


                        details = {
                            "ticker": ticker,
                            "buy_price": buy_price,
                            "current_price": current_price,
                            "prev_close": prev_close,
                            "daily_change_pct": daily_change_pct,
                            "total_change_pct": total_change_pct,
                            "num_shares": num_shares,
                            "daily_p_l": daily_p_l_ils,  # Storing ILS value
                            "total_p_l": total_p_l_ils   # Storing ILS value
                        }
                        portfolio_details.append(details)
                        
                        # Print statement now shows ILS
                        print(f"{ticker} ({num_shares} shares): Buy=${buy_price:.2f}, Current=${current_price:.2f}, "
                              f"Daily P/L=₪{daily_p_l_ils:+.2f} ({daily_change_pct:+.1f}%), "
                              f"Total P/L=₪{total_p_l_ils:+.2f} ({total_change_pct:+.1f}%)")

                    except KeyError:
                         print(f"Warning: No data found for ticker '{ticker}' in downloaded batch. It might be delisted or invalid.")
                    except Exception as e:
                        print(f"Error processing {ticker}: {e}")
                        traceback.print_exc()

        except Exception as e:
            print(f"Error downloading batch data from yfinance: {e}")
            traceback.print_exc()
    else:
        print("No tickers in portfolio file. Skipping portfolio processing.")

    # Get General Market Movers (both losers and gainers)
    # This will now assign to the variables initialized at the top
    general_market_losers, general_market_gainers = get_general_market_movers()

    # Get Gemini AI Analysis
    # The variables are guaranteed to be defined (at least as [])
    gemini_analysis_html = get_gemini_analysis(portfolio_details, general_market_losers, general_market_gainers, total_portfolio_daily_p_l_ils)
    
    # --- $$$$ NEW: Get Gemini AI Insights $$$$ ---
    gemini_insights_html = get_gemini_insights(portfolio_details, general_market_losers, general_market_gainers, total_portfolio_daily_p_l_ils)

    if not portfolio_details and not general_market_losers and not general_market_gainers:
        print("No portfolio details or general market movers to report.")
        return

    # Report Generation and Sending
    print("\nGenerating HTML report...")
    # --- $$$$ UPDATED CALL $$$$ ---
    html_report = generate_html_report(
        portfolio_details, 
        general_market_losers, 
        general_market_gainers, 
        gemini_analysis_html, 
        gemini_insights_html,  # <-- Pass new insights
        total_portfolio_daily_p_l_ils
    )
    
    report_filename = "daily_stock_report.html"
    try:
        with open(report_filename, "w", encoding="utf-8") as f:
            f.write(html_report)
        print(f"✅ Report generated successfully: {report_filename}")
    except Exception as e:
        print(f"Error saving HTML file: {e}")

    # Send Email
    if SENDER_EMAIL and RECIPIENT_EMAIL:
        print("Sending email...")
        send_email(html_report)
    else:
        print("\nEmail credentials not set. Skipping email send.")
        print("View your report at: daily_stock_report.html")
