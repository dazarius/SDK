const ERC20_ABI = [
  { constant: true, inputs: [], name: "name", outputs: [{ name: "", type: "string" }], type: "function" },
  { constant: true, inputs: [], name: "symbol", outputs: [{ name: "", type: "string" }], type: "function" },
  { constant: true, inputs: [], name: "decimals", outputs: [{ name: "", type: "uint8" }], type: "function" },
  { constant: true, inputs: [], name: "totalSupply", outputs: [{ name: "", type: "uint256" }], type: "function" },
  { constant: true, inputs: [{ name: "_owner", type: "address" }], name: "balanceOf", outputs: [{ name: "", type: "uint256" }], type: "function" },
  { constant: false, inputs: [{ name: "_to", type: "address" }, { name: "_value", type: "uint256" }], name: "transfer", outputs: [{ name: "", type: "bool" }], type: "function" },
  { constant: false, inputs: [{ name: "_spender", type: "address" }, { name: "_value", type: "uint256" }], name: "approve", outputs: [{ name: "", type: "bool" }], type: "function" },
  { constant: true, inputs: [{ name: "_owner", type: "address" }, { name: "_spender", type: "address" }], name: "allowance", outputs: [{ name: "", type: "uint256" }], type: "function" },
  { constant: false, inputs: [{ name: "_from", type: "address" }, { name: "_to", type: "address" }, { name: "_value", type: "uint256" }], name: "transferFrom", outputs: [{ name: "", type: "bool" }], type: "function" },
];
const CHEQUES_TYPE = {
    "NativeCheque": 0x0,
    "MultiCheque": 0x1,
    "TokenCheque": 0x3,
    "SwapCheque": 0x4
}

const MAPS_FUNC = {
  [CHEQUES_TYPE.NativeCheque]: {
    init: "InitNativeCheque",
    cashout: "CashOutNativeCheque",
    info: "getNativeChequeInfo",
    detail: "_getNativeChequeInfo",
    code: 0x0
  },
  [CHEQUES_TYPE.MultiCheque]: {
    init: "InitMultiCheque",
    cashout: "CashOutMultiCheque",
    info: "getMultiChequeInfo",
    detail: "_getMultiChequeInfo",
    code: 0x1
  },
  [CHEQUES_TYPE.TokenCheque]: {
    init: "InitTokenCheque",
    cashout: "CashOutTokenCheque",
    info: "getTokenChequeDetail",
    detail: "_getTokenChequeInfo",
    code: 0x3
  },
  [CHEQUES_TYPE.SwapCheque]: {
    init: "InitTokenChequeSwap",
    cashout: "CashOutSwapCheque",
    info: "getSwapDetail",
    detail: "_getSwapDetail",
    code: 0x4
  },
};

// Reverse lookup: last byte of a chequeId -> cheque type, so type can be read
// locally without hitting the contract (see Cheque._resolveChequeType).
const CODE_TO_TYPE = Object.fromEntries(
  Object.entries(MAPS_FUNC).map(([type, cfg]) => [cfg.code, type])
);


const SHADOWPAY_ABI_ERC20 = [
  { inputs: [{ internalType: "bool", name: "_active", type: "bool" }], name: "activated", outputs: [], stateMutability: "nonpayable", type: "function" },
  { inputs: [{ internalType: "bytes32", name: "chequeId", type: "bytes32" }], name: "CashOutMultiCheque", outputs: [], stateMutability: "nonpayable", type: "function" },
  { inputs: [{ internalType: "bytes32", name: "chequeId", type: "bytes32" }], name: "CashOutNativeCheque", outputs: [], stateMutability: "nonpayable", type: "function" },
  { inputs: [{ internalType: "bytes32", name: "_id", type: "bytes32" }], name: "CashOutSwapCheque", outputs: [], stateMutability: "nonpayable", type: "function" },
  { inputs: [{ internalType: "bytes32", name: "id", type: "bytes32" }], name: "CashOutTokenCheque", outputs: [], stateMutability: "nonpayable", type: "function" },
  { inputs: [{ internalType: "bytes32", name: "chequeId", type: "bytes32" }], name: "RefundNativeCheque", outputs: [], stateMutability: "nonpayable", type: "function" },
  { inputs: [{ internalType: "bytes32", name: "chequeId", type: "bytes32" }], name: "RefundMultiCheque", outputs: [], stateMutability: "nonpayable", type: "function" },
  { inputs: [{ internalType: "bytes32", name: "id", type: "bytes32" }], name: "RefundTokenCheque", outputs: [], stateMutability: "nonpayable", type: "function" },
  { inputs: [{ internalType: "bytes32", name: "_id", type: "bytes32" }], name: "RefundSwapCheque", outputs: [], stateMutability: "nonpayable", type: "function" },
  { inputs: [{ internalType: "address", name: "newOwner", type: "address" }], name: "changeOwner", outputs: [], stateMutability: "nonpayable", type: "function" },
  { inputs: [{ internalType: "bytes32", name: "chequeId", type: "bytes32" }, { internalType: "address", name: "tokenAddr", type: "address" }, { internalType: "uint256", name: "amount", type: "uint256" }, { internalType: "address payable[]", name: "to", type: "address[]" }], name: "InitCheque", outputs: [{ internalType: "bytes32", name: "", type: "bytes32" }], stateMutability: "payable", type: "function" },
  { inputs: [{ internalType: "bytes32", name: "chequeId", type: "bytes32" }, { internalType: "address payable[]", name: "_to", type: "address[]" }], name: "InitMultiCheque", outputs: [{ internalType: "bytes32", name: "", type: "bytes32" }], stateMutability: "payable", type: "function" },
  { inputs: [{ internalType: "bytes32", name: "chequeId", type: "bytes32" }, { internalType: "address", name: "_reciever", type: "address" }, { internalType: "address", name: "_tokenIn", type: "address" }, { internalType: "uint256", name: "_amountIn", type: "uint256" }, { internalType: "address", name: "_tokenOut", type: "address" }, { internalType: "uint256", name: "_amountOut", type: "uint256" }], name: "InitSwapCheque", outputs: [{ internalType: "bytes32", name: "", type: "bytes32" }], stateMutability: "nonpayable", type: "function" },
  { inputs: [{ internalType: "uint256", name: "newBps", type: "uint256" }], name: "setMultiBps", outputs: [], stateMutability: "nonpayable", type: "function" },
  { inputs: [{ internalType: "uint256", name: "newBps", type: "uint256" }], name: "setSwapBps", outputs: [], stateMutability: "nonpayable", type: "function" },
  { inputs: [{ internalType: "address", name: "_trassary", type: "address" }], stateMutability: "nonpayable", type: "constructor" },
  { anonymous: false, inputs: [{ indexed: true, internalType: "bytes32", name: "id", type: "bytes32" }], name: "ChequeClaimed", type: "event" },
  { anonymous: false, inputs: [{ indexed: true, internalType: "bytes32", name: "id", type: "bytes32" }], name: "ChequeCreated", type: "event" },
  { inputs: [{ internalType: "bytes32", name: "chequeId", type: "bytes32" }, { internalType: "address payable", name: "_to", type: "address" }], name: "InitNativeCheque", outputs: [{ internalType: "bytes32", name: "", type: "bytes32" }], stateMutability: "payable", type: "function" },
  { inputs: [{ internalType: "bytes32", name: "chequeId", type: "bytes32" }, { internalType: "address", name: "tokenAddr", type: "address" }, { internalType: "uint256", name: "amount", type: "uint256" }, { internalType: "address payable", name: "to", type: "address" }], name: "InitTokenCheque", outputs: [{ internalType: "bytes32", name: "", type: "bytes32" }], stateMutability: "nonpayable", type: "function" },
  { inputs: [{ internalType: "uint256", name: "amount", type: "uint256" }, { internalType: "address", name: "_to", type: "address" }], name: "withdrawAmount", outputs: [], stateMutability: "nonpayable", type: "function" },
  { inputs: [], name: "withdrawFees", outputs: [], stateMutability: "nonpayable", type: "function" },
  { inputs: [], name: "collectedFees", outputs: [{ internalType: "uint256", name: "", type: "uint256" }], stateMutability: "view", type: "function" },
  { inputs: [], name: "FEE_DENOMINATOR", outputs: [{ internalType: "uint256", name: "", type: "uint256" }], stateMutability: "view", type: "function" },
  { inputs: [], name: "getBalance", outputs: [{ internalType: "uint256", name: "", type: "uint256" }], stateMutability: "view", type: "function" },
  { inputs: [], name: "getCollectedFee", outputs: [{ internalType: "uint256", name: "", type: "uint256" }], stateMutability: "view", type: "function" },
  { inputs: [], name: "getFee", outputs: [{ internalType: "uint256", name: "nativeBps", type: "uint256" }, { internalType: "uint256", name: "multiBps", type: "uint256" }, { internalType: "uint256", name: "tokenBps", type: "uint256" }, { internalType: "uint256", name: "swapBps", type: "uint256" }, { internalType: "uint256", name: "denominator", type: "uint256" },{internalType: "uint256", name: "PER_ADDRESS_FEE", type: "uint256"}], stateMutability: "view", type: "function" },
  { inputs: [{ internalType: "bytes32", name: "id", type: "bytes32" }, { internalType: "address", name: "from", type: "address" }], name: "getMultiChequeInfo", outputs: [{ internalType: "uint256", name: "amount", type: "uint256" }, { internalType: "address payable[]", name: "to", type: "address[]" }, { internalType: "bool", name: "claimed", type: "bool" }], stateMutability: "view", type: "function" },
  { inputs: [{ internalType: "bytes32", name: "id", type: "bytes32" }], name: "getNativeChequeInfo", outputs: [{ internalType: "address payable", name: "to", type: "address" }, { internalType: "uint256", name: "amount", type: "uint256" }, { internalType: "bool", name: "claimed", type: "bool" }], stateMutability: "view", type: "function" },
  { inputs: [], name: "getOwner", outputs: [{ internalType: "address", name: "", type: "address" }], stateMutability: "view", type: "function" },
  { inputs: [], name: "getProtocolStats", outputs: [{ internalType: "uint256", name: "balanceWei", type: "uint256" }, { internalType: "uint256", name: "collectedFeesWei", type: "uint256" }, { internalType: "uint256", name: "nativeBps", type: "uint256" }, { internalType: "uint256", name: "multiBps", type: "uint256" }, { internalType: "uint256", name: "tokenBps", type: "uint256" }, { internalType: "uint256", name: "swapBps", type: "uint256" }, { internalType: "uint256", name: "feeDenominator", type: "uint256" }, { internalType: "address", name: "treasuryAddress", type: "address" }, { internalType: "address", name: "ownerAddress", type: "address" }, { internalType: "bool", name: "active", type: "bool" }, { internalType: "uint256", name: "nextWithdrawTimestamp", type: "uint256" }], stateMutability: "view", type: "function" },
  { inputs: [{ internalType: "bytes32", name: "id", type: "bytes32" }], name: "getSwapDetail", outputs: [{ internalType: "address", name: "tokenIn", type: "address" }, { internalType: "uint256", name: "amountIn", type: "uint256" }, { internalType: "address", name: "tokenOut", type: "address" }, { internalType: "uint256", name: "amountOut", type: "uint256" }, { internalType: "address", name: "spender", type: "address" }, { internalType: "address", name: "receiver", type: "address" }, { internalType: "bool", name: "claimed", type: "bool" }], stateMutability: "view", type: "function" },
  { inputs: [{ internalType: "bytes32", name: "id", type: "bytes32" }], name: "getTokenChequeDetail", outputs: [{ internalType: "address", name: "spender", type: "address" }, { internalType: "address", name: "token", type: "address" }, { internalType: "uint256", name: "amount", type: "uint256" }, { internalType: "address", name: "receiver", type: "address" }, { internalType: "bool", name: "claimed", type: "bool" }], stateMutability: "view", type: "function" },
  { inputs: [], name: "getTreasery", outputs: [{ internalType: "address", name: "", type: "address" }], stateMutability: "view", type: "function" },
  { inputs: [], name: "isActive", outputs: [{ internalType: "bool", name: "", type: "bool" }], stateMutability: "view", type: "function" },
  { inputs: [], name: "MAX_BPS", outputs: [{ internalType: "uint256", name: "", type: "uint256" }], stateMutability: "view", type: "function" },
  { inputs: [], name: "MULTI_BPS", outputs: [{ internalType: "uint256", name: "", type: "uint256" }], stateMutability: "view", type: "function" },
  { inputs: [], name: "NATIVE_BPS", outputs: [{ internalType: "uint256", name: "", type: "uint256" }], stateMutability: "view", type: "function" },
  { inputs: [], name: "nextAvailableWithdraw", outputs: [{ internalType: "uint256", name: "timestamp", type: "uint256" }], stateMutability: "view", type: "function" },
  { inputs: [], name: "owner", outputs: [{ internalType: "address", name: "", type: "address" }], stateMutability: "view", type: "function" },
  { inputs: [], name: "PER_ADDRESS_FEE", outputs: [{ internalType: "uint256", name: "", type: "uint256" }], stateMutability: "view", type: "function" },
  { inputs: [], name: "SWAP_BPS", outputs: [{ internalType: "uint256", name: "", type: "uint256" }], stateMutability: "view", type: "function" },
  { inputs: [{ internalType: "bytes32", name: "", type: "bytes32" }], name: "swapCheques", outputs: [{ internalType: "address", name: "spender", type: "address" }, { internalType: "address", name: "receiver", type: "address" }, { internalType: "address", name: "tokenIn", type: "address" }, { internalType: "uint256", name: "amountIn", type: "uint256" }, { internalType: "address", name: "tokenOut", type: "address" }, { internalType: "uint256", name: "amountOut", type: "uint256" }, { internalType: "bool", name: "claimed", type: "bool" }], stateMutability: "view", type: "function" },
  { inputs: [], name: "TOKEN_BPS", outputs: [{ internalType: "uint256", name: "", type: "uint256" }], stateMutability: "view", type: "function" },
  { inputs: [], name: "treasery", outputs: [{ internalType: "address", name: "", type: "address" }], stateMutability: "view", type: "function" },
];
const ORBIS_CHEQUES_ABI = [
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
				"name": "_trassary",
				"type": "address"
			}
		],
		"stateMutability": "nonpayable",
		"type": "constructor"
	},
	{
		"inputs": [],
		"name": "AlreadyClaimed",
		"type": "error"
	},
	{
		"inputs": [],
		"name": "AlreadyRefunded",
		"type": "error"
	},
	{
		"inputs": [],
		"name": "AmountTooSmall",
		"type": "error"
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
		"name": "ChequeAlreadyExists",
		"type": "error"
	},
	{
		"inputs": [],
		"name": "ChequeAlreadyRedeemed",
		"type": "error"
	},
	{
		"inputs": [],
		"name": "ChequeExpired",
		"type": "error"
	},
	{
		"inputs": [],
		"name": "ChequeNotFound",
		"type": "error"
	},
	{
		"inputs": [],
		"name": "ContractPaused",
		"type": "error"
	},
	{
		"inputs": [],
		"name": "ExceedsMaxBps",
		"type": "error"
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
		"inputs": [],
		"name": "InvalidRecipient",
		"type": "error"
	},
	{
		"inputs": [],
		"name": "MaxRecipientsExceeded",
		"type": "error"
	},
	{
		"inputs": [],
		"name": "NoFeesCollected",
		"type": "error"
	},
	{
		"inputs": [],
		"name": "NoNativeValueForTokenCheque",
		"type": "error"
	},
	{
		"inputs": [],
		"name": "NotExpiredYet",
		"type": "error"
	},
	{
		"inputs": [],
		"name": "NotInRecipientsList",
		"type": "error"
	},
	{
		"inputs": [],
		"name": "NotReceiver",
		"type": "error"
	},
	{
		"inputs": [],
		"name": "NotRecipient",
		"type": "error"
	},
	{
		"inputs": [],
		"name": "NotSender",
		"type": "error"
	},
	{
		"inputs": [],
		"name": "NothingToRefund",
		"type": "error"
	},
	{
		"inputs": [],
		"name": "PermissionDenied",
		"type": "error"
	},
	{
		"inputs": [],
		"name": "RecipientsRequired",
		"type": "error"
	},
	{
		"inputs": [],
		"name": "SingleRecipientRequired",
		"type": "error"
	},
	{
		"inputs": [],
		"name": "TokenTransferFailed",
		"type": "error"
	},
	{
		"inputs": [],
		"name": "TransferFailed",
		"type": "error"
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
		"anonymous": false,
		"inputs": [
			{
				"indexed": true,
				"internalType": "bytes32",
				"name": "id",
				"type": "bytes32"
			}
		],
		"name": "ChequeRefunded",
		"type": "event"
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
	},
	{
		"inputs": [],
		"name": "CHEQUE_EXPIRY",
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
		"name": "getFee",
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
			},
			{
				"internalType": "uint256",
				"name": "PER_ADDRESS",
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
				"internalType": "address payable",
				"name": "_from",
				"type": "address"
			},
			{
				"internalType": "address payable[]",
				"name": "to",
				"type": "address[]"
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
			},
			{
				"internalType": "uint256",
				"name": "expiresAt",
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
		"name": "getNativeChequeInfo",
		"outputs": [
			{
				"internalType": "address payable",
				"name": "from",
				"type": "address"
			},
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
			},
			{
				"internalType": "uint256",
				"name": "expiresAt",
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
			},
			{
				"internalType": "uint256",
				"name": "expiresAt",
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
		"name": "getTokenChequeDetail",
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
				"name": "token",
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
			},
			{
				"internalType": "uint256",
				"name": "expiresAt",
				"type": "uint256"
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
			},
			{
				"internalType": "uint256",
				"name": "expiresAt",
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
	}
]

const SHADOWPAY_CONTRACT_ADDRESS_ERC20 = {
  97: "0x5487C0DdCbD5465F26B446c6CAB88D8d6F7DF23b",
  10143: "0x1d856f2eA4738d1a89E27dbfc8950a4976Db41a5",
};
const ORBIS_CHEQUES_CONTRACT = SHADOWPAY_CONTRACT_ADDRESS_ERC20;


const ALLOW_CHAINS = [56, 97, 10143, 0x1, 0x1f984, 0x38, 0x66eed, 0x89, 0xa];

const NULL_ADDRESS = "0x0000000000000000000000000000000000000000";

module.exports = {
  ORBIS_CHEQUES_ABI,
  ERC20_ABI,
  ORBIS_CHEQUES_CONTRACT,
  SHADOWPAY_ABI_ERC20,
  SHADOWPAY_CONTRACT_ADDRESS_ERC20,
  ALLOW_CHAINS,
  NULL_ADDRESS,
  CHEQUES_TYPE,
  MAPS_FUNC,
  CODE_TO_TYPE,
};
