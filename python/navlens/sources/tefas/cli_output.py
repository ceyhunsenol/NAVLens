"""Human-readable output for TEFAS acquisition commands."""

from .acquisition import TefasAcquisitionResult
from .request import TefasPriceRequest


def format_acquisition_result(result: TefasAcquisitionResult, request: TefasPriceRequest) -> str:
    """Render acquisition metadata followed by dated unit-price rows."""
    cache_status = "hit" if result.from_cache else "miss"
    lines = [
        f"fund={request.normalized_fund_code}",
        f"interval={request.start_date.isoformat()}..{request.end_date.isoformat()}",
        f"records={len(result.records)}",
        f"cache={cache_status}",
        f"raw={result.payload_path}",
        "date,unit_price",
    ]
    lines.extend(
        f"{record.market_date.isoformat()},{record.unit_price}" for record in result.records
    )
    return "\n".join(lines)
