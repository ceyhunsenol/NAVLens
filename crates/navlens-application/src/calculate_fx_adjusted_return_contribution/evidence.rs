use super::error::FxReturnContractError;
use navlens_calendar::{FxRateObservation, MarketDate};
use navlens_core::{CurrencyPair, DecimalReturn, FxRateKind, calculate_fx_decimal_return};

/// Verified evidence for a single FX boundary observation.
#[derive(Clone, Debug, PartialEq)]
pub struct FxBoundaryEvidence {
    requested_date: MarketDate,
    observation: FxRateObservation,
    staleness_calendar_days: u32,
}

impl FxBoundaryEvidence {
    /// Creates and validates a new `FxBoundaryEvidence`.
    ///
    /// # Errors
    /// Returns [`FxReturnContractError::ObservationAfterRequestedBoundary`] if the observation date is after `requested_date`.
    /// Returns [`FxReturnContractError::StalenessMismatch`] if `staleness_calendar_days` does not match the actual calendar-day difference.
    pub fn new(
        requested_date: MarketDate,
        observation: FxRateObservation,
        staleness_calendar_days: u32,
    ) -> Result<Self, FxReturnContractError> {
        if observation.market_date() > requested_date {
            return Err(FxReturnContractError::ObservationAfterRequestedBoundary {
                requested_date,
                observation_date: observation.market_date(),
            });
        }

        let actual_staleness = requested_date.calendar_days_since(observation.market_date());
        if actual_staleness != i64::from(staleness_calendar_days) {
            return Err(FxReturnContractError::StalenessMismatch {
                requested_date,
                observation_date: observation.market_date(),
                declared: staleness_calendar_days,
                actual: actual_staleness,
            });
        }

        Ok(Self {
            requested_date,
            observation,
            staleness_calendar_days,
        })
    }

    /// Returns the requested boundary date.
    #[must_use]
    pub const fn requested_date(&self) -> MarketDate {
        self.requested_date
    }

    /// Returns a reference to the boundary observation.
    #[must_use]
    pub fn observation(&self) -> &FxRateObservation {
        &self.observation
    }

    /// Returns the validated staleness in calendar days.
    #[must_use]
    pub const fn staleness_calendar_days(&self) -> u32 {
        self.staleness_calendar_days
    }
}

/// Verified evidence for a foreign exchange period adjustment.
#[derive(Clone, Debug, PartialEq)]
pub struct FxAdjustmentEvidence {
    start: FxBoundaryEvidence,
    end: FxBoundaryEvidence,
    fx_return: DecimalReturn,
}

impl FxAdjustmentEvidence {
    /// Creates and validates a new `FxAdjustmentEvidence`.
    ///
    /// # Errors
    /// Returns [`FxReturnContractError::BoundaryCurrencyPairMismatch`] if currency pairs differ.
    /// Returns [`FxReturnContractError::BoundaryFxRateKindMismatch`] if FX rate kinds differ.
    /// Returns [`FxReturnContractError::FxReturnMismatch`] if `fx_return` does not match the canonical return calculation.
    pub fn new(
        start: FxBoundaryEvidence,
        end: FxBoundaryEvidence,
        fx_return: DecimalReturn,
    ) -> Result<Self, FxReturnContractError> {
        if start.observation().pair() != end.observation().pair() {
            return Err(FxReturnContractError::BoundaryCurrencyPairMismatch {
                start_pair: start.observation().pair().clone(),
                end_pair: end.observation().pair().clone(),
            });
        }

        if start.observation().kind() != end.observation().kind() {
            return Err(FxReturnContractError::BoundaryFxRateKindMismatch {
                start_kind: start.observation().kind(),
                end_kind: end.observation().kind(),
            });
        }

        let calculated_return =
            calculate_fx_decimal_return(start.observation().rate(), end.observation().rate())?;

        if fx_return != calculated_return {
            return Err(FxReturnContractError::FxReturnMismatch {
                supplied: fx_return,
                calculated: calculated_return,
            });
        }

        Ok(Self {
            start,
            end,
            fx_return,
        })
    }

    /// Returns a reference to the start boundary evidence.
    #[must_use]
    pub fn start(&self) -> &FxBoundaryEvidence {
        &self.start
    }

    /// Returns a reference to the end boundary evidence.
    #[must_use]
    pub fn end(&self) -> &FxBoundaryEvidence {
        &self.end
    }

    /// Returns the verified FX decimal return.
    #[must_use]
    pub const fn fx_return(&self) -> DecimalReturn {
        self.fx_return
    }

    /// Returns the currency pair of the boundary observations.
    #[must_use]
    pub fn pair(&self) -> &CurrencyPair {
        self.start.observation().pair()
    }

    /// Returns the FX rate kind of the boundary observations.
    #[must_use]
    pub fn kind(&self) -> FxRateKind {
        self.start.observation().kind()
    }
}

/// Represents currency return adjustment status for portfolio components.
#[derive(Clone, Debug, PartialEq)]
pub enum CurrencyReturnAdjustment {
    /// No currency return adjustment required (same-currency holding).
    NotRequired,
    /// Foreign exchange return adjustment applied with auditable evidence.
    Applied(FxAdjustmentEvidence),
}
