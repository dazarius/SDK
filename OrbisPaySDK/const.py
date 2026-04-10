import json
from dataclasses import dataclass
from solders.pubkey import Pubkey


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
    56,  # BSC Mainnet
    97,  # BSC Testnet
    10143,
    0x1,
    0x1f984,
    0x38,
    0x66eed,
    0x89,
    0xa 
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

__SHADOWPAY_CONTRACT_ADDRESS__ERC20__ = {
    97: "0x5487C0DdCbD5465F26B446c6CAB88D8d6F7DF23b",
    10143: "0x1d856f2eA4738d1a89E27dbfc8950a4976Db41a5"
  }
ERC20_SIGNATURES = {
    "0xa9059cbb": ("Transfer", "Sending tokens to recipient"),
    "0x095ea7b3": ("Approve", "Allowing contract to use your tokens"),
    "0x23b872dd": ("TransferFrom", "Contract moves tokens on your behalf"),
    "0x7ff36ab5": ("Swap (Uniswap/Pancake)", "Exchanging tokens via router"),
    "0x18cbafe5": ("Swap Extract Tokens", "Exchanging fixed amount of tokens"),
    "0x38ed1739": ("Swap Extract ETH for Tokens", "Buying tokens with native BNB/ETH"),
    "0x791ac947": ("Swap Extract Tokens for ETH", "Selling tokens for native BNB/ETH"),
    "0xf3056030": ("Add Liquidity", "Providing assets to a pool"),
    "0xbaa2abde": ("Remove Liquidity", "Withdrawing assets from a pool"),
}
__ORBISPAY_DOMAIN_ABI = json.loads("""[
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
__SHADOWPAY_ABI__ERC20__ = json.loads("""[
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
				"indexed": false,
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
				"indexed": false,
				"internalType": "bytes32",
				"name": "id",
				"type": "bytes32"
			}
		],
		"name": "ChequeCreated",
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
		"name": "redeem",
		"type": "event"
	},
	{
		"inputs": [
			{
				"internalType": "bytes32",
				"name": "groupIdv1",
				"type": "bytes32"
			}
		],
		"name": "CashOutCheque",
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
				"internalType": "address payable[]",
				"name": "_to",
				"type": "address[]"
			}
		],
		"name": "InitCheque",
		"outputs": [
			{
				"internalType": "bytes32",
				"name": "groupIdv1",
				"type": "bytes32"
			}
		],
		"stateMutability": "payable",
		"type": "function"
	},
	{
		"inputs": [
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
				"name": "chequeId",
				"type": "bytes32"
			}
		],
		"stateMutability": "payable",
		"type": "function"
	},
	{
		"inputs": [
			{
				"internalType": "address",
				"name": "tokenAddrr",
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
		"stateMutability": "payable",
		"type": "function"
	},
	{
		"inputs": [],
		"name": "PROTOCOL_FEE",
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
		"name": "feeBasisPoints",
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
		"name": "getChequeInfo",
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
		"name": "getFeeData",
		"outputs": [
			{
				"internalType": "uint256",
				"name": "_protocolFee",
				"type": "uint256"
			},
			{
				"internalType": "uint256",
				"name": "_baseFee",
				"type": "uint256"
			},
			{
				"internalType": "uint256",
				"name": "_minFee",
				"type": "uint256"
			},
			{
				"internalType": "uint256",
				"name": "_maxFees",
				"type": "uint256"
			},
			{
				"internalType": "uint256",
				"name": "_feeBasisPoints",
				"type": "uint256"
			},
			{
				"internalType": "uint256",
				"name": "_swapBasicPoints",
				"type": "uint256"
			},
			{
				"internalType": "uint256",
				"name": "_feeDenominator",
				"type": "uint256"
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
		"inputs": [
			{
				"internalType": "address",
				"name": "",
				"type": "address"
			}
		],
		"name": "nonces",
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
				"name": "_protocolFee",
				"type": "uint256"
			},
			{
				"internalType": "uint256",
				"name": "_minFee",
				"type": "uint256"
			},
			{
				"internalType": "uint256",
				"name": "_maxFees",
				"type": "uint256"
			},
			{
				"internalType": "uint256",
				"name": "_baseFee",
				"type": "uint256"
			}
		],
		"name": "setFees",
		"outputs": [],
		"stateMutability": "nonpayable",
		"type": "function"
	},
	{
		"inputs": [
			{
				"internalType": "uint256",
				"name": "_TokenChequepercentage",
				"type": "uint256"
			},
			{
				"internalType": "uint256",
				"name": "_SwapTokenChequepercentage",
				"type": "uint256"
			}
		],
		"name": "setTokenFees",
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
		"inputs": [],
		"name": "swapBasicPoints",
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
      { "internalType": "address", "name": "token", "type": "address" },
      { "internalType": "uint128", "name": "amount", "type": "uint128" },
      { "internalType": "uint64", "name": "dueAt", "type": "uint64" },
      { "internalType": "address", "name": "payer", "type": "address" },
      { "internalType": "bool", "name": "allowTips", "type": "bool" },
      { "internalType": "bool", "name": "allowPartial", "type": "bool" }
    ],
    "name": "createInvoice",
    "outputs": [],
    "stateMutability": "nonpayable",
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
PROGRAM_ID = Pubkey.from_string("6ZQWADxiM4Vy2ZXxJEZ7DvB8k7FctAXBWKj8z4b3FjMo")

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
