"""CLI composition root for point-in-time fund return prediction."""

import sys
from collections.abc import Sequence

from navlens import NavlensValidationError
from navlens.datasets import FundUnitPriceDatasetError
from navlens.sources import CsvFundUnitPriceSourceError

from .cli_args import parse_prediction_cli_arguments
from .csv import predict_next_published_nav_return_from_csv
from .errors import PointInTimePredictionError
from .serialization import serialize_single_return_prediction
from .text_formatting import format_prediction_text


def main(argv: Sequence[str] | None = None) -> int:
    """Run provider-neutral point-in-time prediction from CLI arguments."""
    try:
        args = parse_prediction_cli_arguments(argv)
        result = predict_next_published_nav_return_from_csv(
            args.fund_unit_prices_csv,
            fund_id=args.fund_id,
            source_id=args.source_id,
            prediction_timestamp=args.prediction_timestamp,
            prediction_date=args.prediction_date,
            pricing_as_of_date=args.pricing_as_of_date,
            target_date=args.target_date,
            lookback=args.lookback,
            minimum_training_returns=args.minimum_training_returns,
            confidence_level=args.confidence_level,
            model_version=args.model_version,
        )
    except (
        CsvFundUnitPriceSourceError,
        FundUnitPriceDatasetError,
        PointInTimePredictionError,
        NavlensValidationError,
        OSError,
    ) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    if args.output_format == "json":
        sys.stdout.buffer.write(serialize_single_return_prediction(result))
        sys.stdout.buffer.write(b"\n")
    else:
        print(format_prediction_text(result))
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
