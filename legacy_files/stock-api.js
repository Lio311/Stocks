// Stock API Client for Yahoo Finance
class StockAPI {
    constructor() {
        this.config = window.API_CONFIG;
        this.callLog = this.loadCallLog();
    }

    // Load call log from localStorage
    loadCallLog() {
        const stored = localStorage.getItem('api_call_log');
        if (stored) {
            const log = JSON.parse(stored);
            // Clean old entries (older than 1 day)
            const oneDayAgo = Date.now() - (24 * 60 * 60 * 1000);
            log.calls = log.calls.filter(time => time > oneDayAgo);
            return log;
        }
        return { calls: [] };
    }

    // Save call log to localStorage
    saveCallLog() {
        localStorage.setItem('api_call_log', JSON.stringify(this.callLog));
    }

    // Check if we can make an API call (rate limiting)
    canMakeCall() {
        const now = Date.now();
        const oneMinuteAgo = now - 60000;
        const oneDayAgo = now - (24 * 60 * 60 * 1000);

        // Count calls in last minute
        const callsLastMinute = this.callLog.calls.filter(time => time > oneMinuteAgo).length;
        if (callsLastMinute >= this.config.RATE_LIMIT.MAX_CALLS_PER_MINUTE) {
            console.warn('Rate limit: Too many calls in the last minute');
            return false;
        }

        // Count calls in last day
        const callsLastDay = this.callLog.calls.filter(time => time > oneDayAgo).length;
        if (callsLastDay >= this.config.RATE_LIMIT.MAX_CALLS_PER_DAY) {
            console.warn('Rate limit: Daily limit reached');
            return false;
        }

        return true;
    }

    // Log an API call
    logCall() {
        this.callLog.calls.push(Date.now());
        this.saveCallLog();
    }

    // Get from cache
    getCache(key) {
        const cached = localStorage.getItem(`api_cache_${key}`);
        if (cached) {
            const data = JSON.parse(cached);
            if (Date.now() - data.timestamp < data.duration) {
                console.log(`Cache hit: ${key}`);
                return data.value;
            } else {
                localStorage.removeItem(`api_cache_${key}`);
            }
        }
        return null;
    }

    // Set cache
    setCache(key, value, duration) {
        const data = {
            value: value,
            timestamp: Date.now(),
            duration: duration
        };
        localStorage.setItem(`api_cache_${key}`, JSON.stringify(data));
    }

    // Map ticker if needed
    mapTicker(ticker) {
        return this.config.TICKER_MAP[ticker] || ticker;
    }

    // Check if should use Excel data
    shouldUseExcelData(ticker) {
        return this.config.USE_EXCEL_DATA.includes(ticker);
    }

    // Fetch current quote from Yahoo Finance
    async fetchQuote(ticker) {
        // Check if API is enabled
        if (!this.config.ENABLE_API) {
            return { source: 'excel', data: null };
        }

        // Check if should use Excel data
        if (this.shouldUseExcelData(ticker)) {
            return { source: 'excel', data: null };
        }

        const mappedTicker = this.mapTicker(ticker);
        const cacheKey = `quote_${mappedTicker}`;

        // Check cache
        const cached = this.getCache(cacheKey);
        if (cached) {
            return { source: 'cache', data: cached };
        }

        // Check rate limit
        if (!this.canMakeCall()) {
            return { source: 'rate_limited', data: null };
        }

        try {
            const apiUrl = `${this.config.YAHOO_QUOTE_URL}?symbols=${mappedTicker}`;
            const url = `${this.config.CORS_PROXY}${encodeURIComponent(apiUrl)}`;
            this.logCall();

            // Add timeout to prevent hanging
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), this.config.API_TIMEOUT);

            const response = await fetch(url, { signal: controller.signal });
            clearTimeout(timeoutId);

            const data = await response.json();

            if (data.quoteResponse && data.quoteResponse.result && data.quoteResponse.result.length > 0) {
                const quote = data.quoteResponse.result[0];
                const result = {
                    price: quote.regularMarketPrice || quote.price,
                    change: quote.regularMarketChange || 0,
                    changePercent: quote.regularMarketChangePercent || 0,
                    volume: quote.regularMarketVolume || 0,
                    latestTradingDay: new Date(quote.regularMarketTime * 1000).toISOString().split('T')[0]
                };

                // Cache the result
                this.setCache(cacheKey, result, this.config.CACHE_DURATION.QUOTE);

                return { source: 'api', data: result };
            } else {
                console.error('Invalid API response:', data);
                return { source: 'error', data: null, error: 'Invalid response' };
            }
        } catch (error) {
            if (error.name === 'AbortError') {
                console.error('API Timeout');
                return { source: 'error', data: null, error: 'Timeout' };
            }
            console.error('API Error:', error);
            return { source: 'error', data: null, error: error.message };
        }
    }

    // Fetch historical data from Yahoo Finance
    async fetchHistoricalData(ticker, period = '1y') {
        // Check if API is enabled
        if (!this.config.ENABLE_API) {
            return { source: 'excel', data: null };
        }

        // Check if should use Excel data
        if (this.shouldUseExcelData(ticker)) {
            return { source: 'excel', data: null };
        }

        const mappedTicker = this.mapTicker(ticker);
        const cacheKey = `historical_${mappedTicker}_${period}`;

        // Check cache
        const cached = this.getCache(cacheKey);
        if (cached) {
            return { source: 'cache', data: cached };
        }

        // Check rate limit
        if (!this.canMakeCall()) {
            return { source: 'rate_limited', data: null };
        }

        try {
            // Calculate time range
            const periodMap = {
                '1w': 7,
                '1mo': 30,
                '3mo': 90,
                '6mo': 180,
                '1y': 365,
                'full': 1825 // 5 years
            };
            const days = periodMap[period] || 365;
            const period2 = Math.floor(Date.now() / 1000);
            const period1 = period2 - (days * 24 * 60 * 60);

            const apiUrl = `${this.config.YAHOO_QUERY_URL}${mappedTicker}?period1=${period1}&period2=${period2}&interval=1d`;
            const url = `${this.config.CORS_PROXY}${encodeURIComponent(apiUrl)}`;
            this.logCall();

            // Add timeout to prevent hanging
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), this.config.API_TIMEOUT);

            const response = await fetch(url, { signal: controller.signal });
            clearTimeout(timeoutId);

            const data = await response.json();

            if (data.chart && data.chart.result && data.chart.result.length > 0) {
                const chartData = data.chart.result[0];
                const timestamps = chartData.timestamp;
                const quotes = chartData.indicators.quote[0];

                const result = timestamps.map((timestamp, i) => ({
                    date: new Date(timestamp * 1000).toISOString().split('T')[0],
                    open: quotes.open[i],
                    high: quotes.high[i],
                    low: quotes.low[i],
                    close: quotes.close[i],
                    volume: quotes.volume[i]
                })).filter(item => item.close !== null); // Filter out null values

                // Cache the result
                this.setCache(cacheKey, result, this.config.CACHE_DURATION.HISTORICAL_DATA);

                return { source: 'api', data: result };
            } else {
                console.error('Invalid API response:', data);
                return { source: 'error', data: null, error: 'Invalid response' };
            }
        } catch (error) {
            if (error.name === 'AbortError') {
                console.error('API Timeout');
                return { source: 'error', data: null, error: 'Timeout' };
            }
            console.error('API Error:', error);
            return { source: 'error', data: null, error: error.message };
        }
    }
}

// Create global instance
window.stockAPI = new StockAPI();
