use crate::alignment_policy::PyAlignmentPolicy;
use crate::holding_position::PyHoldingPosition;
use crate::portfolio_coverage_report::PyPortfolioCoverageReport;
use crate::security_price_history_candidate::PySecurityPriceHistoryCandidate;
use navlens_application::align_holdings_prices as core_align_holdings_prices;
use pyo3::prelude::*;

#[pyfunction]
#[pyo3(signature = (holdings, candidates, policy))]
pub(crate) fn align_holdings_prices(
    holdings: Vec<PyHoldingPosition>,
    candidates: Vec<PySecurityPriceHistoryCandidate>,
    policy: &PyAlignmentPolicy,
) -> PyResult<PyPortfolioCoverageReport> {
    let domain_holdings: Vec<_> = holdings
        .into_iter()
        .map(PyHoldingPosition::into_inner)
        .collect();
    let domain_candidates: Vec<_> = candidates
        .into_iter()
        .map(PySecurityPriceHistoryCandidate::into_inner)
        .collect();
    let domain_policy = policy.clone_inner();

    let report = core_align_holdings_prices(&domain_holdings, &domain_candidates, &domain_policy)
        .map_err(crate::error::validation_error)?;

    Ok(PyPortfolioCoverageReport::from_inner(report))
}
