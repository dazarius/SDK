import json
from dataclasses import dataclass
from solders.pubkey import Pubkey


CHEQUES_TYPE = {
    "NativeCheque": 'native',
    "MultiCheque": 'multi',
    "TokenCheque": 'token',
    "SwapCheque": 'swap'
}

@dataclass(frozen=True)
class EVMChain:
    name: str
    chain_id: int
    rpc: str
    explorer: str
    currency: str = "ETH"
    ws: str = ""


ETHEREUM  = EVMChain("Ethereum",  1,     "ETH",  "https://eth.llamarpc.com",                        "https://etherscan.io",      "wss://eth.llamarpc.com")
BSC       = EVMChain("BSC",       56,    "BNB",  "https://bsc-dataseed.binance.org",                "https://bscscan.com",       "wss://bsc-ws-node.nariox.org")
POLYGON   = EVMChain("Polygon",   137,   "MATIC", "https://polygon-rpc.com",                        "https://polygonscan.com",   "wss://polygon-bor.publicnode.com")
ARBITRUM  = EVMChain("Arbitrum",  42161, "ETH",  "https://arb1.arbitrum.io/rpc",                    "https://arbiscan.io",       "wss://arbitrum-one.publicnode.com")
OPTIMISM  = EVMChain("Optimism",  10,    "ETH",  "https://mainnet.optimism.io",                     "https://optimistic.etherscan.io", "wss://optimism.publicnode.com")
BASE      = EVMChain("Base",      8453,  "ETH",  "https://mainnet.base.org",                        "https://basescan.org",      "wss://base.publicnode.com")
AVALANCHE = EVMChain("Avalanche", 43114, "AVAX", "https://api.avax.network/ext/bc/C/rpc",           "https://snowtrace.io",      "wss://avalanche-c-chain.publicnode.com")
FANTOM    = EVMChain("Fantom",    250,   "FTM",  "https://rpc.ftm.tools",                           "https://ftmscan.com",       "")
ZKSYNC    = EVMChain("zkSync",    324,   "ETH",  "https://mainnet.era.zksync.io",                   "https://explorer.zksync.io", "wss://mainnet.era.zksync.io/ws")
LINEA     = EVMChain("Linea",     59144, "ETH",  "https://rpc.linea.build",                         "https://lineascan.build",   "wss://rpc.linea.build")
SCROLL    = EVMChain("Scroll",    534352,"ETH",  "https://rpc.scroll.io",                           "https://scrollscan.com",    "wss://wss-rpc.scroll.io/ws")

# Testnets
BSC_TESTNET      = EVMChain("BSC Testnet",      97,    "tBNB", "https://data-seed-prebsc-1-s1.binance.org:8545", "https://testnet.bscscan.com", "")
SEPOLIA          = EVMChain("Sepolia",          11155111,"ETH","https://rpc.sepolia.org",                         "https://sepolia.etherscan.io",  "")
ARBITRUM_SEPOLIA = EVMChain("Arbitrum Sepolia", 421614, "ETH", "https://sepolia-rollup.arbitrum.io/rpc",          "https://sepolia.arbiscan.io",   "")


@dataclass(frozen=True)
class SOLNetwork:
    name: str
    rpc: str
    ws: str
    explorer: str
    currency: str = "SOL"


SOL_MAINNET = SOLNetwork("Mainnet", "https://api.mainnet-beta.solana.com", "wss://api.mainnet-beta.solana.com", "https://solscan.io")
SOL_DEVNET  = SOLNetwork("Devnet",  "https://api.devnet.solana.com",       "wss://api.devnet.solana.com",       "https://solscan.io?cluster=devnet")
SOL_TESTNET = SOLNetwork("Testnet", "https://api.testnet.solana.com",      "wss://api.testnet.solana.com",      "https://solscan.io?cluster=testnet")


@dataclass()
class TONNetwork:
    name: str
    api_url: str
    
    explorer: str
    api_key: str = ""
    currency: str = "TON"


TON_MAINNET = TONNetwork("Mainnet", "https://toncenter.com/api/v2",         "https://tonviewer.com")
TON_TESTNET = TONNetwork("Testnet", "https://testnet.toncenter.com/api/v2", "https://testnet.tonviewer.com")


@dataclass(frozen=True)
class TRXNetwork:
    name: str
    rpc: str
    explorer: str
    currency: str = "TRX"

TRX_MAINNET = TRXNetwork("Mainnet", "https://api.trongrid.io",    "https://tronscan.org")
TRX_SHASTA  = TRXNetwork("Shasta",  "https://api.shasta.trongrid.io", "https://shasta.tronscan.org")
TRX_NILE    = TRXNetwork("Nile",    "https://nile.trongrid.io",   "https://nile.tronscan.org")



@dataclass(frozen=True)
class BTCNetwork:
    name: str
    testnet: bool
    explorer: str
    currency: str = "BTC"


BTC_MAINNET = BTCNetwork("Mainnet", False, "https://mempool.space")
BTC_TESTNET = BTCNetwork("Testnet", True,  "https://mempool.space/testnet")


__ALLOW_CHAINS__ = [
    {
        "name": "Base",
        "address": "0x0000000000000000000000000000000000000000",
        "nativeCurrency": {
            "name": "Ether",
            "symbol": "ETH",
            "coingeckoId": "ethereum",
            "decimals": 18
        },
        "rpcUrls": [
            "https://mainnet.base.org"
        ],
        "wssUrls": [
            "wss://base-rpc.publicnode.com"
        ],
        "blockExplorerUrls": [
            "https://basescan.org"
        ],
        "chainIdHex": "0x2105",
        "chainIdDec": 8453,
        "gasPrice": 6000000000000000000000000,
        "deployedDate": "2026-07-18 11:29:06",
        "deployedTimestamp": 1784366946,
        "treasury": "0x72bC9A1965ea2Cb87051f882462F319873Eb185f",
        "feeDominator": 100000,
        "fees": {
            "NATIVE_BPS": 250,
            "MULTI_BPS": 250,
            "TOKEN_BPS": 250,
            "SWAP_BPS": 250,
            "maxBps": 1000
        },
        "txHash": "097a88ee6e970f2bc6106153c8f00d9b8beb6b24287433521afe5fb359b24566",
        "explorer": "https://basescan.org/tx/097a88ee6e970f2bc6106153c8f00d9b8beb6b24287433521afe5fb359b24566",
        "contractAddress": "0x455a2aAa7c7DcD413F05d56462dA13522E43d0D1",
        "balanceEth": 0.001555194185002405,
        "balanceUsd": 2.905056081758943,
        "contracts": {
            "OrbisInvoice": "0x0000000000000000000000000000000000000000",
            "OrbisCheques": "0x455a2aAa7c7DcD413F05d56462dA13522E43d0D1"
        }
    },
    {
        "name": "BSC",
        "chainIdHex": "0x38",
        "chainIdDec": 56,
        "address": "0x0000000000000000000000000000000000000000",
        "nativeCurrency": {
            "name": "BNB",
            "symbol": "BNB",
            "coingeckoId": "binancecoin",
            "decimals": 18
        },
        "rpcUrls": [
            "https://bsc-rpc.publicnode.com",
            "https://bsc-mainnet.infura.io"

        ],
        "wssUrls": [
            "wss://bsc-rpc.publicnode.com"
        ],
        "blockExplorerUrls": [
            "https://bscscan.com"
        ],
        "gasPrice": 100000000000000000000000000,
        "deployedDate": "2026-07-18 11:29:08",
        "deployedTimestamp": 1784366948,
        "treasury": "0x72bC9A1965ea2Cb87051f882462F319873Eb185f",
        "feeDominator": 100000,
        "fees": {
            "NATIVE_BPS": 250,
            "MULTI_BPS": 250,
            "TOKEN_BPS": 250,
            "SWAP_BPS": 250,
            "maxBps": 1000
        },
        "txHash": "244cfb182d0461da8cd71f26ddeea48e404858443bea081c0a81b618bf493f61",
        "explorer": "https://bscscan.com/tx/244cfb182d0461da8cd71f26ddeea48e404858443bea081c0a81b618bf493f61",
        "contractAddress": "0x455a2aAa7c7DcD413F05d56462dA13522E43d0D1",
        "balanceEth": 0.0040117876,
        "balanceUsd": 2.3710065894760004,
        "contracts": {
            "OrbisInvoice": "0x0000000000000000000000000000000000000000",
            "OrbisCheques": "0x455a2aAa7c7DcD413F05d56462dA13522E43d0D1"
        }
    },
    {
        "name": "Arbitrum",
        "address": "0x0000000000000000000000000000000000000000",
        "nativeCurrency": {
            "name": "Ether",
            "symbol": "ETH",
            "coingeckoId": "ethereum",
            "decimals": 18
        },
        "rpcUrls": [
            "https://arb1.arbitrum.io/rpc"
        ],
        "wssUrls": [
            "wss://arbitrum-one.publicnode.com"
        ],
        "blockExplorerUrls": [
            "https://arbiscan.io/"
        ],
        "chainIdHex": "0xa4b1",
        "chainIdDec": 42161,
        "gasPrice": 20004000000000000000000000,
        "deployedDate": "2026-07-18 11:29:08",
        "deployedTimestamp": 1784366948,
        "treasury": "0x72bC9A1965ea2Cb87051f882462F319873Eb185f",
        "feeDominator": 100000,
        "fees": {
            "NATIVE_BPS": 250,
            "MULTI_BPS": 250,
            "TOKEN_BPS": 250,
            "SWAP_BPS": 250,
            "maxBps": 1000
        },
        "txHash": "b2dcb9bc75f33d33ddd0d218b7208d73814fcc9a8f22ba4ab0e5f3bf65fd7bc1",
        "explorer": "https://arbiscan.io//tx/b2dcb9bc75f33d33ddd0d218b7208d73814fcc9a8f22ba4ab0e5f3bf65fd7bc1",
        "contractAddress": "0x455a2aAa7c7DcD413F05d56462dA13522E43d0D1",
        "balanceEth": 0.001403436652616,
        "balanceUsd": 2.6215775639871093,
        "contracts": {
            "OrbisInvoice": "0x0000000000000000000000000000000000000000",
            "OrbisCheques": "0x455a2aAa7c7DcD413F05d56462dA13522E43d0D1"
        }
    },
    {
        "name": "Optimism",
        "address": "0x0000000000000000000000000000000000000000",
        "nativeCurrency": {
            "name": "Ether",
            "symbol": "ETH",
            "coingeckoId": "ethereum",
            "decimals": 18
        },
        "rpcUrls": [
            "https://optimism-rpc.publicnode.com"
        ],
        "wssUrls": [
            "wss://optimism-rpc.publicnode.com"
        ],
        "blockExplorerUrls": [
            "https://explorer.optimism.io/"
        ],
        "chainIdHex": "0xa",
        "chainIdDec": 10,
        "gasPrice": 1000345000000000000000000,
        "deployedDate": "2026-07-18 11:29:11",
        "deployedTimestamp": 1784366951,
        "treasury": "0x72bC9A1965ea2Cb87051f882462F319873Eb185f",
        "feeDominator": 100000,
        "fees": {
            "NATIVE_BPS": 250,
            "MULTI_BPS": 250,
            "TOKEN_BPS": 250,
            "SWAP_BPS": 250,
            "maxBps": 1000
        },
        "txHash": "40c5391a1ba7c496130c9ac30c1e69d9134b1d91f3b17d18ac848254126bdf5d",
        "explorer": "https://explorer.optimism.io//tx/40c5391a1ba7c496130c9ac30c1e69d9134b1d91f3b17d18ac848254126bdf5d",
        "contractAddress": "0x455a2aAa7c7DcD413F05d56462dA13522E43d0D1",
        "balanceEth": 0.001819054465836274,
        "balanceUsd": 3.3979391705481845,
        "contracts": {
            "OrbisInvoice": "0x0000000000000000000000000000000000000000",
            "OrbisCheques": "0x455a2aAa7c7DcD413F05d56462dA13522E43d0D1"
        }
    },
    {
        "address": "0x0000000000000000000000000000000000000000",
        "name": "Base Sepolia",
        "testnet": true,
        "nativeCurrency": {
            "name": "Sepolia Ether",
            "symbol": "ETH",
            "coingeckoId": "ethereum",
            "decimals": 18
        },
        "rpcUrls": [
            "https://sepolia.base.org"
        ],
        "blockExplorerUrls": [
            "https://sepolia.basescan.org"
        ],
        "chainIdHex": "0x14a34",
        "chainIdDec": 84532,
        "gasPrice": 6000000000000000000000000,
        "deployedDate": "2026-07-18 11:29:13",
        "deployedTimestamp": 1784366953,
        "treasury": "0x72bC9A1965ea2Cb87051f882462F319873Eb185f",
        "feeDominator": 100000,
        "fees": {
            "NATIVE_BPS": 250,
            "MULTI_BPS": 250,
            "TOKEN_BPS": 250,
            "SWAP_BPS": 250,
            "maxBps": 1000
        },
        "balanceEth": 0.0,
        "balanceUsd": 0.0,
        "contracts": {
            "OrbisInvoice": "0x0000000000000000000000000000000000000000",
            "OrbisCheques": "0x0000000000000000000000000000000000000000"
        }
    },
    {
        "name": "BSC Testnet",
        "address": "0x0000000000000000000000000000000000000000",
        "testnet": true,
        "nativeCurrency": {
            "name": "tBNB",
            "symbol": "tBNB",
            "coingeckoId": "binancecoin",
            "decimals": 18
        },
        "rpcUrls": [
            "https://bsc-testnet.publicnode.com"
            
        ],
        "wssUrls": [
            "wss://bsc-testnet.publicnode.com"
        ],
        "blockExplorerUrls": [
            "https://testnet.bscscan.com"
        ],
        "chainIdHex": "0x61",
        "chainIdDec": 97,
        "gasPrice": 100000000000000000000000000,
        "deployedDate": "2026-07-18 11:29:14",
        "deployedTimestamp": 1784366954,
        "treasury": "0x72bC9A1965ea2Cb87051f882462F319873Eb185f",
        "contractAddress": "0xc00a171e6a821c0a5ac95070cb0ac61628ee4f78",
        "feeDominator": 100000,
        "fees": {
            "NATIVE_BPS": 250,
            "MULTI_BPS": 250,
            "TOKEN_BPS": 250,
            "SWAP_BPS": 250,
            "maxBps": 1000
        },
        "balanceEth": 0.0,
        "balanceUsd": 0.0,
        "contracts": {
            "OrbisInvoice": "0x0000000000000000000000000000000000000000",
            "OrbisCheques": "0xc00a171e6a821c0a5ac95070cb0ac61628ee4f78"
        }
    }
]

__SOL__NATIVE__ = "So11111111111111111111111111111111111111111"
__SOL__WS__ = "wss://api.mainnet-beta.solana.com"
__SOL__WS__DEVNET__ = "wss://api.devnet.solana.com"

__SOL__EXPLORERS__ = {
    "mainnet": {
        "solscan":  "https://solscan.io",
        "solana":   "https://explorer.solana.com",
        "xray":     "https://xray.helius.xyz",
        "solanafm": "https://solana.fm",
    },
    "devnet": {
        "solscan":  "https://solscan.io?cluster=devnet",
        "solana":   "https://explorer.solana.com?cluster=devnet",
        "solanafm": "https://solana.fm?cluster=devnet-solana",
    },
}
__NULL_ADDRESS__ = "0x0000000000000000000000000000000000000000"
__MULTICALL3__ = "0xcA11bde05977b3631167028862bE2a173976CA11"
__MULTICALL3_ABI__ = [
    {
        "inputs": [{"components": [{"name": "target","type": "address"},{"name": "callData","type": "bytes"}],"name": "calls","type": "tuple[]"}],
        "name": "aggregate",
        "outputs": [{"name": "blockNumber","type": "uint256"},{"name": "returnData","type": "bytes[]"}],
        "stateMutability": "payable",
        "type": "function"
    },
    {
        "inputs": [{"components": [{"name": "target","type": "address"},{"name": "allowFailure","type": "bool"},{"name": "callData","type": "bytes"}],"name": "calls","type": "tuple[]"}],
        "name": "aggregate3",
        "outputs": [{"components": [{"name": "success","type": "bool"},{"name": "returnData","type": "bytes"}],"name": "returnData","type": "tuple[]"}],
        "stateMutability": "payable",
        "type": "function"
    },
    {
        "inputs": [{"components": [{"name": "target","type": "address"},{"name": "allowFailure","type": "bool"},{"name": "value","type": "uint256"},{"name": "callData","type": "bytes"}],"name": "calls","type": "tuple[]"}],
        "name": "aggregate3Value",
        "outputs": [{"components": [{"name": "success","type": "bool"},{"name": "returnData","type": "bytes"}],"name": "returnData","type": "tuple[]"}],
        "stateMutability": "payable",
        "type": "function"
    },
    {
        "inputs": [{"components": [{"name": "target","type": "address"},{"name": "callData","type": "bytes"}],"name": "calls","type": "tuple[]"}],
        "name": "blockAndAggregate",
        "outputs": [{"name": "blockNumber","type": "uint256"},{"name": "blockHash","type": "bytes32"},{"components": [{"name": "success","type": "bool"},{"name": "returnData","type": "bytes"}],"name": "returnData","type": "tuple[]"}],
        "stateMutability": "payable",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "getBasefee",
        "outputs": [{"name": "basefee","type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [{"name": "blockNumber","type": "uint256"}],
        "name": "getBlockHash",
        "outputs": [{"name": "blockHash","type": "bytes32"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "getBlockNumber",
        "outputs": [{"name": "blockNumber","type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "getChainId",
        "outputs": [{"name": "chainid","type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "getCurrentBlockCoinbase",
        "outputs": [{"name": "coinbase","type": "address"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "getCurrentBlockDifficulty",
        "outputs": [{"name": "difficulty","type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "getCurrentBlockGasLimit",
        "outputs": [{"name": "gaslimit","type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "getCurrentBlockTimestamp",
        "outputs": [{"name": "timestamp","type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [{"name": "addr","type": "address"}],
        "name": "getEthBalance",
        "outputs": [{"name": "balance","type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "getLastBlockHash",
        "outputs": [{"name": "blockHash","type": "bytes32"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [{"name": "requireSuccess","type": "bool"},{"components": [{"name": "target","type": "address"},{"name": "callData","type": "bytes"}],"name": "calls","type": "tuple[]"}],
        "name": "tryAggregate",
        "outputs": [{"components": [{"name": "success","type": "bool"},{"name": "returnData","type": "bytes"}],"name": "returnData","type": "tuple[]"}],
        "stateMutability": "payable",
        "type": "function"
    },
    {
        "inputs": [{"name": "requireSuccess","type": "bool"},{"components": [{"name": "target","type": "address"},{"name": "callData","type": "bytes"}],"name": "calls","type": "tuple[]"}],
        "name": "tryBlockAndAggregate",
        "outputs": [{"name": "blockNumber","type": "uint256"},{"name": "blockHash","type": "bytes32"},{"components": [{"name": "success","type": "bool"},{"name": "returnData","type": "bytes"}],"name": "returnData","type": "tuple[]"}],
        "stateMutability": "payable",
        "type": "function"
    }
]


__VERSION__ = "0.1.2"


__ERC20_ABI__ = json.loads("""[
    {"constant":true,"inputs":[],"name":"name","outputs":[{"name":"","type":"string"}],"type":"function"},
    {"constant":true,"inputs":[],"name":"symbol","outputs":[{"name":"","type":"string"}],"type":"function"},
    {"constant":true,"inputs":[],"name":"decimals","outputs":[{"name":"","type":"uint8"}],"type":"function"},
    {"constant":true,"inputs":[],"name":"totalSupply","outputs":[{"name":"","type":"uint256"}],"type":"function"},
    {"constant":true,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"","type":"uint256"}],"type":"function"},
    {"constant":false,"inputs":[{"name":"_to","type":"address"},{"name":"_value","type":"uint256"}],"name":"transfer","outputs":[{"name":"","type":"bool"}],"type":"function"},
    {"constant":false,"inputs":[{"name":"_spender","type":"address"},{"name":"_value","type":"uint256"}],"name":"approve","outputs":[{"name":"","type":"bool"}],"type":"function"},
    {"constant":true,"inputs":[{"name":"_owner","type":"address"},{"name":"_spender","type":"address"}],"name":"allowance","outputs":[{"name":"","type":"uint256"}],"type":"function"},
    {"constant":false,"inputs":[{"name":"_from","type":"address"},{"name":"_to","type":"address"},{"name":"_value","type":"uint256"}],"name":"transferFrom","outputs":[{"name":"", "type":"bool"}],"type":"function"}
]""")

ORBISPAY_CONTRACT_ADDRESS = {
  8453: '0x455a2aAa7c7DcD413F05d56462dA13522E43d0D1',
  56: '0x455a2aAa7c7DcD413F05d56462dA13522E43d0D1',
  42161: '0x455a2aAa7c7DcD413F05d56462dA13522E43d0D1',
  10: '0x455a2aAa7c7DcD413F05d56462dA13522E43d0D1'
}
ERC20_SIGNATURES = {
    # ── ERC20 standard ──────────────────────────────────────────────────────
    "0xa9059cbb": ("Transfer",        "Sending tokens to recipient"),
    "0x095ea7b3": ("Approve",         "Allowing contract to use your tokens"),
    "0x23b872dd": ("TransferFrom",    "Contract moves tokens on your behalf"),
    # ── Uniswap V2 / PancakeSwap V2 ─────────────────────────────────────────
    "0x7ff36ab5": ("Swap ETH→Tokens", "Buying tokens with native BNB/ETH"),
    "0x18cbafe5": ("Swap Tokens→ETH", "Selling tokens for native BNB/ETH"),
    "0x38ed1739": ("Swap Tokens→Tokens","Exchanging fixed amount of tokens"),
    "0x791ac947": ("Swap Tokens→ETH", "Selling exact tokens for BNB/ETH"),
    "0xfb3bdb41": ("Swap ETH→Exact",  "Buying exact token amount with ETH"),
    "0x5c11d795": ("Swap+Fee",        "Swap with fee-on-transfer tokens"),
    # ── Uniswap V3 ──────────────────────────────────────────────────────────
    "0x414bf389": ("Swap V3 Exact In",  "Uniswap V3 single-hop exact input"),
    "0xdb3e2198": ("Swap V3 Exact Out", "Uniswap V3 single-hop exact output"),
    "0xc04b8d59": ("Swap V3 Multi In",  "Uniswap V3 multi-hop exact input"),
    "0xf28c0498": ("Swap V3 Multi Out", "Uniswap V3 multi-hop exact output"),
    # ── Uniswap Universal Router (V3/V4) ────────────────────────────────────
    "0x3593564c": ("Universal Swap",  "Uniswap Universal Router execute()"),
    "0x24856bc3": ("Universal Swap",  "Uniswap Universal Router execute() v2"),
    # ── Liquidity ────────────────────────────────────────────────────────────
    "0xe8e33700": ("Add Liquidity",    "Providing assets to a V2 pool"),
    "0xf305d719": ("Add Liquidity ETH","Providing ETH + token to a V2 pool"),
    "0xbaa2abde": ("Remove Liquidity", "Withdrawing assets from a pool"),
    "0x02751cec": ("Remove Liq ETH",   "Withdrawing ETH from a pool"),
    # ── Misc ─────────────────────────────────────────────────────────────────
    "0xd0e30db0": ("Wrap ETH",   "Wrapping native ETH → WETH"),
    "0x2e1a7d4d": ("Unwrap ETH", "Unwrapping WETH → native ETH"),
    "0x70a08231": ("balanceOf",  "Reading token balance"),
    "0xdd62ed3e": ("allowance",  "Reading token allowance"),
}
ORBISPAY_DOMAIN_ABI = json.loads("""[
                                   [
	{
		"inputs": [],
		"stateMutability": "nonpayable",
		"type": "constructor"
	},
	{
		"anonymous": false,
		"inputs": [
			{
				"indexed": true,
				"internalType": "string",
				"name": "domain",
				"type": "string"
			},
			{
				"indexed": true,
				"internalType": "address",
				"name": "owner",
				"type": "address"
			},
			{
				"indexed": false,
				"internalType": "uint256",
				"name": "expiresAt",
				"type": "uint256"
			}
		],
		"name": "DomainRegistered",
		"type": "event"
	},
	{
		"anonymous": false,
		"inputs": [
			{
				"indexed": true,
				"internalType": "string",
				"name": "domain",
				"type": "string"
			}
		],
		"name": "DomainReleased",
		"type": "event"
	},
	{
		"anonymous": false,
		"inputs": [
			{
				"indexed": true,
				"internalType": "string",
				"name": "domain",
				"type": "string"
			},
			{
				"indexed": true,
				"internalType": "address",
				"name": "owner",
				"type": "address"
			},
			{
				"indexed": false,
				"internalType": "uint256",
				"name": "newExpiresAt",
				"type": "uint256"
			}
		],
		"name": "DomainRenewed",
		"type": "event"
	},
	{
		"anonymous": false,
		"inputs": [
			{
				"indexed": true,
				"internalType": "string",
				"name": "domain",
				"type": "string"
			},
			{
				"indexed": true,
				"internalType": "address",
				"name": "from",
				"type": "address"
			},
			{
				"indexed": true,
				"internalType": "address",
				"name": "to",
				"type": "address"
			}
		],
		"name": "DomainTransferred",
		"type": "event"
	},
	{
		"anonymous": false,
		"inputs": [
			{
				"indexed": false,
				"internalType": "uint256",
				"name": "price3chars",
				"type": "uint256"
			},
			{
				"indexed": false,
				"internalType": "uint256",
				"name": "price4chars",
				"type": "uint256"
			},
			{
				"indexed": false,
				"internalType": "uint256",
				"name": "price5plus",
				"type": "uint256"
			}
		],
		"name": "PricesUpdated",
		"type": "event"
	},
	{
		"anonymous": false,
		"inputs": [
			{
				"indexed": true,
				"internalType": "string",
				"name": "domain",
				"type": "string"
			},
			{
				"indexed": false,
				"internalType": "string",
				"name": "newRecord",
				"type": "string"
			}
		],
		"name": "RecordUpdated",
		"type": "event"
	},
	{
		"anonymous": false,
		"inputs": [
			{
				"indexed": true,
				"internalType": "address",
				"name": "to",
				"type": "address"
			},
			{
				"indexed": false,
				"internalType": "uint256",
				"name": "amount",
				"type": "uint256"
			}
		],
		"name": "Withdrawal",
		"type": "event"
	},
	{
		"inputs": [],
		"name": "SUFFIX",
		"outputs": [
			{
				"internalType": "string",
				"name": "",
				"type": "string"
			}
		],
		"stateMutability": "view",
		"type": "function"
	},
	{
		"inputs": [],
		"name": "YEAR",
		"outputs": [
			{
				"internalType": "uint256",
				"name": "",
				"type": "uint256"
			}
		],
		"stateMutability": "view",
		"type": "function"
	},
	{
		"inputs": [
			{
				"internalType": "string",
				"name": "label",
				"type": "string"
			},
			{
				"internalType": "uint256",
				"name": "timeRent",
				"type": "uint256"
			}
		],
		"name": "calculateFee",
		"outputs": [
			{
				"internalType": "uint256",
				"name": "",
				"type": "uint256"
			}
		],
		"stateMutability": "view",
		"type": "function"
	},
	{
		"inputs": [],
		"name": "contractOwner",
		"outputs": [
			{
				"internalType": "address",
				"name": "",
				"type": "address"
			}
		],
		"stateMutability": "view",
		"type": "function"
	},
	{
		"inputs": [
			{
				"internalType": "string",
				"name": "label",
				"type": "string"
			}
		],
		"name": "getDomain",
		"outputs": [
			{
				"internalType": "address",
				"name": "owner",
				"type": "address"
			},
			{
				"internalType": "string",
				"name": "record",
				"type": "string"
			},
			{
				"internalType": "uint256",
				"name": "registeredAt",
				"type": "uint256"
			},
			{
				"internalType": "uint256",
				"name": "expiresAt",
				"type": "uint256"
			},
			{
				"internalType": "bool",
				"name": "transferLocked",
				"type": "bool"
			},
			{
				"internalType": "bool",
				"name": "active",
				"type": "bool"
			}
		],
		"stateMutability": "view",
		"type": "function"
	},
	{
		"inputs": [
			{
				"internalType": "string",
				"name": "label",
				"type": "string"
			}
		],
		"name": "getFullName",
		"outputs": [
			{
				"internalType": "string",
				"name": "",
				"type": "string"
			}
		],
		"stateMutability": "pure",
		"type": "function"
	},
	{
		"inputs": [
			{
				"internalType": "address",
				"name": "owner",
				"type": "address"
			}
		],
		"name": "getOwnerDomains",
		"outputs": [
			{
				"internalType": "string[]",
				"name": "",
				"type": "string[]"
			}
		],
		"stateMutability": "view",
		"type": "function"
	},
	{
		"inputs": [
			{
				"internalType": "string",
				"name": "label",
				"type": "string"
			}
		],
		"name": "isAvailable",
		"outputs": [
			{
				"internalType": "bool",
				"name": "",
				"type": "bool"
			}
		],
		"stateMutability": "view",
		"type": "function"
	},
	{
		"inputs": [],
		"name": "price3chars",
		"outputs": [
			{
				"internalType": "uint256",
				"name": "",
				"type": "uint256"
			}
		],
		"stateMutability": "view",
		"type": "function"
	},
	{
		"inputs": [],
		"name": "price4chars",
		"outputs": [
			{
				"internalType": "uint256",
				"name": "",
				"type": "uint256"
			}
		],
		"stateMutability": "view",
		"type": "function"
	},
	{
		"inputs": [],
		"name": "price5plus",
		"outputs": [
			{
				"internalType": "uint256",
				"name": "",
				"type": "uint256"
			}
		],
		"stateMutability": "view",
		"type": "function"
	},
	{
		"inputs": [
			{
				"internalType": "string",
				"name": "label",
				"type": "string"
			},
			{
				"internalType": "string",
				"name": "record",
				"type": "string"
			},
			{
				"internalType": "uint256",
				"name": "timeRent",
				"type": "uint256"
			}
		],
		"name": "register",
		"outputs": [],
		"stateMutability": "payable",
		"type": "function"
	},
	{
		"inputs": [
			{
				"internalType": "string",
				"name": "label",
				"type": "string"
			}
		],
		"name": "release",
		"outputs": [],
		"stateMutability": "nonpayable",
		"type": "function"
	},
	{
		"inputs": [
			{
				"internalType": "string",
				"name": "label",
				"type": "string"
			},
			{
				"internalType": "uint256",
				"name": "timeRent",
				"type": "uint256"
			}
		],
		"name": "renew",
		"outputs": [],
		"stateMutability": "payable",
		"type": "function"
	},
	{
		"inputs": [
			{
				"internalType": "uint256",
				"name": "_price3chars",
				"type": "uint256"
			},
			{
				"internalType": "uint256",
				"name": "_price4chars",
				"type": "uint256"
			},
			{
				"internalType": "uint256",
				"name": "_price5plus",
				"type": "uint256"
			}
		],
		"name": "setPrices",
		"outputs": [],
		"stateMutability": "nonpayable",
		"type": "function"
	},
	{
		"inputs": [
			{
				"internalType": "string",
				"name": "label",
				"type": "string"
			},
			{
				"internalType": "bool",
				"name": "locked",
				"type": "bool"
			}
		],
		"name": "setTransferLock",
		"outputs": [],
		"stateMutability": "nonpayable",
		"type": "function"
	},
	{
		"inputs": [
			{
				"internalType": "string",
				"name": "label",
				"type": "string"
			},
			{
				"internalType": "address",
				"name": "to",
				"type": "address"
			}
		],
		"name": "transfer",
		"outputs": [],
		"stateMutability": "nonpayable",
		"type": "function"
	},
	{
		"inputs": [
			{
				"internalType": "string",
				"name": "label",
				"type": "string"
			},
			{
				"internalType": "string",
				"name": "newRecord",
				"type": "string"
			}
		],
		"name": "updateRecord",
		"outputs": [],
		"stateMutability": "nonpayable",
		"type": "function"
	},
	{
		"inputs": [
			{
				"internalType": "address payable",
				"name": "to",
				"type": "address"
			},
			{
				"internalType": "uint256",
				"name": "amount",
				"type": "uint256"
			}
		],
		"name": "withdraw",
		"outputs": [],
		"stateMutability": "nonpayable",
		"type": "function"
	},
	{
		"stateMutability": "payable",
		"type": "receive"
	}
]]""")
ORBISPAY_CHEQUES_ABI = json.loads(""" [
			{
				"inputs": [
					{
						"internalType": "address",
						"name": "_trassary",
						"type": "address"
					}
				],
				"stateMutability": "nonpayable",
				"type": "constructor"
			},
			{
				"anonymous": false,
				"inputs": [
					{
						"indexed": true,
						"internalType": "bytes32",
						"name": "id",
						"type": "bytes32"
					}
				],
				"name": "ChequeClaimed",
				"type": "event"
			},
			{
				"anonymous": false,
				"inputs": [
					{
						"indexed": true,
						"internalType": "bytes32",
						"name": "id",
						"type": "bytes32"
					}
				],
				"name": "ChequeCreated",
				"type": "event"
			},
			{
				"inputs": [
					{
						"internalType": "bytes32",
						"name": "chequeId",
						"type": "bytes32"
					}
				],
				"name": "CashOutMultiCheque",
				"outputs": [],
				"stateMutability": "nonpayable",
				"type": "function"
			},
			{
				"inputs": [
					{
						"internalType": "bytes32",
						"name": "chequeId",
						"type": "bytes32"
					}
				],
				"name": "CashOutNativeCheque",
				"outputs": [],
				"stateMutability": "nonpayable",
				"type": "function"
			},
			{
				"inputs": [
					{
						"internalType": "bytes32",
						"name": "_id",
						"type": "bytes32"
					}
				],
				"name": "CashOutSwapCheque",
				"outputs": [],
				"stateMutability": "nonpayable",
				"type": "function"
			},
			{
				"inputs": [
					{
						"internalType": "bytes32",
						"name": "id",
						"type": "bytes32"
					}
				],
				"name": "CashOutTokenCheque",
				"outputs": [],
				"stateMutability": "nonpayable",
				"type": "function"
			},
			{
				"inputs": [
					{
						"internalType": "bytes32",
						"name": "chequeId",
						"type": "bytes32"
					}
				],
				"name": "RefundNativeCheque",
				"outputs": [],
				"stateMutability": "nonpayable",
				"type": "function"
			},
			{
				"inputs": [
					{
						"internalType": "bytes32",
						"name": "chequeId",
						"type": "bytes32"
					}
				],
				"name": "RefundMultiCheque",
				"outputs": [],
				"stateMutability": "nonpayable",
				"type": "function"
			},
			{
				"inputs": [
					{
						"internalType": "bytes32",
						"name": "id",
						"type": "bytes32"
					}
				],
				"name": "RefundTokenCheque",
				"outputs": [],
				"stateMutability": "nonpayable",
				"type": "function"
			},
			{
				"inputs": [
					{
						"internalType": "bytes32",
						"name": "_id",
						"type": "bytes32"
					}
				],
				"name": "RefundSwapCheque",
				"outputs": [],
				"stateMutability": "nonpayable",
				"type": "function"
			},
			{
				"inputs": [],
				"name": "FEE_DENOMINATOR",
				"outputs": [
					{
						"internalType": "uint256",
						"name": "",
						"type": "uint256"
					}
				],
				"stateMutability": "view",
				"type": "function"
			},
			{
				"inputs": [
					{
						"internalType": "bytes32",
						"name": "chequeId",
						"type": "bytes32"
					},
					{
						"internalType": "address",
						"name": "tokenAddr",
						"type": "address"
					},
					{
						"internalType": "uint256",
						"name": "amount",
						"type": "uint256"
					},
					{
						"internalType": "address payable[]",
						"name": "to",
						"type": "address[]"
					}
				],
				"name": "InitCheque",
				"outputs": [
					{
						"internalType": "bytes32",
						"name": "",
						"type": "bytes32"
					}
				],
				"stateMutability": "payable",
				"type": "function"
			},
			{
				"inputs": [
					{
						"internalType": "bytes32",
						"name": "chequeId",
						"type": "bytes32"
					},
					{
						"internalType": "address payable[]",
						"name": "_to",
						"type": "address[]"
					}
				],
				"name": "InitMultiCheque",
				"outputs": [
					{
						"internalType": "bytes32",
						"name": "",
						"type": "bytes32"
					}
				],
				"stateMutability": "payable",
				"type": "function"
			},
			{
				"inputs": [
					{
						"internalType": "bytes32",
						"name": "chequeId",
						"type": "bytes32"
					},
					{
						"internalType": "address payable",
						"name": "_to",
						"type": "address"
					}
				],
				"name": "InitNativeCheque",
				"outputs": [
					{
						"internalType": "bytes32",
						"name": "",
						"type": "bytes32"
					}
				],
				"stateMutability": "payable",
				"type": "function"
			},
			{
				"inputs": [
					{
						"internalType": "bytes32",
						"name": "chequeId",
						"type": "bytes32"
					},
					{
						"internalType": "address",
						"name": "_reciever",
						"type": "address"
					},
					{
						"internalType": "address",
						"name": "_tokenIn",
						"type": "address"
					},
					{
						"internalType": "uint256",
						"name": "_amountIn",
						"type": "uint256"
					},
					{
						"internalType": "address",
						"name": "_tokenOut",
						"type": "address"
					},
					{
						"internalType": "uint256",
						"name": "_amountOut",
						"type": "uint256"
					}
				],
				"name": "InitSwapCheque",
				"outputs": [
					{
						"internalType": "bytes32",
						"name": "",
						"type": "bytes32"
					}
				],
				"stateMutability": "nonpayable",
				"type": "function"
			},
			{
				"inputs": [
					{
						"internalType": "bytes32",
						"name": "chequeId",
						"type": "bytes32"
					},
					{
						"internalType": "address",
						"name": "tokenAddr",
						"type": "address"
					},
					{
						"internalType": "uint256",
						"name": "amount",
						"type": "uint256"
					},
					{
						"internalType": "address payable",
						"name": "to",
						"type": "address"
					}
				],
				"name": "InitTokenCheque",
				"outputs": [
					{
						"internalType": "bytes32",
						"name": "",
						"type": "bytes32"
					}
				],
				"stateMutability": "nonpayable",
				"type": "function"
			},
			{
				"inputs": [],
				"name": "MAX_BPS",
				"outputs": [
					{
						"internalType": "uint256",
						"name": "",
						"type": "uint256"
					}
				],
				"stateMutability": "view",
				"type": "function"
			},
			{
				"inputs": [],
				"name": "MULTI_BPS",
				"outputs": [
					{
						"internalType": "uint256",
						"name": "",
						"type": "uint256"
					}
				],
				"stateMutability": "view",
				"type": "function"
			},
			{
				"inputs": [],
				"name": "NATIVE_BPS",
				"outputs": [
					{
						"internalType": "uint256",
						"name": "",
						"type": "uint256"
					}
				],
				"stateMutability": "view",
				"type": "function"
			},
			{
				"inputs": [],
				"name": "PER_ADDRESS_FEE",
				"outputs": [
					{
						"internalType": "uint256",
						"name": "",
						"type": "uint256"
					}
				],
				"stateMutability": "view",
				"type": "function"
			},
			{
				"inputs": [],
				"name": "SWAP_BPS",
				"outputs": [
					{
						"internalType": "uint256",
						"name": "",
						"type": "uint256"
					}
				],
				"stateMutability": "view",
				"type": "function"
			},
			{
				"inputs": [],
				"name": "TOKEN_BPS",
				"outputs": [
					{
						"internalType": "uint256",
						"name": "",
						"type": "uint256"
					}
				],
				"stateMutability": "view",
				"type": "function"
			},
			{
				"inputs": [
					{
						"internalType": "bool",
						"name": "_active",
						"type": "bool"
					}
				],
				"name": "activated",
				"outputs": [],
				"stateMutability": "nonpayable",
				"type": "function"
			},
			{
				"inputs": [
					{
						"internalType": "address",
						"name": "newOwner",
						"type": "address"
					}
				],
				"name": "changeOwner",
				"outputs": [],
				"stateMutability": "nonpayable",
				"type": "function"
			},
			{
				"inputs": [],
				"name": "collectedFees",
				"outputs": [
					{
						"internalType": "uint256",
						"name": "",
						"type": "uint256"
					}
				],
				"stateMutability": "view",
				"type": "function"
			},
			{
				"inputs": [],
				"name": "getBalance",
				"outputs": [
					{
						"internalType": "uint256",
						"name": "",
						"type": "uint256"
					}
				],
				"stateMutability": "view",
				"type": "function"
			},
			{
				"inputs": [],
				"name": "getCollectedFee",
				"outputs": [
					{
						"internalType": "uint256",
						"name": "",
						"type": "uint256"
					}
				],
				"stateMutability": "view",
				"type": "function"
			},
			{
				"inputs": [],
				"name": "getFeeSchedule",
				"outputs": [
					{
						"internalType": "uint256",
						"name": "nativeBps",
						"type": "uint256"
					},
					{
						"internalType": "uint256",
						"name": "multiBps",
						"type": "uint256"
					},
					{
						"internalType": "uint256",
						"name": "tokenBps",
						"type": "uint256"
					},
					{
						"internalType": "uint256",
						"name": "swapBps",
						"type": "uint256"
					},
					{
						"internalType": "uint256",
						"name": "denominator",
						"type": "uint256"
					}
				],
				"stateMutability": "view",
				"type": "function"
			},
			{
				"inputs": [
					{
						"internalType": "bytes32",
						"name": "id",
						"type": "bytes32"
					},
					{
						"internalType": "address",
						"name": "from",
						"type": "address"
					}
				],
				"name": "getMultiChequeInfo",
				"outputs": [
					{
						"internalType": "uint256",
						"name": "amount",
						"type": "uint256"
					},
					{
						"internalType": "address payable[]",
						"name": "to",
						"type": "address[]"
					},
					{
						"internalType": "bool",
						"name": "claimed",
						"type": "bool"
					}
				],
				"stateMutability": "view",
				"type": "function"
			},
			{
				"inputs": [
					{
						"internalType": "bytes32",
						"name": "id",
						"type": "bytes32"
					}
				],
				"name": "getNativeChequeInfo",
				"outputs": [
					{
						"internalType": "address payable",
						"name": "to",
						"type": "address"
					},
					{
						"internalType": "uint256",
						"name": "amount",
						"type": "uint256"
					},
					{
						"internalType": "bool",
						"name": "claimed",
						"type": "bool"
					}
				],
				"stateMutability": "view",
				"type": "function"
			},
			{
				"inputs": [],
				"name": "getOwner",
				"outputs": [
					{
						"internalType": "address",
						"name": "",
						"type": "address"
					}
				],
				"stateMutability": "view",
				"type": "function"
			},
			{
				"inputs": [],
				"name": "getProtocolStats",
				"outputs": [
					{
						"internalType": "uint256",
						"name": "balanceWei",
						"type": "uint256"
					},
					{
						"internalType": "uint256",
						"name": "collectedFeesWei",
						"type": "uint256"
					},
					{
						"internalType": "uint256",
						"name": "nativeBps",
						"type": "uint256"
					},
					{
						"internalType": "uint256",
						"name": "multiBps",
						"type": "uint256"
					},
					{
						"internalType": "uint256",
						"name": "tokenBps",
						"type": "uint256"
					},
					{
						"internalType": "uint256",
						"name": "swapBps",
						"type": "uint256"
					},
					{
						"internalType": "uint256",
						"name": "feeDenominator",
						"type": "uint256"
					},
					{
						"internalType": "address",
						"name": "treasuryAddress",
						"type": "address"
					},
					{
						"internalType": "address",
						"name": "ownerAddress",
						"type": "address"
					},
					{
						"internalType": "bool",
						"name": "active",
						"type": "bool"
					},
					{
						"internalType": "uint256",
						"name": "nextWithdrawTimestamp",
						"type": "uint256"
					}
				],
				"stateMutability": "view",
				"type": "function"
			},
			{
				"inputs": [
					{
						"internalType": "bytes32",
						"name": "id",
						"type": "bytes32"
					}
				],
				"name": "getSwapDetail",
				"outputs": [
					{
						"internalType": "address",
						"name": "tokenIn",
						"type": "address"
					},
					{
						"internalType": "uint256",
						"name": "amountIn",
						"type": "uint256"
					},
					{
						"internalType": "address",
						"name": "tokenOut",
						"type": "address"
					},
					{
						"internalType": "uint256",
						"name": "amountOut",
						"type": "uint256"
					},
					{
						"internalType": "address",
						"name": "spender",
						"type": "address"
					},
					{
						"internalType": "address",
						"name": "receiver",
						"type": "address"
					},
					{
						"internalType": "bool",
						"name": "claimed",
						"type": "bool"
					}
				],
				"stateMutability": "view",
				"type": "function"
			},
			{
				"inputs": [
					{
						"internalType": "bytes32",
						"name": "id",
						"type": "bytes32"
					}
				],
				"name": "getTokenChequeDetail",
				"outputs": [
					{
						"internalType": "address",
						"name": "spender",
						"type": "address"
					},
					{
						"internalType": "address",
						"name": "token",
						"type": "address"
					},
					{
						"internalType": "uint256",
						"name": "amount",
						"type": "uint256"
					},
					{
						"internalType": "address",
						"name": "receiver",
						"type": "address"
					},
					{
						"internalType": "bool",
						"name": "claimed",
						"type": "bool"
					}
				],
				"stateMutability": "view",
				"type": "function"
			},
			{
				"inputs": [],
				"name": "getTreasery",
				"outputs": [
					{
						"internalType": "address",
						"name": "",
						"type": "address"
					}
				],
				"stateMutability": "view",
				"type": "function"
			},
			{
				"inputs": [],
				"name": "isActive",
				"outputs": [
					{
						"internalType": "bool",
						"name": "",
						"type": "bool"
					}
				],
				"stateMutability": "view",
				"type": "function"
			},
			{
				"inputs": [],
				"name": "nextAvailableWithdraw",
				"outputs": [
					{
						"internalType": "uint256",
						"name": "timestamp",
						"type": "uint256"
					}
				],
				"stateMutability": "view",
				"type": "function"
			},
			{
				"inputs": [],
				"name": "owner",
				"outputs": [
					{
						"internalType": "address",
						"name": "",
						"type": "address"
					}
				],
				"stateMutability": "view",
				"type": "function"
			},
			{
				"inputs": [
					{
						"internalType": "uint256",
						"name": "newBps",
						"type": "uint256"
					}
				],
				"name": "setMultiBps",
				"outputs": [],
				"stateMutability": "nonpayable",
				"type": "function"
			},
			{
				"inputs": [
					{
						"internalType": "uint256",
						"name": "newBps",
						"type": "uint256"
					}
				],
				"name": "setNativeBps",
				"outputs": [],
				"stateMutability": "nonpayable",
				"type": "function"
			},
			{
				"inputs": [
					{
						"internalType": "uint256",
						"name": "newBps",
						"type": "uint256"
					}
				],
				"name": "setSwapBps",
				"outputs": [],
				"stateMutability": "nonpayable",
				"type": "function"
			},
			{
				"inputs": [
					{
						"internalType": "uint256",
						"name": "newBps",
						"type": "uint256"
					}
				],
				"name": "setTokenBps",
				"outputs": [],
				"stateMutability": "nonpayable",
				"type": "function"
			},
			{
				"inputs": [
					{
						"internalType": "address",
						"name": "_treaseryAddress",
						"type": "address"
					}
				],
				"name": "setTreasery",
				"outputs": [],
				"stateMutability": "nonpayable",
				"type": "function"
			},
			{
				"inputs": [
					{
						"internalType": "bytes32",
						"name": "",
						"type": "bytes32"
					}
				],
				"name": "swapCheques",
				"outputs": [
					{
						"internalType": "address",
						"name": "spender",
						"type": "address"
					},
					{
						"internalType": "address",
						"name": "receiver",
						"type": "address"
					},
					{
						"internalType": "address",
						"name": "tokenIn",
						"type": "address"
					},
					{
						"internalType": "uint256",
						"name": "amountIn",
						"type": "uint256"
					},
					{
						"internalType": "address",
						"name": "tokenOut",
						"type": "address"
					},
					{
						"internalType": "uint256",
						"name": "amountOut",
						"type": "uint256"
					},
					{
						"internalType": "bool",
						"name": "claimed",
						"type": "bool"
					}
				],
				"stateMutability": "view",
				"type": "function"
			},
			{
				"inputs": [],
				"name": "treasery",
				"outputs": [
					{
						"internalType": "address",
						"name": "",
						"type": "address"
					}
				],
				"stateMutability": "view",
				"type": "function"
			},
			{
				"inputs": [
					{
						"internalType": "uint256",
						"name": "amount",
						"type": "uint256"
					},
					{
						"internalType": "address",
						"name": "_to",
						"type": "address"
					}
				],
				"name": "withdrawAmount",
				"outputs": [],
				"stateMutability": "nonpayable",
				"type": "function"
			},
			{
				"inputs": [],
				"name": "withdrawFees",
				"outputs": [],
				"stateMutability": "nonpayable",
				"type": "function"
			}
		]""")
__SHADOWPAY_ABI__ERC721__ = json.loads("""[]""")
__SHADOWPAY_ABI__INVOISE__ = json.loads("""[
  {
    "inputs": [
      { "internalType": "address", "name": "_treasury", "type": "address" },
      { "internalType": "uint256", "name": "_feeBps", "type": "uint256" }
    ],
    "stateMutability": "nonpayable",
    "type": "constructor"
  },
  {
    "inputs": [
      { "internalType": "address", "name": "token", "type": "address" }
    ],
    "name": "SafeERC20FailedOperation",
    "type": "error"
  },
  {
    "anonymous": false,
    "inputs": [
      { "indexed": true, "internalType": "bytes32", "name": "id", "type": "bytes32" }
    ],
    "name": "InvoiceCanceled",
    "type": "event"
  },
  {
    "anonymous": false,
    "inputs": [
      { "indexed": true, "internalType": "bytes32", "name": "id", "type": "bytes32" },
      { "indexed": true, "internalType": "address", "name": "merchant", "type": "address" },
      { "indexed": false, "internalType": "address", "name": "token", "type": "address" },
      { "indexed": false, "internalType": "uint256", "name": "amount", "type": "uint256" }
    ],
    "name": "InvoiceCreated",
    "type": "event"
  },
  {
    "anonymous": false,
    "inputs": [
      { "indexed": true, "internalType": "bytes32", "name": "id", "type": "bytes32" },
      { "indexed": true, "internalType": "address", "name": "payer", "type": "address" },
      { "indexed": false, "internalType": "uint256", "name": "amount", "type": "uint256" },
      { "indexed": false, "internalType": "uint256", "name": "tip", "type": "uint256" },
      { "indexed": false, "internalType": "uint256", "name": "fee", "type": "uint256" },
      { "indexed": false, "internalType": "uint256", "name": "toMerchant", "type": "uint256" }
    ],
    "name": "InvoicePaid",
    "type": "event"
  },
  {
    "inputs": [],
    "name": "FEE_DENOMINATOR",
    "outputs": [
      { "internalType": "uint256", "name": "", "type": "uint256" }
    ],
    "stateMutability": "view",
    "type": "function"
  },
  {
    "inputs": [
      { "internalType": "bytes32", "name": "id", "type": "bytes32" }
    ],
    "name": "cancelInvoice",
    "outputs": [],
    "stateMutability": "nonpayable",
    "type": "function"
  },
  {
    "inputs": [
      { "internalType": "address", "name": "merchant", "type": "address" },
      { "internalType": "address", "name": "token", "type": "address" },
      { "internalType": "uint128", "name": "amount", "type": "uint128" },
      { "internalType": "uint64", "name": "dueAt", "type": "uint64" },
      { "internalType": "address", "name": "payer", "type": "address" },
      { "internalType": "bytes32", "name": "salt", "type": "bytes32" }
    ],
    "name": "computeId",
    "outputs": [
      { "internalType": "bytes32", "name": "", "type": "bytes32" }
    ],
    "stateMutability": "pure",
    "type": "function"
  },
  {
    "inputs": [
      { "internalType": "bytes32", "name": "id", "type": "bytes32" },
      { "internalType": "address", "name": "merchant", "type": "address" },
      { "internalType": "address", "name": "token", "type": "address" },
      { "internalType": "uint128", "name": "amount", "type": "uint128" },
      { "internalType": "uint64", "name": "dueAt", "type": "uint64" },
      { "internalType": "address", "name": "payer", "type": "address" },
      { "internalType": "bool", "name": "allowTips", "type": "bool" },
      { "internalType": "bool", "name": "allowPartial", "type": "bool" }
    ],
    "name": "createInvoice",
    "outputs": [],
    "stateMutability": "payable",
    "type": "function"
  },
  {
    "inputs": [
      { "internalType": "bytes32", "name": "", "type": "bytes32" }
    ],
    "name": "invoices",
    "outputs": [
      { "internalType": "address", "name": "merchant", "type": "address" },
      { "internalType": "address", "name": "token", "type": "address" },
      { "internalType": "uint128", "name": "amount", "type": "uint128" },
      { "internalType": "uint128", "name": "paid", "type": "uint128" },
      { "internalType": "uint64", "name": "createdAt", "type": "uint64" },
      { "internalType": "uint64", "name": "dueAt", "type": "uint64" },
      { "internalType": "address", "name": "payer", "type": "address" },
      { "internalType": "bool", "name": "allowTips", "type": "bool" },
      { "internalType": "bool", "name": "allowPartial", "type": "bool" },
      { "internalType": "bool", "name": "canceled", "type": "bool" }
    ],
    "stateMutability": "view",
    "type": "function"
  },
  {
    "inputs": [
      {
        "components": [
          { "internalType": "address", "name": "merchant", "type": "address" },
          { "internalType": "address", "name": "token", "type": "address" },
          { "internalType": "uint128", "name": "amount", "type": "uint128" },
          { "internalType": "uint128", "name": "paid", "type": "uint128" },
          { "internalType": "uint64", "name": "createdAt", "type": "uint64" },
          { "internalType": "uint64", "name": "dueAt", "type": "uint64" },
          { "internalType": "address", "name": "payer", "type": "address" },
          { "internalType": "bool", "name": "allowTips", "type": "bool" },
          { "internalType": "bool", "name": "allowPartial", "type": "bool" },
          { "internalType": "bool", "name": "canceled", "type": "bool" }
        ],
        "internalType": "struct InvoiceHub.Invoice",
        "name": "inv",
        "type": "tuple"
      }
    ],
    "name": "isSettled",
    "outputs": [
      { "internalType": "bool", "name": "", "type": "bool" }
    ],
    "stateMutability": "pure",
    "type": "function"
  },
  {
    "inputs": [
      { "internalType": "bytes32", "name": "id", "type": "bytes32" },
      { "internalType": "uint256", "name": "amount", "type": "uint256" },
      { "internalType": "uint256", "name": "tip", "type": "uint256" }
    ],
    "name": "payERC20",
    "outputs": [],
    "stateMutability": "nonpayable",
    "type": "function"
  },
  {
    "inputs": [
      { "internalType": "bytes32", "name": "id", "type": "bytes32" },
      { "internalType": "uint256", "name": "amount", "type": "uint256" },
      { "internalType": "uint256", "name": "tip", "type": "uint256" }
    ],
    "name": "payETH",
    "outputs": [],
    "stateMutability": "payable",
    "type": "function"
  },
  {
    "inputs": [{ "internalType": "bytes32", "name": "id", "type": "bytes32" }],
    "name": "getInvoice",
    "outputs": [{"components": [
      { "internalType": "address", "name": "merchant", "type": "address" },
      { "internalType": "address", "name": "token", "type": "address" },
      { "internalType": "uint128", "name": "amount", "type": "uint128" },
      { "internalType": "bool", "name": "fact_paid", "type": "bool" },
      { "internalType": "uint128", "name": "paid", "type": "uint128" },
      { "internalType": "uint64", "name": "createdAt", "type": "uint64" },
      { "internalType": "uint64", "name": "dueAt", "type": "uint64" },
      { "internalType": "address", "name": "payer", "type": "address" },
      { "internalType": "bool", "name": "allowTips", "type": "bool" },
      { "internalType": "bool", "name": "allowPartial", "type": "bool" },
      { "internalType": "bool", "name": "baseFeePaid", "type": "bool" },
      { "internalType": "bool", "name": "canceled", "type": "bool" },
      { "internalType": "uint256", "name": "count", "type": "uint256" }
    ], "internalType": "struct InvoiceHub.Invoice", "name": "inv", "type": "tuple"}],
    "stateMutability": "view",
    "type": "function"
  },
  {
    "inputs": [],
    "name": "getFee",
    "outputs": [
      { "internalType": "uint256", "name": "", "type": "uint256" },
      { "internalType": "uint256", "name": "", "type": "uint256" },
      { "internalType": "uint256", "name": "", "type": "uint256" },
      { "internalType": "uint256", "name": "", "type": "uint256" },
      { "internalType": "uint256", "name": "", "type": "uint256" }
    ],
    "stateMutability": "view",
    "type": "function"
  },
  {
    "inputs": [],
    "name": "getCollectedFee",
    "outputs": [{ "internalType": "uint256", "name": "", "type": "uint256" }],
    "stateMutability": "view",
    "type": "function"
  }
]
""")
__SHADOWPAY_CONTRACT_ADDRESS__ERC721__ = {
    "0x1": "0x3c5b8d6f2e"
}
SOLSCAN = "https://solscan.io/"
SOLANA_SYSTEM_PROGRAMM = "11111111111111111111111111111111"
LAMPORTS_PER_SOL = 1_000_000_000
WRAPED_SOL = "So11111111111111111111111111111111111111112"
TOKEN_PROGRAM_ID = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
NATIVE_DECIMALS: int = 9
PROGRAM_ID = Pubkey.from_string("6UuZpEGvntsQX1EW9aYhCDRd3WdyfXPaeMVdbq1eryiy")

CONFIG_PDA=Pubkey.find_program_address([b"config"], PROGRAM_ID)


# ========================= TON Constants =========================
NANOTON = 1_000_000_000  # 1 TON = 10^9 nanotons
TON_API_URL = "https://toncenter.com/api/v2"
TON_TESTNET_API_URL = "https://testnet.toncenter.com/api/v2"
TON_NATIVE_DECIMALS = 9
TONSCAN = "https://tonscan.org/"

# TON Jetton (token) standard opcodes
TON_JETTON_TRANSFER_OP = 0x0F8A7EA5
TON_JETTON_BURN_OP = 0x595F07BC

# OrbisPaySDK contract addresses on TON (to be filled after deployment)
__ORBISPAY_CONTRACT_ADDRESS__TON__ = {}


# ========================= TRX (Tron) Constants =========================
SUN_PER_TRX = 1_000_000  # 1 TRX = 10^6 sun
TRX_NATIVE_DECIMALS = 6
TRONSCAN = "https://tronscan.org/"

TRX_NETWORKS = {
    "mainnet": "https://api.trongrid.io",
    "shasta": "https://api.shasta.trongrid.io",
    "nile": "https://nile.trongrid.io",
}

# USDT TRC20 contract address on Tron mainnet
TRX_USDT_CONTRACT = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"

# OrbisPaySDK contract addresses on Tron (to be filled after deployment)
__ORBISPAY_CONTRACT_ADDRESS__TRX__ = {}


# ========================= Bitcoin Constants =========================
SATOSHI_PER_BTC = 100_000_000  # 1 BTC = 10^8 satoshi
BTC_NATIVE_DECIMALS = 8

BTC_EXPLORERS = {
    "mainnet": "https://blockstream.info/",
    "testnet": "https://blockstream.info/testnet/",
}

# Known Bitcoin network fee estimation APIs
BTC_FEE_API = "https://mempool.space/api/v1/fees/recommended"
