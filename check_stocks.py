import pandas as pd
import yfinance as yf
import smtplib
import os
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import re
from datetime import datetime
import traceback # For debugging

# --- NEW IMPORT ---
# This library helps us scan the market for losers
# Make sure to install it: pip install yahoo_fin
try:
    from yahoo_fin import stock_info as si
except ImportError:
    print("Error: 'yahoo_fin' library not found.")
    print("Please install it by running: pip install yahoo_fin")
    exit()
# -----------------

# --- Configuration ---
PORTFOLIO_FILE = 'תיק מניות.xlsx'
TICKER_COLUMN = 'טיקר'
BUY_PRICE_COLUMN = 'מחיר עלות'
HEADER_ROW = 8 # The row where data starts (headers are row 9)
# ----------------------

# --- Email Configuration (Reads from Environment Variables) ---
SENDER_EMAIL = os.environ.get('GMAIL_USER')
SENDER_PASSWORD = os.environ.get('GMAIL_PASSWORD')
RECIPIENT_EMAIL = os.environ.get('RECIPIENT_EMAIL')
# ----------------------

def clean_price(price_str):
    """ Cleans a price string, removing currency symbols or other non-numeric characters. """
    if isinstance(price_str, (int, float)):
        return float(price_str)
    if not isinstance(price_str, str):
        price_str = str(price_str)
    
    cleaned_str = re.sub(r"[^0-9.-]", "", price_str)
    
    try:
        return float(cleaned_str) if cleaned_str else None
    except ValueError:
        print(f"Warning: Could not convert price string '{price_str}' to float.")
        return None

def convert_market_cap_to_float(cap_str):
    """ NEW: Converts market cap strings (e.g., '1.5T', '250B', '100M') to float. """
    if not isinstance(cap_str, str) or cap_str == 'N/A':
        return 0.0
    
    cap_str = cap_str.upper()
    multiplier = 1.0
    
    if 'T' in cap_str:
        multiplier = 1_000_000_000_000
    elif 'B' in cap_str:
        multiplier = 1_000_000_000
    elif 'M' in cap_str:
        multiplier = 1_000_000
    
    # Remove the letter and any other non-numeric chars (except dot)
    num_str = re.sub(r"[^0-9.]", "", cap_str)
    try:
        return float(num_str) * multiplier
    except ValueError:
        return 0.0

def get_general_market_losers():
    """ NEW: Scans Yahoo Finance for top losers and filters them. """
    print("\nScanning general market for big losers...")
    try:
        # Get the day's top losers from Yahoo's screener
        losers_df = si.get_day_losers()
        
        if losers_df.empty:
            print("Could not fetch general market losers.")
            return []

        # Clean and filter data
        # 1. Convert Market Cap string to a float number
        losers_df['Market Cap Float'] = losers_df['Market Cap'].apply(convert_market_cap_to_float)
        
        # 2. Ensure '% Change' is a float
        losers_df['% Change'] = pd.to_numeric(losers_df['% Change'], errors='coerce')

        # 3. Apply the filters
        min_market_cap = 100_000_000  # 100M USD
        # UPDATED: Relaxed filter from -20% to -5%
        min_drop_pct = -5.0          # -5%
        
        filtered_losers = losers_df[
            (losers_df['Market Cap Float'] > min_market_cap) &
            (losers_df['% Change'] <= min_drop_pct)
        ]
        
        # Sort by most dropped and take the top 15
        filtered_losers = filtered_losers.sort_values(by='% Change', ascending=True).head(15)
        
        print(f"Found {len(filtered_losers)} general market losers matching criteria (Cap > 100M, Drop > 5%).")
        return filtered_losers.to_dict('records') # Convert DataFrame to list of dicts
        
    except Exception as e:
        print(f"Error in get_general_market_losers: {e}")
        traceback.print_exc()
        return []

def generate_html_report(portfolio_details, general_market_losers):
    """ Generates a complete HTML report string. """
    today = datetime.now().strftime("%B %d, %Y")
    
    html = f"""
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: Arial, sans-serif; background-color: #f7f7f7; padding: 20px; direction: ltr; }}
            h1 {{ color: #333; border-bottom: 2px solid #4CAF50; }}
            h2 {{ color: #444; margin-top: 30px; }}
            table {{ border-collapse: collapse; width: 100%; margin-top: 15px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}
            th, td {{ border: 1px solid #ddd; padding: 10px; text-align: left; }}
            th {{ background-color: #4CAF50; color: white; }}
            tr:nth-child(even) {{ background-color: #f2f2f2; }}
            tr:hover {{ background-color: #e9e9e9; }}
            .positive {{ color: green; font-weight: bold; }}
            .negative {{ color: red; font-weight: bold; }}
            .neutral {{ color: #555; }}
            .alert-section {{ background-color: #fff0f0; border: 2px solid #d9534f; padding: 15px; border-radius: 8px; margin-top: 20px; }}
            .info-section {{ background-color: #f0f8ff; border: 2px solid #4a90e2; padding: 15px; border-radius: 8px; margin-top: 20px; }}
            .alert-section h2 {{ margin-top: 0; color: #d9534f; }}
            .info-section h2 {{ margin-top: 0; color: #4a90e2; }}
        </style>
    </head>
    <body>
        <h1>Daily Stock Report - {today}</h1>

    """
    
    # --- Personal Alerts Section ---
    total_drops = [s for s in portfolio_details if s['total_change_pct'] <= -30]
    daily_drops_10 = [s for s in portfolio_details if s['daily_change_pct'] <= -10]
    daily_drops_20 = [s for s in portfolio_details if s['daily_change_pct'] <= -20]
    daily_gains_20 = [s for s in portfolio_details if s['daily_change_pct'] >= 20]

    # --- Significant Daily Movers (Gains) ---
    if daily_gains_20:
        html += "<div class='info-section'><h2>🚀 My Portfolio Movers (Up)</h2>"
        html += "<h3 style='color:green;'>Stocks Up More Than 20% Today</h3><table>"
        html += "<tr><th>Stock</th><th>Daily Change</th></tr>"
        for s in daily_gains_20:
            html += f"<tr><td>{s['ticker']}</td><td class='positive'>{s['daily_change_pct']:.1f}%</td></tr>"
        html += "</table></div>"

    # --- Significant Daily Movers & Alerts (Drops) ---
    if total_drops or daily_drops_10 or daily_drops_20:
        html += "<div class='alert-section'><h2>🔻 My Portfolio Alerts & Drops</h2>"
        
        if total_drops:
            html += "<h3 style='color:#d9534f;'>TOTAL DROP Over 30%</h3><table>"
            html += "<tr><th>Stock</th><th>Buy Price</th><th>Current</th><th>Total Change</th></tr>"
            for s in total_drops:
                html += f"<tr><td>{s['ticker']}</td><td>{s['buy_price']:.2f}</td><td>{s['current_price']:.2f}</td><td class='negative'>{s['total_change_pct']:.1f}%</td></tr>"
            html += "</table>"

        if daily_drops_10:
            html += "<h3 style='color:#d9534f;'>⚠️ DAILY DROP Over 10%</h3><table>"
            html += "<tr><th>Stock</th><th>Yesterday</th><th>Current</th><th>Daily Change</th></tr>"
            for s in daily_drops_10:
                html += f"<tr><td>{s['ticker']}</td><td>{s['prev_close']:.2f}</td><td>{s['current_price']:.2f}</td><td class='negative'>{s['daily_change_pct']:.1f}%</td></tr>"
            html += "</table>"

        if daily_drops_20:
            html += "<h3 style='color:#d9534f;'>Stocks Down More Than 20% Today</h3><table>"
            html += "<tr><th>Stock</th><th>Daily Change</th></tr>"
            for s in daily_drops_20:
                html += f"<tr><td>{s['ticker']}</td><td class='negative'>{s['daily_change_pct']:.1f}%</td></tr>"
            html += "</table>"
            
        html += "</div>"
    
    # --- NEW: General Market Scan Section ---
    html += "<div class='info-section' style='background-color: #f5f5f5; border-color: #aaa;'>"
    # UPDATED: Title reflects the new 5% filter
    html += "<h2>🌎 General Market Scan - Losers (Cap >100M, Drop >5%)</h2>"
    
    if general_market_losers:
        html += "<table><tr><th>Stock</th><th>Name</th><th>Daily Change</th><th>Market Cap</th></tr>"
        for stock in general_market_losers:
            html += f"""
                <tr>
                    <td>{stock['Symbol']}</td>
                    <td>{stock['Name']}</td>
                    <td class='negative'>{stock['% Change']:.2f}%</td>
                    <td>{stock['Market Cap']}</td>
                </tr>
            """
        html += "</table>"
    else:
        # UPDATED: Message reflects the new 5% filter
        html += "<p>No stocks found matching the criteria (Market Cap > 100M and Daily Drop > 5%).</p>"
    
    html += "</div>"
    # --- End of General Market Scan Section ---

    html += """
        <h2>My Portfolio Summary</h2>
        <table>
            <tr>
                <th>Stock</th>
                <th>Buy Price</th>
                <th>Current Price</th>
                <th>Daily Change</th>
                <th>Total Change</th>
            </tr>
    """

    # --- Portfolio Summary Table ---
    for stock in portfolio_details:
        daily_cls = "positive" if stock['daily_change_pct'] > 0 else ("negative" if stock['daily_change_pct'] < 0 else "neutral")
        total_cls = "positive" if stock['total_change_pct'] > 0 else ("negative" if stock['total_change_pct'] < 0 else "neutral")
        
        html += f"""
            <tr>
                <td>{stock['ticker']}</td>
                <td>{stock['buy_price']:.2f}</td>
                <td>{stock['current_price']:.2f}</td>
                <td class='{daily_cls}'>{stock['daily_change_pct']:+.2f}%</td>
                <td class='{total_cls}'>{stock['total_change_pct']:+.2f}%</td>
            </tr>
        """
    
    html += "</table>"

    html += "</body></html>"
    return html

def send_email(html_body):
    """ Sends an email with the given HTML body. """
    if not SENDER_EMAIL or not SENDER_PASSWORD or not RECIPIENT_EMAIL:
        print("Error: Email credentials (GMAIL_USER, GMAIL_PASSWORD, RECIPIENT_EMAIL) not set in environment variables.")
        return

    today = datetime.now().strftime("%Y-%m-%d")
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"📈 Daily Stock Report - {today}"
    msg["From"] = SENDER_EMAIL
    msg["To"] = RECIPIENT_EMAIL
    
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)
            print("Daily report email sent successfully.")
    except Exception as e:
        print(f"Error sending email: {e}")
        traceback.print_exc()

def check_portfolio_and_report():
    try:
        df = pd.read_excel(PORTFOLIO_FILE, header=HEADER_ROW)
    except FileNotFoundError:
        print(f"Error: Could not find file {PORTFOLIO_FILE}")
        return
    except Exception as e:
        print(f"Error reading Excel file: {e}")
        return

    df.columns = [str(c).strip() for c in df.columns]

    required_cols = [TICKER_COLUMN, BUY_PRICE_COLUMN]
    for col in required_cols:
        if col not in df.columns:
            print(f"Error: Missing column '{col}'. Found columns: {list(df.columns)}")
            return

    print("Reading portfolio from Excel...")
    
    portfolio_map = {}
    for index, row in df.iterrows():
        ticker_symbol = str(row[TICKER_COLUMN]).strip()
        buy_price_raw = row[BUY_PRICE_COLUMN]

        if not ticker_symbol or ticker_symbol.lower() == 'nan' or pd.isna(buy_price_raw):
            continue
            
        buy_price = clean_price(buy_price_raw)
        if buy_price:
            portfolio_map[ticker_symbol] = buy_price
    
    if not portfolio_map:
        print("No valid tickers found in portfolio file.")
        # Do not return yet, user might just want the general scan
    
    tickers_list = list(portfolio_map.keys())
    
    # --- Portfolio Data Processing ---
    portfolio_details = []
    if tickers_list:
        print(f"Fetching data for {len(tickers_list)} tickers: {', '.join(tickers_list)}")
        try:
            all_data = yf.download(tickers_list, period="5d", progress=False)
            if all_data.empty or len(all_data) < 2:
                print("Could not download sufficient portfolio data from yfinance.")
            else:
                close_prices = all_data['Close']
                latest_prices = close_prices.iloc[-1]
                prev_prices = close_prices.iloc[-2]

                for ticker, buy_price in portfolio_map.items():
                    try:
                        if len(tickers_list) == 1:
                            current_price = latest_prices
                            prev_close = prev_prices
                        else:
                            current_price = latest_prices.get(ticker)
                            prev_close = prev_prices.get(ticker)

                        if current_price is None or prev_close is None or pd.isna(current_price) or pd.isna(prev_close):
                            print(f"Skipping {ticker}: Missing current or previous price data.")
                            continue

                        total_change_pct = ((current_price - buy_price) / buy_price) * 100
                        daily_change_pct = ((current_price - prev_close) / prev_close) * 100

                        details = {
                            "ticker": ticker,
                            "buy_price": buy_price,
                            "current_price": current_price,
                            "prev_close": prev_close,
                            "daily_change_pct": daily_change_pct,
                            "total_change_pct": total_change_pct
                        }
                        portfolio_details.append(details)
                        
                        print(f"{ticker}: Buy={buy_price:.2f}, Current={current_price:.2f}, "
                              f"Daily={daily_change_pct:+.1f}%, Total={total_change_pct:+.1f}%")

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

    # --- NEW: Get General Market Losers ---
    general_market_losers = get_general_market_losers()
    # --- End ---

    if not portfolio_details and not general_market_losers:
        print("No portfolio details or general market losers to report.")
        return

    # --- Report Generation and Sending ---
    print("\nGenerating HTML report...")
    # Pass the new data to the report generator
    html_report = generate_html_report(portfolio_details, general_market_losers)
    
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
        send_email(html_body)
    else:
        print("\nEmail credentials not set. Skipping email send.")
        print("View your report at: daily_stock_report.html")

if __name__ == "__main__":
    check_portfolio_and_report()
