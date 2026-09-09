"""Data package."""
from data.crypto import fetch_crypto_markets, fetch_global_market
from .fx import fetch_fiat_rates

__all__ = [
    "fetch_crypto_markets",
    "fetch_fiat_rates",
    "fetch_global_market",
]