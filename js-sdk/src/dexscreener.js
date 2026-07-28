/**
 * DexScreener API Client for JavaScript SDK.
 * 
 * Public DEX analytics endpoint — no key required.
 * 
 * Example:
 *   const { DexScreener } = require('./dexscreener');
 *   const ds = new DexScreener();
 *   const pairs = await ds.search('SOL/USDC');
 *   const price = await ds.getTokenPrice('solana', 'So111...112');
 */

const CHAINS = {
    ethereum: "ethereum", eth: "ethereum", evm: "ethereum",
    bsc: "bsc", solana: "solana", sol: "solana",
    tron: "tron", trx: "tron", ton: "ton",
    base: "base", arbitrum: "arbitrum", polygon: "polygon", avalanche: "avalanche"
};

class DexScreener {
    constructor() {
        this.baseUrl = "https://api.dexscreener.com";
    }

    _chain(chainId) {
        return CHAINS[chainId.toLowerCase()] || chainId.toLowerCase();
    }

    async _get(path, params = {}) {
        const url = new URL(this.baseUrl + path);
        Object.keys(params).forEach(k => url.searchParams.append(k, params[k]));

        const resp = await fetch(url.toString());
        if (!resp.ok) {
            if (resp.status === 429) return null;
            throw new Error(`DexScreener HTTP ${resp.status}`);
        }
        return await resp.json();
    }

    async search(query) {
        const data = await this._get("/latest/dex/search", { q: query });
        return (data && data.pairs) ? data.pairs : [];
    }

    async getPair(chainId, pairAddress) {
        const chain = this._chain(chainId);
        const data = await this._get(`/latest/dex/pairs/${chain}/${pairAddress}`);
        if (!data || !data.pairs) return null;
        return data.pairs[0] || null;
    }

    async getTokens(chainId, tokenAddresses) {
        const chain = this._chain(chainId);
        const data = await this._get(`/tokens/v1/${chain}/${tokenAddresses}`);
        return Array.isArray(data) ? data : [];
    }

    async getTokenPools(chainId, tokenAddress) {
        const chain = this._chain(chainId);
        const data = await this._get(`/token-pairs/v1/${chain}/${tokenAddress}`);
        return Array.isArray(data) ? data : [];
    }

    async getTokenPrice(chainId, tokenAddress) {
        const pairs = await this.getTokens(chainId, tokenAddress);
        if (!pairs || !pairs.length) return 0.0;

        let best = pairs[0];
        let maxLiq = 0;
        for (const p of pairs) {
            const liq = (p.liquidity && p.liquidity.usd) || 0;
            if (liq > maxLiq) {
                maxLiq = liq;
                best = p;
            }
        }
        return best && best.priceUsd ? parseFloat(best.priceUsd) : 0.0;
    }

    async getTopBoosts() {
        const data = await this._get("/token-boosts/top/v1");
        return Array.isArray(data) ? data : [];
    }
}

module.exports = { DexScreener };
