import pandas as pd
import yfinance as yf
import smtplib
import os
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import re
from datetime import datetime
import traceback # לניפוי שגיאות

# --- Configuration ---
PORTFOLIO_FILE = 'תיק מניות.xlsx'
TICKER_COLUMN = 'טיקר'
BUY_PRICE_COLUMN = 'מחיר עלות'
HEADER_ROW = 8 # שורה שבה מתחילים הנתונים (כותרות הן שורה 9)
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
    
    # מסיר כל דבר שאינו ספרה, נקודה, או מינוס (למקרה הצורך)
    cleaned_str = re.sub(r"[^0-9.-]", "", price_str)
    
    try:
        return float(cleaned_str) if cleaned_str else None
    except ValueError:
        print(f"Warning: Could not convert price string '{price_str}' to float.")
        return None

def get_market_overview():
    """ Fetches daily change for major market indices. """
    print("Fetching market overview...")
    index_symbols = {"S&P 500": "^GSPC", "NASDAQ": "^IXIC", "Dow Jones": "^DJI"}
    market_changes = {}

    for name, ticker in index_symbols.items():
        try:
            data = yf.download(ticker, period="2d", progress=False)
            if len(data) < 2:
                market_changes[name] = 0.0
                continue
            
            change = ((data['Close'].iloc[-1] - data['Close'].iloc[-2]) / data['Close'].iloc[-2]) * 100
            market_changes[name] = round(change, 2)
        except Exception as e:
            print(f"Error fetching index {name} ({ticker}): {e}")
            market_changes[name] = 0.0
            
    return market_changes

def generate_html_report(market_changes, portfolio_details):
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

        <h2>Market Overview</h2>
        <table>
            <tr><th>Index</th><th>Daily Change (%)</th></tr>
    """
    
    # --- Market Overview Table ---
    for name, change in market_changes.items():
        cls = "positive" if change > 0 else ("negative" if change < 0 else "neutral")
        html += f"<tr><td>{name}</td><td class='{cls}'>{change:+.2f}%</td></tr>"

    html += """
        </table>

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

    # --- Alerts Section ---
    total_drops = [s for s in portfolio_details if s['total_change_pct'] <= -30]
    daily_drops_10 = [s for s in portfolio_details if s['daily_change_pct'] <= -10]
    daily_drops_20 = [s for s in portfolio_details if s['daily_change_pct'] <= -20]
    daily_gains_20 = [s for s in portfolio_details if s['daily_change_pct'] >= 20]

    # --- Significant Daily Movers (Gains) ---
    if daily_gains_20:
        html += "<div class='info-section'><h2>🚀 Significant Daily Movers (Up)</h2>"
        html += "<h3 style='color:green;'>Stocks Up More Than 20% Today</h3><table>"
        html += "<tr><th>Stock</th><th>Daily Change</th></tr>"
        for s in daily_gains_20:
            html += f"<tr><td>{s['ticker']}</td><td class='positive'>{s['daily_change_pct']:.1f}%</td></tr>"
        html += "</table></div>"

    # --- Significant Daily Movers & Alerts (Drops) ---
    if total_drops or daily_drops_10 or daily_drops_20:
        html += "<div class='alert-section'><h2>🔻 Portfolio Alerts & Significant Drops</h2>"
        
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
    
    # Attach the HTML part
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
    
    # יצירת מפה של טיקרים ומחירי קנייה
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
        return

    tickers_list = list(portfolio_map.keys())
    print(f"Fetching data for {len(tickers_list)} tickers: {', '.join(tickers_list)}")
    
    # הורדת כל הנתונים בבת אחת
    try:
        all_data = yf.download(tickers_list, period="5d", progress=False)
        if all_data.empty:
            print("No data downloaded from yfinance.")
            return
            
        # ודא שיש לנו מספיק נתונים
        if len(all_data) < 2:
            print("Not enough historical data (less than 2 days) to calculate changes.")
            return
            
        close_prices = all_data['Close']
        latest_prices = close_prices.iloc[-1]
        prev_prices = close_prices.iloc[-2]

    except Exception as e:
        print(f"Error downloading batch data from yfinance: {e}")
        traceback.print_exc()
        return

    # --- קבלת סקירת שוק ---
    market_changes = get_market_overview()

    # --- עיבוד נתוני התיק ---
    portfolio_details = []
    
    for ticker, buy_price in portfolio_map.items():
        try:
            # אם יש רק טיקר אחד, yfinance מחזיר מבנה נתונים שטוח
            if len(tickers_list) == 1:
                current_price = latest_prices
                prev_close = prev_prices
            else:
                current_price = latest_prices[ticker]
                prev_close = prev_prices[ticker]

            if pd.isna(current_price) or pd.isna(prev_close):
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

    if not portfolio_details:
        print("No portfolio details could be processed.")
        return

    # --- יצירה ושליחת הדוח ---
    print("\nGenerating HTML report...")
    html_report = generate_html_report(market_changes, portfolio_details)
    
    # שמירת קובץ HTML מקומי
    report_filename = "daily_stock_report.html"
    try:
        with open(report_filename, "w", encoding="utf-8") as f:
            f.write(html_report)
        print(f"✅ Report generated successfully: {report_filename}")
    except Exception as e:
        print(f"Error saving HTML file: {e}")

    # שליחת אימייל
    if SENDER_EMAIL and RECIPIENT_EMAIL:
        print("Sending email...")
        send_email(html_report)
    else:
        print("\nEmail credentials not set. Skipping email send.")
        print("View your report at: daily_stock_report.html")

if __name__ == "__main__":
    check_portfolio_and_report()
