from calendar import month
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import OrbisPaySDK
from OrbisPaySDK.interface.erc20 import ERC20Token

from OrbisPaySDK.interface.evm import EVM
from OrbisPaySDK.interface.sol import SOL
from OrbisPaySDK.interface.btc import BTC
from OrbisPaySDK.interface.ton import TON, DEFAULT_VERSION
from OrbisPaySDK.interface.trx import Tron
from OrbisPaySDK.utils import utils, bybit
# from web3 import Web3
# w3 = Web3(Web3.HTTPProvider('https://bsc-rpc.publicnode.com'))
# token_address = '0x55d398326f99059fF775485246999027B3197955' ## USDT on BSC 
# spender_address = '0x70F753c7ce542B1008aDFC00A8dbfe4F64AcDF6c'
from OrbisPaySDK.interface import sol
WALLET_PATH = "wallets"
evm  = EVM()
s = sol()
ton = TON()
trx = Tron()

btc = BTC()

def _wallet_gen():
    # token = ERC20Token(w3, token_address)
    

    data = {
        "wallets":{
            "evm": evm.gen_wallet(),
            "sol": s.gen_wallet(),
            "ton": ton.gen_wallet(),
            "trx": trx.generate_address(),
            "btc": btc.gen_wallet()

        }
    } 
    # print(data)
    return data
    # print(f"btc:{btc.gen_wallet_mnemonic()}\n trx:{trx.generate_address()}")
    # print(f"erc20:{trx.get_asset_from_name("TLaGjwhvA8XQYSxFAcAXy7Dvuue9eGYitv")}")



async def get_price(coin):
    # _p = await utils.get_native_prices(vs_currency="usd")
    coingeko = utils.CoinGecko()
    if coin:
        _p = await coingeko.get_price(coin)
    else:
        _p2 = await utils.get_native_price()
    return _p

async def test_ton(mnemonic = 'token asset quarter all ordinary truck short elite actor toddler liberty person hundred same age timber spatial gauge dentist neither salute solid mystery lock'):
    chain_key = "ton"
    # new_wallets = _wallet_gen()
    # address = new_wallets[WALLET_PATH][chain_key]["address"]
    # print(f"adddress: {address}\nMnemonic: {new_wallets[WALLET_PATH][chain_key]["mnemonics"]}")
    # mnemonic_list = new_wallets["wallets"]["ton"]["mnemonics_list"]
    # acc = ton.set_params(mnemonics=mnemonic)
    # print("ton.get_address():"," ",ton.get_address())
    # print(f"[ton.get_balance()]: {await ton.get_balance()}")
    ton_price = await get_price("ton")
    txs = await ton.get_and_parse_transactions(address="UQDy3BhgaGzWWJh-K-2CFlMtjABEYNreqQfMfUrXI2xJa5C1", limit=100,get_price=True, price = ton_price)
    print(f"[ton.get_balance()]: {txs}")
    import json
    with open("ton_txs.json", "w") as f:
        json.dump(txs,f, indent=4)


async def f(*args):
    print("Starting withdrawal summary...")
    print(f"sol price: ${await get_price('sol')}")
    bb = bybit.Bybit(api_key="SLm7WOTnmzChXMLssJ", api_secret="Tyb6kAfUYTfX24hfMua6UIODF9muBBpWaxoD")
    total_coins_amount = {}
    month = args[0]
    # Сначала загрузим сырые записи, чтобы видеть что вернул API
    records = await bb.get_all_withdrawal_records(months=month)
    print(f"Total raw records loaded: {len(records)}")
    for r in records:
        if r.get('coin') not in total_coins_amount:
            total_coins_amount[r.get('coin')] = 0
        total_coins_amount[r.get('coin')] += float(r.get('amount'))
    print(total_coins_amount)
    if records:
        for r in records[:5]:
            print(f"  [{r.get('status')}] {r.get('coin')} {r.get('amount')} "
                  f"via {r.get('chain')} → {r.get('toAddress','')[:20]}…")
        if len(records) > 5:
            print(f"  ... and {len(records) - 5} more")

    # Теперь строим сводку
    summary = bb.summarize_withdrawals(records, status_filter="success")
    if not summary:
        # Попробуем без фильтра по статусу
        print("\nNo 'success' records. Trying without status filter...")
        summary = bb.summarize_withdrawals(records, status_filter=None)

    if not summary:
        print("No withdrawal records found at all.")
    else:
        print(f"\n=== Withdrawal Summary ({len(summary)} tokens) ===")
        for coin, s in summary.items():
            print(f"{coin}: {s.total_amount} withdrawn ({s.count} txns, fee: {s.total_fee})")
            for chain, info in s.by_chain.items():
                print(f"  {chain}: {info['amount']} ({info['count']} txns)")

    print("====================bb.get_withdrawal_addresses()====================")
    print(await bb.get_order_history())
    # print(await bb.get_withdrawal_addresses(coin="USDT"))

if __name__ == "__main__":
    import asyncio
    s.set_params(
        rpc_url="https://api.devnet.solana.com"
    )
    tx_dict = asyncio.run(s._parse_transaction("5JVRbqjttRCHVUagT5ZjawaVEyRRWcqXjrHxsZ9v6xtgcEJjapZrxvSi59um1AhCihJx2wmtsDq78YvaPTSvgHUh"))
    print(tx_dict)
    # test_erc20()    
    # asyncio.run(f(12))
    # asyncio.run(prices())
