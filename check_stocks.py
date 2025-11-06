import pandas as pd
import yfinance as yf
import smtplib
import os
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import re

# --- Configuration: Update these to match your file ---
# This must be the exact name of the file you upload to GitHub
PORTFOLIO_FILE = 'תיק מניות.xlsx - גיליון1.csv' 
# This is the name of your Ticker/Symbol column
TICKER_COLUMN = 'טיקר'
# This is the name of your Buy Price (Cost Price) column
BUY_PRICE_COLUMN = 'מחיר עלות'
# ----------------------------------------------------

# --- Do Not Touch: Email details will be taken from GitHub Secrets ---
SENDER_EMAIL = os.environ.get('GMAIL_USER')
SENDER_PASSWORD = os.environ.get('GMAIL_PASSWORD')
RECIPIENT_EMAIL = os.environ.get('RECIPIENT_EMAIL')
# ------------------------------------------------------------------

def clean_price(price_str):
    """Cleans a price string, removing currency symbols and commas."""
    if isinstance(price_str, (int, float)):
        return float(price_str)
    # Remove any non-numeric characters except for the decimal point
    cleaned_str = re.sub(r"[^0-9.]", "", str(price_str))
    if cleaned_str:
        return float(cleaned_str)
    return None

def check_portfolio():
    try:
        # Read the CSV file. We try 'utf-8' first, then 'utf-8-sig'
        # which is common for CSVs exported from Excel with Hebrew.
        portfolio = pd.read_csv(PORTFOLIO_FILE, encoding='utf-8')
    except UnicodeDecodeError:
        print("UTF-8 failed, trying 'utf-8-sig'...")
        try:
            portfolio = pd.read_csv(PORTFOLIO_FILE, encoding='utf-8-sig')
        except Exception as e:
            print(f"Error reading CSV file with all encodings: {e}")
            return
    except FileNotFoundError:
        print(f"Error: Could not find file {PORTFOLIO_FILE}")
        return
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        return

    alerts = []
    print("Checking portfolio...")

    for index, row in portfolio.iterrows():
        try:
            ticker_symbol = str(row[TICKER_COLUMN]).strip()
            buy_price_raw = row[BUY_PRICE_COLUMN]

            # Skip rows with missing critical data
            if pd.isna(ticker_symbol) or ticker_symbol == "nan" or ticker_symbol == "" or pd.isna(buy_price_raw):
                print(f"Skipping row {index+1}: missing Ticker or Buy Price")
                continue

            buy_price = clean_price(buy_price_raw)
            if buy_price is None or buy_price == 0:
                print(f"Skipping {ticker_symbol}: Invalid Buy Price ({buy_price_raw})")
                continue

            # Fetch current market data
            data = yf.Ticker(ticker_symbol).history(period='1d')
            
            if data.empty:
                print(f"Could not find data for {ticker_symbol}")
                continue

            current_price = data['Close'].iloc[-1]
            change_pct = ((current_price - buy_price) / buy_price) * 100

            print(f"Checked {ticker_symbol}: Current={current_price:.2f}, Buy={buy_price:.2f}, Change={change_pct:.1f}%")

            # Check the alert condition (-10% drop)
            if change_pct <= -10:
                alert_msg = (
                    f"--- Price Alert! ---\n"
                    f"Stock: {ticker_symbol}\n"
                    f"Buy Price: {buy_price:.2f}\n"
                    f"Current Price: {current_price:.2f}\n"
                    f"Change: {change_pct:.1f}%\n"
                )
                alerts.append(alert_msg)

        except Exception as e:
            print(f"Error processing {ticker_symbol} (Row {index+1}): {e}")

    if alerts:
        print("\nFound alerts, sending email...")
        send_email(alerts)
    else:
        print("\nNo stocks triggered alerts. All good!")

def send_email(alerts):
    if not SENDER_EMAIL or not SENDER_PASSWORD or not RECIPIENT_EMAIL:
        print("Error: Email credentials not set in environment variables (GitHub Secrets).")
        return

    message_body = "\n".join(alerts)
    
    msg = MIMEMultipart()
    # Email Subject in English
    msg["Subject"] = "🔔 Stock Portfolio Alert"
    msg["From"] = SENDER_EMAIL
    msg["To"] = RECIPIENT_EMAIL
    
    # Attach the body with UTF-8 encoding (to support Hebrew ticker names in the email)
    msg.attach(MIMEText(message_body, "plain", "utf-8"))

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)
            print("Alerts email sent successfully!")
    except Exception as e:
        print(f"Error sending email: {e}")

if __name__ == "__main__":
    check_portfolio()
