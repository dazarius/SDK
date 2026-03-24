from .erc20 import ERC20Token as ERC20
from .erc721 import ERC721Token as ERC721
from .sol import SOL as sol
from .ton import TON as ton
from .trx import TRX as trx
from .btc import BTC as btc

__all__ = ["ERC20", "ERC721", "sol", "ton", "trx", "btc"]