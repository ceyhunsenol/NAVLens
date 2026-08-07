use crate::align_holdings_prices::PortfolioCoverageReport;
use crate::calculate_return_contribution::ReturnCoverageGap;
use crate::return_coverage_breakdown::ReturnCoverageBreakdown;

/// Constructs a `ReturnCoverageBreakdown` from an existing report and newly identified return gaps.
pub(crate) fn construct_return_coverage_breakdown(
    report: &PortfolioCoverageReport,
    return_gaps: Vec<ReturnCoverageGap>,
) -> ReturnCoverageBreakdown {
    ReturnCoverageBreakdown::new(
        report.weights().covered_weight(),
        report.uncovered_listed().to_vec(),
        return_gaps,
    )
}
