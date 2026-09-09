from datetime import datetime, timezone
from typing import Any, Optional

from config import STABLECOINS_USD_PEG


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _payload(
    amount: float,
    base: str,
    target: str,
    *,
    status: str,
    base_usd_price: Optional[float] = None,
    fx_rate_used: Optional[float] = None,
    result: Optional[float] = None,
    audit: Optional[str] = None,
    extra: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    data: dict[str, Any] = {
        "amount": amount,
        "base": base,
        "target": target,
        "base_usd_price": base_usd_price,
        "fx_rate_used": fx_rate_used,
        "result": result,
        "timestamp": _utc_now_iso(),
        "source": "python_calculated",
        "status": status,
        "audit": audit,
    }
    if extra:
        data.update(extra)
    return data


def _fx_per_usd(code: str, fiat_rates: dict[str, float]) -> Optional[float]:
    if code == "USD":
        return 1.0
    if code not in fiat_rates:
        return None
    rate = fiat_rates[code]
    if rate is None:
        return None
    try:
        value = float(rate)
    except (TypeError, ValueError):
        return None
    return value


def _coin_usd_price(symbol: str, coins: list[dict[str, Any]]) -> Optional[float]:
    wanted = symbol.upper()
    for coin in coins:
        if str(coin.get("symbol") or "").upper() != wanted:
            continue
        price = coin.get("price_usd")
        if price is None:
            return None
        try:
            return float(price)
        except (TypeError, ValueError):
            return None
    return None


def _is_fiat(code: str, fiat_rates: dict[str, float]) -> bool:
    return code == "USD" or code in fiat_rates


def convert(
    amount: float,
    base: str,
    target: str,
    fiat_rates: Optional[dict[str, float]] = None,
    coins: Optional[list[dict[str, Any]]] = None,
) -> dict[str, Any]:
    """Deterministic conversion. Missing data returns an explicit status, never 0 as a fake rate."""
    fiat_rates = fiat_rates or {}
    coins = coins or []
    base_code = str(base or "").strip().upper()
    target_code = str(target or "").strip().upper()
    try:
        amount_n = float(amount)
    except (TypeError, ValueError):
        return _payload(
            0.0,
            base_code or str(base),
            target_code or str(target),
            status="price_missing",
            audit="Amount is not a valid number.",
        )

    target_fx = _fx_per_usd(target_code, fiat_rates)
    if target_fx is None:
        return _payload(
            amount_n,
            base_code,
            target_code,
            status="fx_missing",
            audit=f"Target FX code {target_code or '(empty)'} is not in the live USD rate book.",
        )

    if _is_fiat(base_code, fiat_rates):
        base_fx = _fx_per_usd(base_code, fiat_rates)
        if base_fx is None:
            return _payload(
                amount_n,
                base_code,
                target_code,
                status="fx_missing",
                fx_rate_used=target_fx,
                audit=f"Base FX code {base_code} is not in the live USD rate book.",
            )
        if base_fx == 0:
            return _payload(
                amount_n,
                base_code,
                target_code,
                status="fx_missing",
                fx_rate_used=target_fx,
                extra={"base_fx_per_usd": base_fx},
                audit=f"Base FX rate for {base_code} is unusable.",
            )
        base_usd = 1.0 / base_fx
        result = amount_n * target_fx / base_fx
        audit = (
            f"{amount_n:g} {base_code} = {amount_n:g} × {target_fx} {target_code}/USD "
            f"÷ {base_fx} {base_code}/USD = {result:,.8f} {target_code} (Python-verified)"
        )
        return _payload(
            amount_n,
            base_code,
            target_code,
            status="ok",
            base_usd_price=base_usd,
            fx_rate_used=target_fx,
            result=result,
            audit=audit,
            extra={"base_fx_per_usd": base_fx},
        )

    if base_code in STABLECOINS_USD_PEG:
        base_usd = 1.0
        result = amount_n * base_usd * target_fx
        audit = (
            f"{amount_n:g} {base_code} = {amount_n:g} × 1.00 USD × {target_fx} {target_code}/USD "
            f"= {result:,.8f} {target_code} (Python-verified)"
        )
        return _payload(
            amount_n,
            base_code,
            target_code,
            status="ok",
            base_usd_price=base_usd,
            fx_rate_used=target_fx,
            result=result,
            audit=audit,
        )

    price_usd = _coin_usd_price(base_code, coins)
    if price_usd is None:
        return _payload(
            amount_n,
            base_code,
            target_code,
            status="price_missing",
            fx_rate_used=target_fx,
            audit=(
                f"No live USD price for {base_code} in the CoinGecko snapshot. "
                "No conversion was calculated."
            ),
        )

    result = amount_n * price_usd * target_fx
    audit = (
        f"{amount_n:g} {base_code} = {price_usd:,.8f} USD × {target_fx} {target_code}/USD "
        f"= {result:,.8f} {target_code} (Python-verified)"
    )
    return _payload(
        amount_n,
        base_code,
        target_code,
        status="ok",
        base_usd_price=price_usd,
        fx_rate_used=target_fx,
        result=result,
        audit=audit,
    )
