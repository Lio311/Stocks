import yfinance as yf
import pandas as pd
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# === CONFIG ===
portfolio_file = "portfolio.csv"  # your local CSV file with column 'Symbol'
alert_threshold = 0.2  # 20%
email_to = "your_email@example.com"
email_from = "your_email@example.com"
email_password = "YOUR_APP_PASSWORD"  # if you want automatic email sending

# === LOAD PORTFOLIO ===
portfolio = pd.read_csv(portfolio_file)
symbols = portfolio["Symbol"].tolist()

# === DOWNLOAD DATA ===
data = yf.download(symbols, period="2d")["Close"]

# === CALCULATE DAILY CHANGES ===
changes = ((data.iloc[-1] - data.iloc[-2]) / data.iloc[-2]) * 100
changes = changes.round(2)

# === CREATE ALERTS ===
drops = changes[changes <= -20]
gains = changes[changes >= 20]

# === MARKET SUMMARY ===
index_symbols = {"S&P 500": "^GSPC", "NASDAQ": "^IXIC", "Dow Jones": "^DJI"}
market_data = {name: yf.download(ticker, period="2d")["Close"] for name, ticker in index_symbols.items()}
market_changes = {
    name: round(((df.iloc[-1] - df.iloc[-2]) / df.iloc[-2]) * 100, 2)
    for name, df in market_data.items()
}

# === BUILD HTML REPORT ===
today = datetime.now().strftime("%B %d, %Y")

html = f"""
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; background-color: #f7f7f7; padding: 20px; }}
        h1 {{ color: #333; }}
        table {{ border-collapse: collapse; width: 100%; margin-top: 10px; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #4CAF50; color: white; }}
        tr:nth-child(even) {{ background-color: #f2f2f2; }}
        .positive {{ color: green; font-weight: bold; }}
        .negative {{ color: red; font-weight: bold; }}
    </style>
</head>
<body>
    <h1>Daily Stock Report - {today}</h1>

    <h2>Market Overview</h2>
    <table>
        <tr><th>Index</th><th>Daily Change (%)</th></tr>
"""
for name, change in market_changes.items():
    cls = "positive" if change > 0 else "negative"
    html += f"<tr><td>{name}</td><td class='{cls}'>{change}</td></tr>"

html += """
    </table>

    <h2>Significant Movements</h2>
"""

if not drops.empty:
    html += "<h3 style='color:red;'>🔻 Stocks Down More Than 20%</h3><table><tr><th>Symbol</th><th>Change (%)</th></tr>"
    for symbol, change in drops.items():
        html += f"<tr><td>{symbol}</td><td class='negative'>{change}</td></tr>"
    html += "</table>"

if not gains.empty:
    html += "<h3 style='color:green;'>🚀 Stocks Up More Than 20%</h3><table><tr><th>Symbol</th><th>Change (%)</th></tr>"
    for symbol, change in gains.items():
        html += f"<tr><td>{symbol}</td><td class='positive'>{change}</td></tr>"
    html += "</table>"

html += "</body></html>"

# === SAVE TO FILE ===
with open("daily_stock_report.html", "w", encoding="utf-8") as f:
    f.write(html)

# === OPTIONAL: SEND EMAIL ===
send_email = False  # change to True if you want to send email

if send_email:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"Daily Stock Report - {today}"
    msg["From"] = email_from
    msg["To"] = email_to
    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(email_from, email_password)
        server.sendmail(email_from, email_to, msg.as_string())

print("✅ Report generated successfully: daily_stock_report.html")
