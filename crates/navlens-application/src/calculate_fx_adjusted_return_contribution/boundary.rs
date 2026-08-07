use super::{FxBoundaryEvidence, FxReturnPolicy};
use crate::calculate_return_contribution::{
    CalculateReturnContributionError, ReturnCoverageGapReason,
};
use navlens_calendar::{FxRateObservation, FxRateSeries, MarketDate};
use navlens_core::{CurrencyPair, FxRateKind};

type BoundarySelection = Result<FxBoundaryEvidence, ReturnCoverageGapReason>;

fn boundary_evidence(
    requested_date: MarketDate,
    observation: &FxRateObservation,
) -> Result<FxBoundaryEvidence, CalculateReturnContributionError> {
    let staleness = requested_date.calendar_days_since(observation.market_date());
    let staleness_calendar_days = u32::try_from(staleness).map_err(|_| {
        CalculateReturnContributionError::InvalidStalenessConversion {
            requested_date,
            observation_date: observation.market_date(),
            staleness,
        }
    })?;
    Ok(FxBoundaryEvidence::new(
        requested_date,
        observation.clone(),
        staleness_calendar_days,
    )?)
}

pub(super) fn select_start_boundary(
    series: &FxRateSeries,
    requested_date: MarketDate,
    policy: FxReturnPolicy,
    required_pair: &CurrencyPair,
    required_kind: FxRateKind,
) -> Result<BoundarySelection, CalculateReturnContributionError> {
    let Some(observation) = series.latest_observation_on_or_before(requested_date) else {
        return Ok(Err(ReturnCoverageGapReason::MissingFxStartObservation {
            required_pair: required_pair.clone(),
            required_kind,
            requested_date,
        }));
    };
    let evidence = boundary_evidence(requested_date, observation)?;
    if evidence.staleness_calendar_days() > policy.max_fx_staleness_calendar_days() {
        return Ok(Err(ReturnCoverageGapReason::StaleFxStartObservation {
            evidence,
            maximum_staleness_calendar_days: policy.max_fx_staleness_calendar_days(),
        }));
    }
    Ok(Ok(evidence))
}

pub(super) fn select_end_boundary(
    series: &FxRateSeries,
    requested_date: MarketDate,
    policy: FxReturnPolicy,
) -> Result<BoundarySelection, CalculateReturnContributionError> {
    let observation = series
        .latest_observation_on_or_before(requested_date)
        .ok_or(
            CalculateReturnContributionError::MissingFxEndAfterStartInvariant { requested_date },
        )?;
    let evidence = boundary_evidence(requested_date, observation)?;
    if evidence.staleness_calendar_days() > policy.max_fx_staleness_calendar_days() {
        return Ok(Err(ReturnCoverageGapReason::StaleFxEndObservation {
            evidence,
            maximum_staleness_calendar_days: policy.max_fx_staleness_calendar_days(),
        }));
    }
    Ok(Ok(evidence))
}
