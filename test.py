from OrbisPaySDK.types.SOLcheque import SOLCheque
from OrbisPaySDK.interface.sol import SOL
import asyncio
import time
import requests
import json
k = SOLCheque(
    rpc_url="https://api.devnet.solana.com",
    key=""
)
async def efwa():
    
    tokenA = "Gh9ZwEmdLJ8DscKNTkTqPbNwLNNBjuSzaG9Vp2KGtKJr"
    tokenB = "HzwqbKZw8HxMN6bF2yFZNrht3c2iXXzpKcFu7uBEDKtr"
    j = await k.init_swap_cheque(
        mintA=tokenA,
        mintB=tokenB,
        amountA=0.1,
        amountB=0.1,
        recepient="9zXTCt6dyoVn4GFmwtQfwGjayVVjojSjgayWK7u6GLVy"
    )
    j["signature"] = f"https://solscan.io/tx/{j['signature']}?cluster=devnet"
    
    return j


async def efwa2():
    cheque_acc = input("Enter cheque account: ")
    cheque = await k.claim_swap_cheque(
        pda_acc=cheque_acc,
    )


    cheque["signature"] = f"https://solscan.io/tx/{cheque['signature']}?cluster=devnet"
    return cheque

def download_asset():
    uri = "https://tokens.1inch.io/v1.1/1"
    res = requests.get(uri)
    with open("assets.json", "w") as f:
        json.dump(res.json(), f, indent=4)
def get_sol_tokens_balance(address:str = "C3MhUqKFRkkTRBRZcH7EKoD8c1iose9T3tPb7qiytzxs"):
    s = SOL(
        rpc_url="https://api.devnet.solana.com",
    )
    print(asyncio.run(s.get_token_accounts_by_owner(owner_pubkey=address)))
if __name__ == "__main__":
    # print(k.parse_swap_cheque_data(pda="FejNYkUCn3f9FErTWrGPdD2tZnqkCdBw8pbjCNdezt84"))
    # print(asyncio.run(efwa()))
    


    # k.set_params(
    #     key=""
    # )
    # time.sleep(5)

    get_sol_tokens_balance()
    # print(k.get_config())