"""Canonical Python-to-Rust mapping for parsed source prices."""

from collections.abc import Sequence

from navlens import MarketDate, PriceObservation, UnitPrice

from .price_record import PriceRecord


def to_price_observations(records: Sequence[PriceRecord]) -> list[PriceObservation]:
    """Map provider-neutral price fields to Rust-owned validated types."""
    return [
        PriceObservation(
            MarketDate(record.market_date.year, record.market_date.month, record.market_date.day),
            UnitPrice(record.unit_price),
        )
        for record in records
    ]
