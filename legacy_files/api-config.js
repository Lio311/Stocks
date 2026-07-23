// API Configuration - Disabled (Using Excel Data Only)
const API_CONFIG = {
    // API disabled due to CORS issues
    API_KEY: null,

    // URLs (not used)
    CORS_PROXY: 'https://api.allorigins.win/raw?url=',
    YAHOO_QUERY_URL: 'https://query1.finance.yahoo.com/v8/finance/chart/',
    YAHOO_QUOTE_URL: 'https://query1.finance.yahoo.com/v7/finance/quote',

    // Rate Limiting
    RATE_LIMIT: {
        MAX_CALLS_PER_MINUTE: 10,
        MAX_CALLS_PER_DAY: 2000
    },

    // Cache Duration (in milliseconds)
    CACHE_DURATION: {
        CURRENT_PRICE: 5 * 60 * 1000,
        HISTORICAL_DATA: 12 * 60 * 60 * 1000,
        QUOTE: 5 * 60 * 1000
    },

    // Ticker Mapping
    TICKER_MAP: {
        '1159250': 'CSPX.L',
        '1183441': 'SPXS.L'
    },

    // Use Excel data for all stocks
    USE_EXCEL_DATA: [],

    // API DISABLED - Using Excel data only
    ENABLE_API: false,

    // Timeout
    API_TIMEOUT: 10000
};

// Export
window.API_CONFIG = API_CONFIG;
