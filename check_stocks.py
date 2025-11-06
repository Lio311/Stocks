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
        df = pd.read_excel(PORTFOLIO_FILE, header=8)
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

    print("Checking portfolio...")

    total_drop_alerts = []
    daily_drop_alerts = []

    for index, row in df.iterrows():
        ticker_symbol = None
        try:
            ticker_symbol = str(row[TICKER_COLUMN]).strip()
            buy_price_raw = row[BUY_PRICE_COLUMN]

            if not ticker_symbol or pd.isna(buy_price_raw):
                continue

            buy_price = clean_price(buy_price_raw)
            if not buy_price:
                continue

            data = yf.Ticker(ticker_symbol).history(period='5d')  # 5 ימים למקרה שאין מסחר היום
            if data.empty:
                print(f"No data for {ticker_symbol}")
                continue

            current_price = data['Close'].iloc[-1]
            prev_close = data['Close'].iloc[-2] if len(data) > 1 else current_price

            total_change_pct = ((current_price - buy_price) / buy_price) * 100
            daily_change_pct = ((current_price - prev_close) / prev_close) * 100

            print(f"{ticker_symbol}: Total={total_change_pct:.1f}%, Daily={daily_change_pct:.1f}%")

            # ירידה כוללת מעל 30%
            if total_change_pct <= -30:
                total_drop_alerts.append(
                    f"🔻 TOTAL DROP ALERT\n"
                    f"Stock: {ticker_symbol}\n"
                    f"Buy Price: {buy_price:.2f}\n"
                    f"Current: {current_price:.2f}\n"
                    f"Change: {total_change_pct:.1f}%\n"
                )

            # ירידה יומית מעל 10%
            if daily_change_pct <= -10:
                daily_drop_alerts.append(
                    f"⚠️ DAILY DROP ALERT\n"
                    f"Stock: {ticker_symbol}\n"
                    f"Yesterday Close: {prev_close:.2f}\n"
                    f"Current: {current_price:.2f}\n"
                    f"Change Today: {daily_change_pct:.1f}%\n"
                )

        except Exception as e:
            print(f"Error processing row {index+1}: {e}")

    if total_drop_alerts or daily_drop_alerts:
        body = ""
        if total_drop_alerts:
            body += "=== TOTAL DROP OVER 30% ===\n" + "\n".join(total_drop_alerts) + "\n\n"
        if daily_drop_alerts:
            body += "=== DAILY DROP OVER 10% ===\n" + "\n".join(daily_drop_alerts)

        print("\nSending alerts email...")
        send_email(body)
    else:
        print("\nNo alerts triggered today.")

def send_email(body):
    if not SENDER_EMAIL or not SENDER_PASSWORD or not RECIPIENT_EMAIL:
        print("Error: Email credentials not set.")
        return

    msg = MIMEMultipart()
    msg["Subject"] = "📉 Stock Alerts - Portfolio Monitor"
    msg["From"] = SENDER_EMAIL
    msg["To"] = RECIPIENT_EMAIL
    msg.attach(MIMEText(body, "plain", "utf-8"))

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)
            print("Alert email sent successfully.")
    except Exception as e:
        print(f"Error sending email: {e}")

if __name__ == "__main__":
    check_portfolio()
