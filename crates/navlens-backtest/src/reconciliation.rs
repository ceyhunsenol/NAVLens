use crate::BacktestError;
use navlens_calendar::ReturnPeriod;
use navlens_core::FundReturnReconciliation;
use std::collections::HashSet;

/// An observation of one fund return reconciliation for a specific period.
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct ReconciliationObservation {
    period: ReturnPeriod,
    reconciliation: FundReturnReconciliation,
}

impl ReconciliationObservation {
    /// Creates a new reconciliation observation.
    #[must_use]
    pub const fn new(period: ReturnPeriod, reconciliation: FundReturnReconciliation) -> Self {
        Self {
            period,
            reconciliation,
        }
    }

    /// The return period of the reconciliation observation.
    #[must_use]
    pub const fn period(&self) -> ReturnPeriod {
        self.period
    }

    /// The core fund return reconciliation result.
    #[must_use]
    pub const fn reconciliation(&self) -> FundReturnReconciliation {
        self.reconciliation
    }
}

/// A validated non-empty, chronologically ordered sequence of reconciliation observations.
#[derive(Clone, Debug, PartialEq)]
pub struct ReconciliationSeries {
    observations: Vec<ReconciliationObservation>,
}

impl ReconciliationSeries {
    /// Creates a new non-empty, chronologically ordered reconciliation series.
    ///
    /// # Errors
    /// Returns [`BacktestError::NoReconciliationObservations`] if empty, [`BacktestError::DuplicateReconciliationPeriod`]
    /// for duplicate periods, or [`BacktestError::NonChronologicalReconciliationPeriod`] if period end dates
    /// are not strictly increasing.
    pub fn new(observations: Vec<ReconciliationObservation>) -> Result<Self, BacktestError> {
        if observations.is_empty() {
            return Err(BacktestError::NoReconciliationObservations);
        }

        let mut seen_periods = HashSet::with_capacity(observations.len());
        let mut previous_period: Option<ReturnPeriod> = None;
        for observation in &observations {
            let current = observation.period();

            if !seen_periods.insert(current) {
                return Err(BacktestError::DuplicateReconciliationPeriod(current));
            }
            if let Some(previous) = previous_period
                && current.period_end_date() <= previous.period_end_date()
            {
                return Err(BacktestError::NonChronologicalReconciliationPeriod {
                    previous: previous.period_end_date(),
                    current: current.period_end_date(),
                });
            }
            previous_period = Some(current);
        }

        Ok(Self { observations })
    }

    /// Returns the sequence of reconciliation observations.
    #[must_use]
    pub fn observations(&self) -> &[ReconciliationObservation] {
        &self.observations
    }
}

/// Aggregate evaluation metrics for a sequence of fund return reconciliations.
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct ReconciliationMetrics {
    sample_count: usize,
    mean_absolute_residual: f64,
    mean_residual: f64,
    root_mean_squared_residual: f64,
    mean_return_coverage: f64,
    full_return_coverage_ratio: f64,
}

impl ReconciliationMetrics {
    /// The total number of evaluated reconciliation observations.
    #[must_use]
    pub const fn sample_count(&self) -> usize {
        self.sample_count
    }

    /// The mean absolute value of the reconciliation residuals.
    #[must_use]
    pub const fn mean_absolute_residual(&self) -> f64 {
        self.mean_absolute_residual
    }

    /// The arithmetic mean of the reconciliation residuals.
    #[must_use]
    pub const fn mean_residual(&self) -> f64 {
        self.mean_residual
    }

    /// The root-mean-squared value of the reconciliation residuals.
    #[must_use]
    pub const fn root_mean_squared_residual(&self) -> f64 {
        self.root_mean_squared_residual
    }

    /// The mean return coverage ratio across all observations.
    #[must_use]
    pub const fn mean_return_coverage(&self) -> f64 {
        self.mean_return_coverage
    }

    /// The proportion of observations with full return coverage (1.0).
    #[must_use]
    pub const fn full_return_coverage_ratio(&self) -> f64 {
        self.full_return_coverage_ratio
    }
}

/// Evaluates aggregate metrics for a validated chronological reconciliation series.
#[must_use]
pub fn evaluate_reconciliations(series: &ReconciliationSeries) -> ReconciliationMetrics {
    let observations = series.observations();
    let mut absolute_residual_sum = 0.0;
    let mut residual_sum = 0.0;
    let mut squared_residual_sum = 0.0;
    let mut coverage_sum = 0.0;
    let mut full_coverage_count = 0usize;

    for obs in observations {
        let residual = obs.reconciliation().reconciliation_residual().value();
        let contrib = obs.reconciliation().observed_portfolio_contribution();

        absolute_residual_sum += residual.abs();
        residual_sum += residual;
        squared_residual_sum += residual * residual;
        coverage_sum += contrib.return_coverage().value();
        if contrib.has_full_coverage() {
            full_coverage_count += 1;
        }
    }

    #[allow(clippy::cast_precision_loss)]
    let count = observations.len() as f64;
    #[allow(clippy::cast_precision_loss)]
    let full_return_coverage_ratio = full_coverage_count as f64 / count;

    ReconciliationMetrics {
        sample_count: observations.len(),
        mean_absolute_residual: absolute_residual_sum / count,
        mean_residual: residual_sum / count,
        root_mean_squared_residual: (squared_residual_sum / count).sqrt(),
        mean_return_coverage: coverage_sum / count,
        full_return_coverage_ratio,
    }
}
