# OrbisPaySDK

A multi-chain Python SDK for payments, token operations, wallet management, and DEX integrations.

**Supported chains:** Ethereum / EVM · Solana · TON · Bitcoin · Tron

---

## Installation

```bash
pip install orbis_pay_sdk
```

---

## Quick Start

```python
from OrbisPaySDK import (
    ERC20Token, ERC721Token,
    SOL, TON, TRX, BTC,
    Cheque, SOLCheque, TONCheque, TRXCheque, BTCCheque,
    CoinGecko, Binance, Jupiter, ZeroX
)
```

---

## Modules

### EVM (Ethereum / BSC / Polygon / etc.)

```python
from web3 import Web3
from OrbisPaySDK.interface.evm import EVM

w3 = Web3(Web3.HTTPProvider("https://mainnet.infura.io/v3/YOUR_KEY"))
evm = EVM(w3=w3, key="0xPRIVATE_KEY", address="0xYOUR_ADDRESS")

# Generate wallet
wallet = evm.gen_wallet()
# {"address": "0x...", "private_key": "0x..."}

# Get balance
balance = evm.get_balance("0xADDRESS")
# {"balance": 1000000000000000000, "balance_ui": 1.0, "symbol": "ETH"}

# Batch balances (uses Multicall3)
balances = evm.get_balance_batch(["0xAddr1", "0xAddr2"])

# Transfer native currency
tx_hash = evm._native_transfer(to="0xRECEIVER", amount=0.01)

# Parse transaction
tx = evm.parse_transaction("0xTX_HASH", rpc_url="https://...")
```

---

### ERC20 Tokens

```python
from OrbisPaySDK.interface.erc20 import ERC20Token

token = ERC20Token(w3=w3, contract="0xTOKEN_CONTRACT")

# Metadata
meta = token.get_metadata()
# {"symbol": "USDC", "decimals": 6, "token_contract": "0x..."}

# Balance
balance = token.get_balance("0xWALLET", decimals=6)

# Transfer
tx_hash = token.transfer(
    private_key="0xKEY",
    to="0xRECEIVER",
    amount=10.0,
    decimals=6
)

# Approve spender
tx_hash = token.approve(spender="0xSPENDER", amount=100.0, private_key="0xKEY")

# Ensure allowance before swap
token.ensure_allowance(private_key="0xKEY", spender="0xDEX", amount=1000000)
```

---

### ERC721 (NFTs)

```python
from OrbisPaySDK.interface.erc721 import ERC721Token

nft = ERC721Token(web3=w3, address="0xNFT_CONTRACT")

owner = nft.owner_of(token_id=42)
uri   = nft.token_uri(token_id=42)
tx    = nft.transfer(private_key="0xKEY", to="0xRECEIVER", token_id=42)
```

---

### Solana

```python
import asyncio
from OrbisPaySDK.interface.sol import SOL

sol = SOL(rpc_url="https://api.mainnet-beta.solana.com", KEYPAIR="base58_private_key")

# Generate wallet
wallet = sol.gen_wallet()
# {"private_key": "base58...", "public_key": "..."}

# Get SOL balance
balance = asyncio.run(sol.get_balance())
# {"balance": 1.5, "raw_balance": 1500000000}

# Get all SPL token accounts
tokens = asyncio.run(sol.get_token_accounts_by_owner("PUBKEY"))

# Transfer SOL
tx = asyncio.run(sol.transfer_native(to="PUBKEY", amount=1000000000))

# Transfer SPL token
tx = asyncio.run(sol.transfer_token(to="PUBKEY", amount=1.0))

# Parse transaction
tx_info = asyncio.run(sol._parse_transaction("SIGNATURE"))
```

---

### TON

```python
import asyncio
from OrbisPaySDK.interface.ton import TON

ton = TON(
    api_url="https://toncenter.com/api/v2",
    api_key="YOUR_API_KEY",
    mnemonics=["word1", "word2", ...],  # 24 words
    wallet_version="v4r2"
)

# Generate wallet
wallet = TON.gen_wallet(version="v4r2")
# {"mnemonics": [...], "address": "EQ...", "raw_address": "0:..."}

# Balance
balance = asyncio.run(ton.get_balance("EQ..."))
# {"symbol": "TON", "decimals": 9, "balance": 5.0, "raw_balance": 5000000000}

# Transfer TON
result = asyncio.run(ton.transfer_native(to="EQ...", amount=1.0, memo="payment"))

# Transfer Jetton
jetton_wallet = asyncio.run(ton.get_jetton_wallet_address(jetton_master="EQ...", owner="EQ..."))
result = asyncio.run(ton.transfer_jetton(
    jetton_wallet_address=jetton_wallet,
    to="EQ...",
    amount=1000000,
    comment="payment"
))

# Get & parse transactions
txs = asyncio.run(ton.get_and_parse_transactions("EQ...", limit=10))
```

---

### Bitcoin

```python
from OrbisPaySDK.interface.btc import BTC

# Generate wallet
wallet = BTC.gen_wallet()
# {"private_key": "WIF...", "address": "1...", "segwit_address": "3...", "public_key": "..."}

# Generate from mnemonic
wallet = BTC.gen_wallet_mnemonic(words=12, address_type="bip84")
# {"mnemonic": "...", "address": "bc1q...", "path": "m/84'/0'/0'/0/0", ...}

# Load existing wallet
btc = BTC(private_key="WIF_KEY")
# or from mnemonic:
btc = BTC(mnemonics="word1 word2 ...", address_type="bip84")

# Balance
balance = btc.get_balance()
# {"balance_ui": 0.005, "balance": 500000}  # satoshi

# Transfer
tx_hash = btc.transfer(to="1ADDRESS", amount=0.001, fee=1000)

# Derive multiple addresses from mnemonic
addresses = btc.derive_addresses(count=5, start_index=0)
```

**HD Wallet standards:**
| Type | Path | Format |
|------|------|--------|
| BIP44 | `m/44'/0'/0'/0/n` | Legacy (1...) |
| BIP49 | `m/49'/0'/0'/0/n` | Wrapped SegWit (3...) |
| BIP84 | `m/84'/0'/0'/0/n` | Native SegWit (bc1q...) |

---

### Tron

```python
from OrbisPaySDK.interface.trx import TRX

# Generate wallet
wallet = TRX.gen_wallet()
# {"private_key": "hex...", "address": "T...", "public_key": "hex..."}

trx = TRX(network="mainnet", private_key="HEX_KEY")

# Balance
balance = trx.get_balance("TADDRESS")
# {"balance_ui": 100.0, "balance": 100000000}  # in sun

# Transfer TRX
result = trx.transfer_native(to="TADDRESS", amount=10.0, private_key="HEX_KEY")

# TRC20 operations
info    = trx.get_trc20_info("CONTRACT")
balance = trx.get_trc20_balance("CONTRACT", "TADDRESS", decimals=6)
tx      = trx.transfer_trc20("CONTRACT", to="TADDRESS", amount=10.0, decimals=6)
```

---

## Cheque / Escrow System

The SDK includes a cheque system — lock funds on-chain, release to a recipient.

### EVM Cheques

```python
import asyncio
from OrbisPaySDK.types.EVMcheque import Cheque

cheque = Cheque(w3=w3, private_key="0xKEY", ABI=ABI, allowed_chains=[56, 1])

# Native currency cheque
result = asyncio.run(cheque.InitCheque(
    support_bps=100, amount=1000000000000000000,
    receiver=["0xRECEIVER"], private_key="0xKEY"
))
# {"hash": "0x...", "chequeId": "0x..."}

# Cash out
result = asyncio.run(cheque.CashOutCheque(private_key="0xKEY", cheque_id="0xID"))

# ERC20 token cheque
result = asyncio.run(cheque.InitTokenCheque(
    support_bps=100, token_address="0xUSDC",
    amount=10000000, receiver="0xRECEIVER", private_key="0xKEY"
))

# Swap cheque (lock token A, receive token B)
result = asyncio.run(cheque.InitTokenChequeSwap(
    support_bps=100,
    token_in="0xUSDC", amount_in=10000000,
    token_out="0xETH",  amount_out=4000000000000000,
    receiver="0xRECEIVER", private_key="0xKEY"
))
```

### Solana Cheques

```python
import asyncio
from OrbisPaySDK.types.SOLcheque import SOLCheque

cheque = SOLCheque(rpc_url="https://api.mainnet-beta.solana.com", key="BASE58_KEY")

# SOL cheque
result = asyncio.run(cheque.init_cheque(cheque_amount=0.1, recipient="PUBKEY"))
# {"cheque_pubkey": "...", "signature": "..."}

result = asyncio.run(cheque.claim_cheque(pda_acc="CHEQUE_PUBKEY"))

# SPL token cheque
result = asyncio.run(cheque.init_token_cheque(
    token_mint="MINT_ADDRESS", token_amount=10.0, recipient="PUBKEY"
))

# Swap cheque
result = asyncio.run(cheque.init_swap_cheque(
    mintA="TOKEN_A_MINT", mintB="TOKEN_B_MINT",
    amountA=1.0, amountB=10.0, recepient="PUBKEY"
))
```

---

## Price Feeds

### CoinGecko (free)

```python
import asyncio
from OrbisPaySDK.utils.utils import CoinGecko

cg = CoinGecko()

prices = asyncio.run(cg.get_prices(["bitcoin", "ethereum", "solana"]))
# {"bitcoin": 97000.0, "ethereum": 2600.0, "solana": 180.0}

price = asyncio.run(cg.get_price("bitcoin"))
# 97000.0

chart = asyncio.run(cg.get_market_chart("ethereum", days=7))
```

### CoinMarketCap

```python
from OrbisPaySDK.utils.utils import CoinMarketCap

cmc = CoinMarketCap(api_key="YOUR_CMC_KEY")
prices = asyncio.run(cmc.get_prices(["BTC", "ETH"]))
```

---

## Exchange Integrations

### Binance

```python
import asyncio
from OrbisPaySDK.utils.binance import Binance

binance = Binance(api_key="KEY", api_secret="SECRET")

price   = asyncio.run(binance.get_price("BTCUSDT"))
klines  = asyncio.run(binance.get_klines("ETHUSDT", interval="1h", limit=100))
account = asyncio.run(binance.get_account())

order = asyncio.run(binance.place_order(
    symbol="BTCUSDT", side="BUY",
    order_type="LIMIT", quantity="0.001", price="90000"
))
```

### Bybit

```python
from OrbisPaySDK.utils.bybit import Bybit

bybit = Bybit(api_key="KEY", api_secret="SECRET")

ticker  = asyncio.run(bybit.get_ticker("BTCUSDT"))
balance = asyncio.run(bybit.get_wallet_balance())
order   = asyncio.run(bybit.place_order(
    symbol="BTCUSDT", side="Buy",
    order_type="Limit", qty="0.001", price="90000"
))
```

### Jupiter (Solana DEX)

```python
from OrbisPaySDK.utils.jupiter import Jupiter

jup = Jupiter(api_key="YOUR_KEY")

# Get swap quote
quote = asyncio.run(jup.get_quote(
    input_mint="So11111111111111111111111111111111111111112",  # SOL
    output_mint="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
    amount=1000000000,  # 1 SOL in lamports
    slippage_bps=50
))

# Build swap transaction
swap = asyncio.run(jup.get_swap(quote, user_public_key="YOUR_PUBKEY"))

# Get token price
price = asyncio.run(jup.get_price("So11111111111111111111111111111111111111112"))
```

### 0x Protocol (EVM DEX)

```python
from OrbisPaySDK.utils.zerox import ZeroX

zx = ZeroX(api_key="YOUR_0X_KEY")

# Price check
price = asyncio.run(zx.get_price(
    chain_id=1,
    sell_token="0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",  # USDC
    buy_token="0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",   # WETH
    sell_amount="1000000000"  # 1000 USDC
))

# Executable swap quote
quote = asyncio.run(zx.get_quote(
    chain_id=1,
    sell_token="USDC", buy_token="WETH",
    sell_amount="1000000000", taker="0xYOUR_ADDRESS"
))
```

**Supported chains for 0x:** Ethereum (1) · Polygon (137) · BSC (56) · Arbitrum (42161) · Base (8453) · Optimism (10) · Avalanche (43114)

---

## Requirements

- Python 3.9+
- `web3>=6.0.0`
- `solana>=0.35.0`
- `tonsdk`
- `tonutils`
- `tronpy`
- `bit`
- `bip_utils`
- `requests>=2.28.0`
- `httpx`

---

## License

MIT
