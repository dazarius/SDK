import json
from solders.pubkey import Pubkey
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


__NULL_ADDRESS__ = "0x0000000000000000000000000000000000000000"

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
