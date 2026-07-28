/**
 * CoinMarketCap API v2 Client for JavaScript SDK.
 * 
 * Requires an API key (https://pro.coinmarketcap.com).
 * 
 * Example:
 *   const { CoinMarketCap } = require('./coinmarketcap');
 *   const cmc = new CoinMarketCap({ apiKey: 'YOUR_API_KEY' });
 *   const prices = await cmc.getPrices(['btc', 'eth']);
 */

const SYMBOL_MAP = {
    btc: "BTC", bitcoin: "BTC",
    eth: "ETH", evm: "ETH", ethereum: "ETH",
    bnb: "BNB", bsc: "BNB", binancecoin: "BNB",
    sol: "SOL", solana: "SOL",
    trx: "TRX", tron: "TRX",
    ton: "TON", "the-open-network": "TON",
};

const DEFAULT_SYMBOLS = ["BTC", "ETH", "BNB", "SOL", "TRX", "TON"];

class CoinMarketCap {
    constructor(options = {}) {
        if (!options.apiKey) {
            throw new Error("CoinMarketCap requires an apiKey parameter.");
        }
        this.apiKey = options.apiKey;
        this.baseUrl = "https://pro-api.coinmarketcap.com";
    }

    async _get(path, params = {}) {
        const url = new URL(this.baseUrl + path);
        Object.keys(params).forEach(k => url.searchParams.append(k, params[k]));

        const headers = {
            "X-CMC_PRO_API_KEY": this.apiKey,
            "Accept": "application/json"
        };

        const resp = await fetch(url.toString(), { headers });
        if (!resp.ok) {
            if (resp.status === 429) return null;
            throw new Error(`CoinMarketCap HTTP ${resp.status}`);
        }
        return await resp.json();
    }

    _resolveSymbols(coins) {
        if (!coins || !coins.length) return DEFAULT_SYMBOLS;
        return coins.map(c => SYMBOL_MAP[c.toLowerCase()] || c.toUpperCase());
    }

    async getPrices(coins = null, vsCurrency = "USD") {
        const symbols = this._resolveSymbols(coins);
        const vs = vsCurrency.toUpperCase();
        const data = await this._get("/v2/cryptocurrency/quotes/latest", {
            symbol: symbols.join(","),
            convert: vs
        });

        const result = {};
        if (!data || !data.data) {
            symbols.forEach(s => result[s.toLowerCase()] = 0.0);
            return result;
        }

        const quotes = data.data;
        for (const sym of symbols) {
            const entries = quotes[sym];
            let entry = null;
            if (Array.isArray(entries) && entries.length) {
                entry = entries[0];
            } else if (typeof entries === "object" && entries !== null) {
                entry = entries;
            }

            if (!entry) {
                result[sym.toLowerCase()] = 0.0;
                continue;
            }

            const price = (entry.quote && entry.quote[vs] && entry.quote[vs].price) || 0;
            result[sym.toLowerCase()] = parseFloat(price);
        }
        return result;
    }

    async getPrice(coin, vsCurrency = "USD") {
        const prices = await this.getPrices([coin], vsCurrency);
        const sym = (SYMBOL_MAP[coin.toLowerCase()] || coin.toUpperCase()).toLowerCase();
        return prices[sym] || 0.0;
    }

    async getListings(limit = 100, vsCurrency = "USD") {
        const vs = vsCurrency.toUpperCase();
        const data = await this._get("/v1/cryptocurrency/listings/latest", {
            limit: String(limit),
            convert: vs
        });

        if (!data || !data.data) return [];
        return data.data.map(item => {
            const q = (item.quote && item.quote[vs]) || {};
            return {
                symbol: item.symbol || "",
                name: item.name || "",
                price: q.price || 0,
                market_cap: q.market_cap || 0,
                volume_24h: q.volume_24h || 0,
                percent_change_24h: q.percent_change_24h || 0,
                percent_change_7d: q.percent_change_7d || 0
            };
        });
    }

    async getCoinInfo(coin) {
        const sym = SYMBOL_MAP[coin.toLowerCase()] || coin.toUpperCase();
        const data = await this._get("/v2/cryptocurrency/info", { symbol: sym });
        if (!data || !data.data) return null;
        const entries = data.data[sym];
        if (Array.isArray(entries) && entries.length) return entries[0];
        return entries || null;
    }
}

module.exports = { CoinMarketCap };
