import pandas as pd
import yfinance as yf
import smtplib
import os
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import re

# --- Configuration ---
PORTFOLIO_FILE = 'תיק מניות.xlsx'
TICKER_COLUMN = 'טיקר'
BUY_PRICE_COLUMN = 'מחיר עלות'
# ----------------------

SENDER_EMAIL = os.environ.get('GMAIL_USER')
SENDER_PASSWORD = os.environ.get('GMAIL_PASSWORD')
RECIPIENT_EMAIL = os.environ.get('RECIPIENT_EMAIL')


def clean_price(price_str):
    if isinstance(price_str, (int, float)):
        return float(price_str)
    cleaned_str = re.sub(r"[^0-9.]", "", str(price_str))
    return float(cleaned_str) if cleaned_str else None


def check_portfolio():
    try:
        # השתמש בקריאה המתאימה לקובץ Excel
        portfolio = pd.read_excel(PORTFOLIO_FILE)
    except FileNotFoundError:
        print(f"Error: Could not find file {PORTFOLIO_FILE}")
        return
    except Exception as e:
        print(f"Error reading Excel file: {e}")
        return

    alerts = []
    print("Checking portfolio...")

    for index, row in portfolio.iterrows():
        try:
            ticker_symbol = str(row[TICKER_COLUMN]).strip()
            buy_price_raw = row[BUY_PRICE_COLUMN]

            if not ticker_symbol or pd.isna(buy_price_raw):
                print(f"Skipping row {index+1}: missing Ticker or Buy Price")
                continue

            buy_price = clean_price(buy_price_raw)
            if not buy_price:
                print(f"Skipping {ticker_symbol}: Invalid Buy Price ({buy_price_raw})")
                continue

            data = yf.Ticker(ticker_symbol).history(period='1d')
            if data.empty:
                print(f"Could not find data for {ticker_symbol}")
                continue

            current_price = data['Close'].iloc[-1]
            change_pct = ((current_price - buy_price) / buy_price) * 100

            print(f"Checked {ticker_symbol}: Current={current_price:.2f}, Buy={buy_price:.2f}, Change={change_pct:.1f}%")

            if change_pct <= -20:  # שינוי ל־20% ירידה
                alerts.append(
                    f"--- Price Alert! ---\n"
                    f"Stock: {ticker_symbol}\n"
                    f"Buy Price: {buy_price:.2f}\n"
                    f"Current Price: {current_price:.2f}\n"
                    f"Change: {change_pct:.1f}%\n"
                )

        except Exception as e:
            print(f"Error processing {ticker_symbol} (Row {index+1}): {e}")

    if alerts:
        print("\nFound alerts, sending email...")
        send_email(alerts)
    else:
        print("\nNo stocks triggered alerts. All good!")


def send_email(alerts):
    if not SENDER_EMAIL or not SENDER_PASSWORD or not RECIPIENT_EMAIL:
        print("Error: Email credentials not set in environment variables.")
        return

    message_body = "\n".join(alerts)
    msg = MIMEMultipart()
    msg["Subject"] = "🔔 Stock Portfolio Alert"
    msg["From"] = SENDER_EMAIL
    msg["To"] = RECIPIENT_EMAIL
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
