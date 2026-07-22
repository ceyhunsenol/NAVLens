use crate::align_holdings_prices::{
    AlignHoldingsPricesError, AlignmentPolicy, CoverageGapReason, CoveredHoldingPrice,
    PortfolioCoverageReport, SecurityPriceHistoryCandidate, UncoveredHolding,
};
use navlens_calendar::SecurityPriceSeries;
use navlens_core::{AssetClass, HoldingPosition, InstrumentId, PortfolioCoverageWeights};
use std::collections::{HashMap, HashSet};

type CandidateMap<'a> = HashMap<&'a InstrumentId, &'a SecurityPriceHistoryCandidate>;

enum HoldingAlignment {
    Covered(CoveredHoldingPrice),
    Uncovered(UncoveredHolding),
}

/// Deterministically aligns holdings with security prices.
///
/// # Errors
/// Returns an error when request-wide uniqueness, point-in-time, price-series,
/// or coverage arithmetic invariants are violated.
pub fn align_holdings_prices(
    holdings: &[HoldingPosition],
    candidates: &[SecurityPriceHistoryCandidate],
    policy: &AlignmentPolicy,
) -> Result<PortfolioCoverageReport, AlignHoldingsPricesError> {
    ensure_unique_holdings(holdings)?;
    let candidate_map = index_candidates(candidates)?;
    let mut covered = Vec::new();
    let mut uncovered = Vec::new();

    for holding in holdings {
        match align_holding(holding, &candidate_map, policy)? {
            HoldingAlignment::Covered(item) => covered.push(item),
            HoldingAlignment::Uncovered(item) => uncovered.push(item),
        }
    }

    let weights = calculate_coverage_weights(&covered, &uncovered)?;
    Ok(PortfolioCoverageReport::new(
        covered,
        uncovered,
        weights,
        policy.clone(),
    ))
}

fn ensure_unique_holdings(holdings: &[HoldingPosition]) -> Result<(), AlignHoldingsPricesError> {
    let mut seen = HashSet::with_capacity(holdings.len());
    for holding in holdings {
        if !seen.insert(holding.instrument_id()) {
            return Err(AlignHoldingsPricesError::DuplicateHoldingInstrument(
                holding.instrument_id().clone(),
            ));
        }
    }
    Ok(())
}

fn index_candidates(
    candidates: &[SecurityPriceHistoryCandidate],
) -> Result<CandidateMap<'_>, AlignHoldingsPricesError> {
    let mut indexed = HashMap::with_capacity(candidates.len());
    for candidate in candidates {
        if indexed
            .insert(candidate.instrument_id(), candidate)
            .is_some()
        {
            return Err(AlignHoldingsPricesError::DuplicateHistoryCandidate(
                candidate.instrument_id().clone(),
            ));
        }
    }
    Ok(indexed)
}

fn align_holding(
    holding: &HoldingPosition,
    candidates: &CandidateMap<'_>,
    policy: &AlignmentPolicy,
) -> Result<HoldingAlignment, AlignHoldingsPricesError> {
    if !is_supported_asset_class(holding.asset_class()) {
        return Ok(uncovered(
            holding,
            CoverageGapReason::UnsupportedAssetClass {
                asset_class: holding.asset_class(),
            },
        ));
    }
    let Some(candidate) = candidates.get(holding.instrument_id()).copied() else {
        return Ok(uncovered(holding, CoverageGapReason::MissingPriceSeries));
    };
    validate_point_in_time(candidate, policy)?;
    if candidate.observations().len() < policy.minimum_observations() {
        return Ok(uncovered(
            holding,
            CoverageGapReason::InsufficientObservations {
                found: candidate.observations().len(),
                required: policy.minimum_observations(),
            },
        ));
    }
    align_validated_candidate(holding, candidate, policy)
}

fn validate_point_in_time(
    candidate: &SecurityPriceHistoryCandidate,
    policy: &AlignmentPolicy,
) -> Result<(), AlignHoldingsPricesError> {
    if let Some(observation) = candidate
        .observations()
        .iter()
        .find(|item| item.market_date() > policy.pricing_as_of_date())
    {
        return Err(AlignHoldingsPricesError::ObservationAfterPricingAsOf {
            instrument_id: candidate.instrument_id().clone(),
            observation_date: observation.market_date(),
            pricing_as_of_date: policy.pricing_as_of_date(),
        });
    }
    Ok(())
}

fn align_validated_candidate(
    holding: &HoldingPosition,
    candidate: &SecurityPriceHistoryCandidate,
    policy: &AlignmentPolicy,
) -> Result<HoldingAlignment, AlignHoldingsPricesError> {
    let series = SecurityPriceSeries::new(candidate.observations().to_vec()).map_err(|source| {
        AlignHoldingsPricesError::InvalidPriceHistory {
            instrument_id: holding.instrument_id().clone(),
            source,
        }
    })?;
    if let Some(reason) = policy_gap(&series, policy) {
        return Ok(uncovered(holding, reason));
    }
    Ok(HoldingAlignment::Covered(CoveredHoldingPrice::new(
        holding.clone(),
        series,
    )))
}

fn policy_gap(series: &SecurityPriceSeries, policy: &AlignmentPolicy) -> Option<CoverageGapReason> {
    if series.currency() != policy.fund_base_currency() {
        return Some(CoverageGapReason::CurrencyMismatch {
            expected: policy.fund_base_currency().clone(),
            found: series.currency().clone(),
        });
    }
    if series.adjustment() != policy.required_price_adjustment() {
        return Some(CoverageGapReason::IncompatiblePriceAdjustment {
            expected: policy.required_price_adjustment(),
            found: series.adjustment(),
        });
    }
    stale_gap(series, policy)
}

fn stale_gap(series: &SecurityPriceSeries, policy: &AlignmentPolicy) -> Option<CoverageGapReason> {
    let latest_observation_date = series.observations().last()?.market_date();
    let staleness = policy
        .pricing_as_of_date()
        .calendar_days_since(latest_observation_date);
    (staleness > i64::from(policy.max_staleness_calendar_days())).then_some(
        CoverageGapReason::StalePrices {
            latest_observation_date,
            pricing_as_of_date: policy.pricing_as_of_date(),
            max_staleness_calendar_days: policy.max_staleness_calendar_days(),
        },
    )
}

fn calculate_coverage_weights(
    covered: &[CoveredHoldingPrice],
    uncovered: &[UncoveredHolding],
) -> Result<PortfolioCoverageWeights, AlignHoldingsPricesError> {
    let covered_weights: Vec<_> = covered
        .iter()
        .map(|item| item.holding().fund_total_weight())
        .collect();
    let uncovered_weights: Vec<_> = uncovered
        .iter()
        .map(|item| item.holding().fund_total_weight())
        .collect();
    PortfolioCoverageWeights::new(&covered_weights, &uncovered_weights)
        .map_err(|source| AlignHoldingsPricesError::CoverageArithmetic { source })
}

fn uncovered(holding: &HoldingPosition, reason: CoverageGapReason) -> HoldingAlignment {
    HoldingAlignment::Uncovered(UncoveredHolding::new(holding.clone(), reason))
}

fn is_supported_asset_class(asset_class: AssetClass) -> bool {
    matches!(
        asset_class,
        AssetClass::Equity | AssetClass::ExchangeTradedFund
    )
}
