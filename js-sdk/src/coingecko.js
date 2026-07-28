/**
 * CoinGecko API v3 Client for JavaScript SDK.
 * 
 * Example:
 *   const { CoinGecko } = require('./coingecko');
 *   const cg = new CoinGecko();
 *   const prices = await cg.getPrices(['btc', 'eth']);
 *   const price = await cg.getPrice('sol');
 */

const COIN_ID_MAP = {
    btc: "bitcoin", bitcoin: "bitcoin",
    eth: "ethereum", evm: "ethereum", ethereum: "ethereum",
    bnb: "binancecoin", bsc: "binancecoin", binancecoin: "binancecoin",
    sol: "solana", solana: "solana",
    trx: "tron", tron: "tron",
    ton: "the-open-network", "the-open-network": "the-open-network",
};

const DEFAULT_COINS = ["bitcoin", "ethereum", "binancecoin", "solana", "tron", "the-open-network"];

const SYMBOL_MAP = {
    bitcoin: "btc", ethereum: "eth", binancecoin: "bnb", solana: "sol",
    tron: "trx", "the-open-network": "ton",
};

class CoinGecko {
    constructor(options = {}) {
        this.apiKey = options.apiKey || null;
        this.baseUrl = this.apiKey
            ? "https://pro-api.coingecko.com/api/v3"
            : "https://api.coingecko.com/api/v3";
    }

    async _get(path, params = {}) {
        const url = new URL(this.baseUrl + path);
        Object.keys(params).forEach(k => url.searchParams.append(k, params[k]));

        const headers = {};
        if (this.apiKey) {
            headers["x-cg-pro-api-key"] = this.apiKey;
        }

        const resp = await fetch(url.toString(), { headers });
        if (!resp.ok) {
            if (resp.status === 429) return null;
            throw new Error(`CoinGecko HTTP ${resp.status}`);
        }
        return await resp.json();
    }

    _resolveIds(coins) {
        if (!coins || !coins.length) return DEFAULT_COINS;
        return coins.map(c => {
            const cgId = COIN_ID_MAP[c.toLowerCase()];
            if (!cgId) throw new Error(`Unknown coin '${c}'.`);
            return cgId;
        });
    }

    async getPrices(coins = null, vsCurrency = "usd") {
        const cgIds = this._resolveIds(coins);
        const vs = vsCurrency.toLowerCase();
        const data = await this._get("/simple/price", {
            ids: Array.from(new Set(cgIds)).join(","),
            vs_currencies: vs
        }) || {};

        const result = {};
        for (const cgId of cgIds) {
            const sym = SYMBOL_MAP[cgId] || cgId;
            result[sym] = parseFloat((data[cgId] || {})[vs] || 0);
        }
        return result;
    }

    async getPrice(coin, vsCurrency = "usd") {
        const prices = await this.getPrices([coin], vsCurrency);
        const cgId = COIN_ID_MAP[coin.toLowerCase()] || coin.toLowerCase();
        const sym = SYMBOL_MAP[cgId] || cgId;
        return prices[sym] || 0.0;
    }

    async getCoinInfo(coin) {
        const cgId = COIN_ID_MAP[coin.toLowerCase()] || coin.toLowerCase();
        return await this._get(`/coins/${cgId}`);
    }

    async search(query) {
        const data = await this._get("/search", { query }) || {};
        return data.coins || [];
    }

    async getMarketChart(coin, days = 7, vsCurrency = "usd") {
        const cgId = COIN_ID_MAP[coin.toLowerCase()] || coin.toLowerCase();
        return await this._get(`/coins/${cgId}/market_chart`, {
            vs_currency: vsCurrency.toLowerCase(),
            days: String(days)
        });
    }
}

module.exports = { CoinGecko };
