// Chart and period selection functionality
let stockChart = null;
let currentPeriod = '1w';

function initStockChart(stock) {
    const ctx = document.getElementById('stockChart');
    if (!ctx) return;

    // Destroy existing chart if any
    if (stockChart) {
        stockChart.destroy();
    }

    // Generate data from Excel (API is disabled)
    const data = generateHistoricalData(stock, currentPeriod);
    const dataSource = 'excel';

    const isProfit = stock.currentPrice >= stock.buyPrice;
    const lineColor = isProfit ? '#10b981' : '#ef4444';
    const fillColor = isProfit ? 'rgba(16, 185, 129, 0.1)' : 'rgba(239, 68, 68, 0.1)';

    stockChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.labels,
            datasets: [{
                label: 'מחיר',
                data: data.prices,
                borderColor: lineColor,
                backgroundColor: fillColor,
                borderWidth: 2,
                fill: true,
                tension: 0.4,
                pointRadius: 0,
                pointHoverRadius: 6,
                pointHoverBackgroundColor: lineColor,
                pointHoverBorderColor: '#fff',
                pointHoverBorderWidth: 2
            }, {
                label: 'מחיר עלות',
                data: Array(data.labels.length).fill(stock.buyPrice),
                borderColor: '#f59e0b',
                borderWidth: 2,
                borderDash: [5, 5],
                fill: false,
                pointRadius: 0,
                pointHoverRadius: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                intersect: false,
                mode: 'index'
            },
            plugins: {
                legend: {
                    display: true,
                    position: 'top',
                    align: 'end',
                    labels: {
                        usePointStyle: false,
                        padding: 15,
                        font: {
                            size: 12,
                            family: "'Segoe UI', system-ui, -apple-system, sans-serif"
                        },
                        generateLabels: function (chart) {
                            const datasets = chart.data.datasets;
                            return datasets.map((dataset, i) => ({
                                text: dataset.label,
                                fillStyle: dataset.borderColor,
                                strokeStyle: dataset.borderColor,
                                lineWidth: 2,
                                lineDash: dataset.borderDash || [],
                                hidden: !chart.isDatasetVisible(i),
                                datasetIndex: i
                            }));
                        }
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    padding: 12,
                    titleFont: {
                        size: 13
                    },
                    bodyFont: {
                        size: 12
                    },
                    callbacks: {
                        label: function (context) {
                            const symbol = stock.currency === 'ILS' ? '₪' : '$';
                            return context.dataset.label + ': ' + symbol + context.parsed.y.toFixed(2);
                        }
                    }
                }
            },
            scales: {
                x: {
                    grid: {
                        display: false
                    },
                    ticks: {
                        maxRotation: 0,
                        autoSkipPadding: 20,
                        font: {
                            size: 11
                        }
                    }
                },
                y: {
                    grid: {
                        color: 'rgba(0, 0, 0, 0.05)'
                    },
                    ticks: {
                        callback: function (value) {
                            const symbol = stock.currency === 'ILS' ? '₪' : '$';
                            return symbol + value.toFixed(0);
                        },
                        font: {
                            size: 11
                        }
                    }
                }
            }
        }
    });

    // Update data source indicator
    updateDataSourceIndicator(dataSource);
}

function processApiHistoricalData(apiData, stock, period) {
    const periods = {
        '1w': 7,
        '1mo': 30,
        '3mo': 90,
        '6mo': 180,
        '1y': 365,
        'all': 1825
    };

    const days = periods[period] || 7;
    const cutoffDate = new Date();
    cutoffDate.setDate(cutoffDate.getDate() - days);

    // Filter data by period
    const filtered = apiData.filter(item => new Date(item.date) >= cutoffDate);

    const labels = filtered.map(item => {
        const date = new Date(item.date);
        if (days <= 7) {
            return date.toLocaleDateString('he-IL', { weekday: 'short' });
        } else if (days <= 30) {
            return date.toLocaleDateString('he-IL', { day: 'numeric', month: 'short' });
        } else {
            return date.toLocaleDateString('he-IL', { month: 'short', year: '2-digit' });
        }
    });

    const prices = filtered.map(item => item.close);

    return { labels, prices };
}

function updateDataSourceIndicator(source) {
    const noteEl = document.querySelector('.chart-note span');
    if (noteEl) {
        const messages = {
            'api': 'נתונים מקובץ Excel',
            'cache': 'נתונים מקובץ Excel',
            'excel': 'נתונים מקובץ Excel - גרף מבוסס על מחיר עלות ומחיר נוכחי',
            'simulated': 'נתונים מקובץ Excel - גרף מבוסס על מחיר עלות ומחיר נוכחי',
            'rate_limited': 'נתונים מקובץ Excel',
            'error': 'נתונים מקובץ Excel'
        };
        noteEl.textContent = messages[source] || messages['excel'];
    }
}

function generateHistoricalData(stock, period) {
    const periods = {
        '1w': { days: 7, interval: 1 },
        '1mo': { days: 30, interval: 1 },
        '3mo': { days: 90, interval: 3 },
        '6mo': { days: 180, interval: 7 },
        '1y': { days: 365, interval: 7 },
        'all': { days: 1825, interval: 30 } // 5 years with monthly data points
    };

    const config = periods[period] || periods['1w'];
    const points = Math.floor(config.days / config.interval);

    const labels = [];
    const prices = [];

    // Generate dates
    const now = new Date();
    for (let i = points - 1; i >= 0; i--) {
        const date = new Date(now);
        date.setDate(date.getDate() - (i * config.interval));

        if (config.days <= 7) {
            labels.push(date.toLocaleDateString('he-IL', { weekday: 'short' }));
        } else if (config.days <= 30) {
            labels.push(date.toLocaleDateString('he-IL', { day: 'numeric', month: 'short' }));
        } else {
            labels.push(date.toLocaleDateString('he-IL', { month: 'short', year: '2-digit' }));
        }
    }

    // Generate price trend from buyPrice to currentPrice
    const priceChange = stock.currentPrice - stock.buyPrice;
    const volatility = Math.abs(priceChange) * 0.15; // 15% of total change as volatility

    for (let i = 0; i < points; i++) {
        const progress = i / (points - 1);
        const trendPrice = stock.buyPrice + (priceChange * progress);
        const randomVariation = (Math.random() - 0.5) * volatility;
        prices.push(Math.max(0, trendPrice + randomVariation));
    }

    // Ensure last price matches current price
    prices[prices.length - 1] = stock.currentPrice;

    return { labels, prices };
}

function setupPeriodButtons() {
    const buttons = document.querySelectorAll('.period-btn');
    buttons.forEach(btn => {
        btn.addEventListener('click', function () {
            // Remove active class from all buttons
            buttons.forEach(b => b.classList.remove('active'));
            // Add active class to clicked button
            this.classList.add('active');
            // Update period and refresh chart
            currentPeriod = this.dataset.period;
            initStockChart(selectedStock);
        });
    });
}

// Add to window for access
window.initStockChart = initStockChart;
window.setupPeriodButtons = setupPeriodButtons;
