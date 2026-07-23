// Portfolio data
let portfolio = [];
let currentUsdIlsRate = 3.65;
let selectedStock = null; // Track which stock is selected for detail view

// DOM Elements
const addBtn = document.getElementById('addBtn');
const importBtn = document.getElementById('importBtn');
const excelUpload = document.getElementById('excelUpload');
const ticker = document.getElementById('ticker');
const shares = document.getElementById('shares');
const buyPrice = document.getElementById('buyPrice');
const portfolioBody = document.getElementById('portfolioBody');
const totalValue = document.getElementById('totalValue');
const totalGain = document.getElementById('totalGain');
const totalPercent = document.getElementById('totalPercent');

// Event Listeners
addBtn.addEventListener('click', addStock);
importBtn.addEventListener('click', importExcel);

// Initialize
initApp();

async function initApp() {
    localStorage.removeItem('portfolio');
    await fetchExchangeRate();
    await loadDefaultPortfolio();
}

async function fetchExchangeRate() {
    const CACHE_KEY = 'usd_ils_rate';
    const CACHE_TIME_KEY = 'usd_ils_rate_timestamp';
    const CACHE_DURATION = 4 * 60 * 60 * 1000;

    const cachedRate = localStorage.getItem(CACHE_KEY);
    const cachedTime = localStorage.getItem(CACHE_TIME_KEY);

    if (cachedRate && cachedTime) {
        if (Date.now() - parseInt(cachedTime) < CACHE_DURATION) {
            currentUsdIlsRate = parseFloat(cachedRate);
            displayExchangeRate();
            return;
        }
    }

    try {
        const response = await fetch('https://api.exchangerate-api.com/v4/latest/USD');
        const data = await response.json();
        if (data.rates.ILS) {
            currentUsdIlsRate = data.rates.ILS;
            localStorage.setItem(CACHE_KEY, currentUsdIlsRate);
            localStorage.setItem(CACHE_TIME_KEY, Date.now());
        }
    } catch (e) { console.warn(e); }
    displayExchangeRate();
}

function displayExchangeRate() {
    const headerTitle = document.querySelector('.logo h1');
    if (headerTitle) {
        if (!document.getElementById('rate-display')) {
            const rateSpan = document.createElement('span');
            rateSpan.id = 'rate-display';
            rateSpan.style.fontSize = '0.8rem';
            rateSpan.style.marginLeft = '10px';
            rateSpan.style.color = '#64748b';
            rateSpan.style.fontWeight = 'normal';
            rateSpan.innerHTML = `(שער: ₪${currentUsdIlsRate.toFixed(2)})`;
            headerTitle.appendChild(rateSpan);
        } else {
            document.getElementById('rate-display').innerHTML = `(שער: ₪${currentUsdIlsRate.toFixed(2)})`;
        }
    }
}

async function loadDefaultPortfolio() {
    try {
        let response = await fetch('תיק מניות.xlsx');
        if (!response.ok) response = await fetch('portfolio.xlsx');
        if (!response.ok) { updatePortfolio(); return; }

        const arrayBuffer = await response.arrayBuffer();
        const workbook = XLSX.read(arrayBuffer, { type: 'array' });
        const rawData = XLSX.utils.sheet_to_json(workbook.Sheets[workbook.SheetNames[0]], { header: 1 });

        if (rawData.length > 0) processComplexExcelData(rawData);
        else updatePortfolio();

    } catch (error) {
        console.error(error);
        updatePortfolio();
    }
}

function processComplexExcelData(rows) {
    // Scan for explicit Exchange Rate in the first 20 rows
    for (let i = 0; i < Math.min(rows.length, 20); i++) {
        const row = rows[i];
        if (!row) continue;
        for (let j = 0; j < row.length; j++) {
            const val = String(row[j]).trim();
            if (val.includes('שער הדולר') || val.includes('Dollar Rate')) {
                let rateVal = parseFloat(String(row[j + 1] || "").replace(/[^\d\.]/g, ''));
                if (!rateVal || isNaN(rateVal)) {
                    rateVal = parseFloat(String(row[j + 2] || "").replace(/[^\d\.]/g, ''));
                }
                if (rateVal && !isNaN(rateVal) && rateVal > 0) {
                    currentUsdIlsRate = rateVal;
                    console.log(`Using Excel Exchange Rate: ${currentUsdIlsRate}`);
                    displayExchangeRate();
                    break;
                }
            }
        }
    }

    let headerRowIndex = -1;
    let colMap = { ticker: -1, shares: -1, price: -1, currentPrice: -1 };

    for (let i = 0; i < rows.length; i++) {
        const row = rows[i];
        if (!row) continue;
        for (let j = 0; j < row.length; j++) {
            const val = String(row[j]).trim();
            if (['טיקר', 'Ticker', 'Symbol'].some(s => val.includes(s))) colMap.ticker = j;
            if (['כמות מניות', 'כמות', 'Shares'].some(s => val === s)) colMap.shares = j;
            if (['מחיר עלות', 'Cost', 'Buy Price'].some(s => val.includes(s))) colMap.price = j;
            if (['מחיר זמן אמת', 'Real Time', 'Last Price', 'Current Price'].some(s => val.includes(s))) colMap.currentPrice = j;
        }
        if (colMap.ticker !== -1 && colMap.shares !== -1) { headerRowIndex = i; break; }
        colMap = { ticker: -1, shares: -1, price: -1, currentPrice: -1 };
    }

    if (headerRowIndex === -1) { updatePortfolio(); return; }

    portfolio = [];

    for (let i = headerRowIndex + 1; i < rows.length; i++) {
        const row = rows[i];
        if (!row) continue;

        let tickerStr = String(row[colMap.ticker] || "").trim();
        if (!tickerStr || tickerStr.toLowerCase() === "nan") continue;

        let sharesStr = String(row[colMap.shares] || "0").replace(/[^\d\.]/g, '');
        const sharesVal = parseFloat(sharesStr);
        if (!sharesVal) continue;

        // Buy Price Parsing
        let priceVal = 0;
        if (colMap.price !== -1) {
            priceVal = parseFloat(String(row[colMap.price]).replace(/[^\d\.\-]/g, '')) || 0;
        }

        // Current Price Parsing (Real Time from Excel)
        let currentPriceVal = 0;
        let foundRealTimePrice = false;
        if (colMap.currentPrice !== -1) {
            let rawRealTime = String(row[colMap.currentPrice] || "");
            let cleanRealTime = rawRealTime.replace(/[^\d\.\-]/g, '');
            let parsed = parseFloat(cleanRealTime);
            if (!isNaN(parsed) && parsed !== 0) {
                currentPriceVal = parsed;
                foundRealTimePrice = true;
            }
        }

        // Currency Detection
        const ILS_TICKERS = ['1159250', '1183441'];
        let currency = 'USD';
        if (ILS_TICKERS.includes(tickerStr)) currency = 'ILS';

        // Current Price Strategy
        let finalCurrentPrice;
        if (foundRealTimePrice) {
            finalCurrentPrice = currentPriceVal;
        } else {
            finalCurrentPrice = priceVal > 0 ? priceVal * (0.95 + Math.random() * 0.1) : (currency === 'ILS' ? 100 : 30);
        }

        portfolio.push({
            ticker: tickerStr.toUpperCase(),
            shares: sharesVal,
            buyPrice: priceVal,
            currentPrice: finalCurrentPrice,
            currency: currency
        });
    }
    updatePortfolio();
}

async function importExcel() {
    const file = excelUpload.files[0];
    if (!file) { alert('אנא בחר קובץ Excel תחילה'); return; }

    const reader = new FileReader();
    reader.onload = function (e) {
        const workbook = XLSX.read(e.target.result, { type: 'array' });
        const rawData = XLSX.utils.sheet_to_json(workbook.Sheets[workbook.SheetNames[0]], { header: 1 });
        if (confirm('לייבא נתונים מהקובץ?')) processComplexExcelData(rawData);
    };
    reader.readAsArrayBuffer(file);
}

function addStock() {
    const tickerVal = ticker.value.trim().toUpperCase();
    const sharesVal = parseInt(shares.value);
    const priceVal = parseFloat(buyPrice.value);

    if (!tickerVal || !sharesVal || !priceVal) return alert('מלא את כל השדות');

    const currency = ['1159250', '1183441'].includes(tickerVal) ? 'ILS' : 'USD';

    portfolio.push({
        ticker: tickerVal,
        shares: sharesVal,
        buyPrice: priceVal,
        currentPrice: priceVal * (0.95 + Math.random() * 0.1),
        currency: currency
    });

    updatePortfolio();
    ticker.value = ''; shares.value = '1'; buyPrice.value = '';
}

function removeStock(index) {
    if (confirm('למחוק?')) {
        portfolio.splice(index, 1);
        updatePortfolio();
    }
}

async function selectStock(index) {
    selectedStock = portfolio[index];

    // Try to fetch live price from API
    if (window.stockAPI && !window.stockAPI.shouldUseExcelData(selectedStock.ticker)) {
        const result = await window.stockAPI.fetchQuote(selectedStock.ticker);

        if (result.source === 'api' || result.source === 'cache') {
            // Update with live price
            selectedStock.currentPrice = result.data.price;
            selectedStock.apiData = result.data;
            selectedStock.dataSource = result.source;
        } else {
            // Use Excel data
            selectedStock.dataSource = result.source;
        }
    } else {
        selectedStock.dataSource = 'excel';
    }

    showDetailView();
}

function showDetailView() {
    document.getElementById('portfolio-view').style.display = 'none';
    document.getElementById('detail-view').style.display = 'block';
    renderDetailView();
}

function backToPortfolio() {
    selectedStock = null;
    document.getElementById('detail-view').style.display = 'none';
    document.getElementById('portfolio-view').style.display = 'block';
}

function renderDetailView() {
    if (!selectedStock) return;

    const detailContainer = document.getElementById('detail-content');
    const stock = selectedStock;

    // Calculate metrics
    const gain = (stock.currentPrice - stock.buyPrice) * stock.shares;
    const gainPercent = stock.buyPrice > 0 ? ((stock.currentPrice - stock.buyPrice) / stock.buyPrice) * 100 : 0;
    const totalCost = stock.buyPrice * stock.shares;
    const totalValue = stock.currentPrice * stock.shares;

    const symbol = stock.currency === 'ILS' ? '₪' : '$';
    const gainClass = gain >= 0 ? 'positive' : 'negative';

    // Data source badge
    const sourceLabels = {
        'api': '<span style="background: #64748b; color: white; padding: 0.25rem 0.5rem; border-radius: 4px; font-size: 0.75rem; margin-right: 0.5rem;">📊 EXCEL</span>',
        'cache': '<span style="background: #64748b; color: white; padding: 0.25rem 0.5rem; border-radius: 4px; font-size: 0.75rem; margin-right: 0.5rem;">📊 EXCEL</span>',
        'excel': '<span style="background: #64748b; color: white; padding: 0.25rem 0.5rem; border-radius: 4px; font-size: 0.75rem; margin-right: 0.5rem;">📊 EXCEL</span>',
        'rate_limited': '<span style="background: #64748b; color: white; padding: 0.25rem 0.5rem; border-radius: 4px; font-size: 0.75rem; margin-right: 0.5rem;">📊 EXCEL</span>'
    };
    const sourceBadge = sourceLabels[stock.dataSource] || sourceLabels['excel'];

    detailContainer.innerHTML = `
        <div class="detail-header">
            <button class="btn-back" onclick="backToPortfolio()">
                <i class="fas fa-arrow-right"></i> חזרה לתיק
            </button>
            <h2>${sourceBadge}${stock.ticker} <small style="color: #94a3b8;">(${stock.currency})</small></h2>
        </div>
        
        <div class="section-panel">
            <h3><i class="fas fa-chart-area"></i> ביצועי מניה</h3>
            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="metric-label">מחיר עלות</div>
                    <div class="metric-value">${symbol}${stock.buyPrice.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">מחיר נוכחי</div>
                    <div class="metric-value">${symbol}${stock.currentPrice.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">שינוי</div>
                    <div class="metric-value ${gainClass}"><span dir="ltr">${gainPercent >= 0 ? '+' : ''}${gainPercent.toFixed(2)}%</span></div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">כמות</div>
                    <div class="metric-value">${stock.shares}</div>
                </div>
            </div>
        </div>
        
        <div class="section-panel">
            <h3><i class="fas fa-wallet"></i> סיכום פוזיציה</h3>
            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="metric-label">עלות כוללת</div>
                    <div class="metric-value">${symbol}${totalCost.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">שווי נוכחי</div>
                    <div class="metric-value">${symbol}${totalValue.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">רווח/הפסד</div>
                    <div class="metric-value ${gainClass}"><span dir="ltr">${gain >= 0 ? '+' : ''}${symbol}${Math.abs(gain).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span></div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">אחוז שינוי</div>
                    <div class="metric-value ${gainClass}"><span dir="ltr">${gainPercent >= 0 ? '+' : ''}${gainPercent.toFixed(2)}%</span></div>
                </div>
            </div>
        </div>
        
        <div class="section-panel">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
                <h3 style="margin: 0;"><i class="fas fa-chart-line"></i> גרף מחירים</h3>
                <div class="period-selector">
                    <button class="period-btn active" data-period="1w">שבוע</button>
                    <button class="period-btn" data-period="1mo">חודש</button>
                    <button class="period-btn" data-period="3mo">3 חודשים</button>
                    <button class="period-btn" data-period="6mo">6 חודשים</button>
                    <button class="period-btn" data-period="1y">שנה</button>
                    <button class="period-btn" data-period="all">הכל</button>
                </div>
            </div>
            <div class="chart-container">
                <canvas id="stockChart"></canvas>
            </div>
            <div class="chart-note">
                <i class="fas fa-info-circle"></i>
                <span>הגרף מבוסס על נתוני Excel. לנתונים בזמן אמת נדרש חיבור ל-API פיננסי.</span>
            </div>
        </div>
        
        <div class="section-panel">
            <h3><i class="fas fa-chart-bar"></i> סטטיסטיקות נוספות</h3>
            <div class="info-grid">
                <div class="info-item">
                    <i class="fas fa-coins"></i>
                    <div>
                        <div class="info-label">מטבע</div>
                        <div class="info-value">${stock.currency === 'ILS' ? 'שקל ישראלי (₪)' : 'דולר אמריקאי ($)'}</div>
                    </div>
                </div>
                <div class="info-item">
                    <i class="fas fa-calendar"></i>
                    <div>
                        <div class="info-label">עדכון אחרון</div>
                        <div class="info-value">${new Date().toLocaleDateString('he-IL')}</div>
                    </div>
                </div>
                <div class="info-item">
                    <i class="fas fa-exchange-alt"></i>
                    <div>
                        <div class="info-label">שער המרה</div>
                        <div class="info-value">$1 = ₪${currentUsdIlsRate.toFixed(2)}</div>
                    </div>
                </div>
            </div>
        </div>
    `;

    // Initialize chart after DOM is ready
    setTimeout(() => {
        initStockChart(stock);
        setupPeriodButtons();
    }, 100);
}

function updatePortfolio() {
    if (!portfolio || portfolio.length === 0) {
        portfolioBody.innerHTML = `<tr class="empty-state"><td colspan="7">התיק ריק. יבא קובץ Excel או הוסף מניות ידנית.</td></tr>`;
        updateSummary();
        return;
    }

    portfolioBody.innerHTML = '';

    portfolio.forEach((stock, index) => {
        const gain = (stock.currentPrice - stock.buyPrice) * stock.shares;
        const gainPercent = stock.buyPrice > 0 ? ((stock.currentPrice - stock.buyPrice) / stock.buyPrice) * 100 : 0;
        const gainClass = gain >= 0 ? 'positive' : 'negative';

        const symbol = stock.currency === 'ILS' ? '₪' : '$';
        const formatMoney = (val) => `<span dir="ltr">${val < 0 ? '-' : ''}${symbol}${Math.abs(val).toFixed(2)}</span>`;
        const formatPercent = (val) => `<span dir="ltr">${val < 0 ? '-' : (val > 0 ? '+' : '')}${Math.abs(val).toFixed(2)}%</span>`;

        const tr = document.createElement('tr');
        tr.style.cursor = 'pointer';
        tr.onclick = () => selectStock(index);
        tr.innerHTML = `
            <td><strong>${stock.ticker}</strong> <small style="color:#94a3b8">(${stock.currency})</small></td>
            <td>${stock.shares}</td>
            <td>${formatMoney(stock.buyPrice)}</td>
            <td>${formatMoney(stock.currentPrice)}</td>
            <td class="${gainClass}">${formatMoney(gain)}</td>
            <td class="${gainClass}">${formatPercent(gainPercent)}</td>
            <td onclick="event.stopPropagation()">
                <button class="btn-remove" onclick="removeStock(${index})">
                    <i class="fas fa-trash"></i>
                </button>
            </td>
        `;
        portfolioBody.appendChild(tr);
    });

    updateSummary();
}

function updateSummary() {
    // Calculate separate totals for ILS and USD
    let totalIlsVal = 0, totalIlsCost = 0;
    let totalUsdVal = 0, totalUsdCost = 0;

    portfolio.forEach(stock => {
        if (stock.currency === 'ILS') {
            totalIlsVal += stock.currentPrice * stock.shares;
            totalIlsCost += stock.buyPrice * stock.shares;
        } else {
            totalUsdVal += stock.currentPrice * stock.shares;
            totalUsdCost += stock.buyPrice * stock.shares;
        }
    });

    // Convert USD to ILS for combined total
    const combinedTotal = totalIlsVal + (totalUsdVal * currentUsdIlsRate);
    const combinedCost = totalIlsCost + (totalUsdCost * currentUsdIlsRate);
    const gain = combinedTotal - combinedCost;
    const gainPercent = combinedCost > 0 ? (gain / combinedCost) * 100 : 0;

    const fmtIls = (n) => `₪${n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    const fmtUsd = (n) => `$${n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

    // Display split totals with combined total
    totalValue.innerHTML = `
        <div style="font-size: 0.65em; color: #64748b; margin-bottom: 4px;">
            ${fmtIls(totalIlsVal)} + ${fmtUsd(totalUsdVal)}
        </div>
        <div>${fmtIls(combinedTotal)}</div>
    `;

    totalGain.innerHTML = `<span dir="ltr">${gain >= 0 ? '+' : ''}${fmtIls(gain)}</span>`;
    totalGain.className = gain >= 0 ? 'card-value positive' : 'card-value negative';

    totalPercent.innerHTML = `<span dir="ltr">${gainPercent > 0 ? '+' : ''}${gainPercent.toFixed(2)}%</span>`;
    totalPercent.className = gainPercent >= 0 ? 'card-value positive' : 'card-value negative';
}

window.removeStock = removeStock;
window.selectStock = selectStock;
window.backToPortfolio = backToPortfolio;
