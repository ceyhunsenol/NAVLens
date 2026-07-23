use super::fixtures::{align, candidate, date, holding};
use navlens_application::calculate_return_contribution;
use navlens_calendar::ReturnPeriod;

#[test]
fn preserves_component_and_gap_ordering() {
    let start = date(2026, 1, 1);
    let end = date(2026, 1, 2);
    let later = date(2026, 1, 3);
    let holdings = [
        holding("A", 0.1),
        holding("B", 0.1),
        holding("C", 0.1),
        holding("D", 0.1),
        holding("E", 0.1),
        holding("F", 0.1),
    ];
    let candidates = [
        candidate("A", &[(start, 100.0), (end, 105.0)]),
        candidate("C", &[(start, 100.0), (end, 105.0)]),
        candidate("D", &[(end, 100.0), (later, 105.0)]),
        candidate("F", &[(end, 100.0), (later, 105.0)]),
    ];
    let report = align(&holdings, &candidates, later);
    let period = ReturnPeriod::new(start, end).expect("test period should be valid");

    let result =
        calculate_return_contribution(&report, period).expect("calculation should succeed");

    let component_ids: Vec<_> = result
        .component_contributions()
        .iter()
        .map(|component| component.holding().instrument_id().as_str())
        .collect();
    let price_gap_ids: Vec<_> = result
        .price_gaps()
        .iter()
        .map(|gap| gap.holding().instrument_id().as_str())
        .collect();
    let return_gap_ids: Vec<_> = result
        .return_gaps()
        .iter()
        .map(|gap| gap.holding().instrument_id().as_str())
        .collect();

    assert_eq!(component_ids, ["A", "C"]);
    assert_eq!(price_gap_ids, ["B", "E"]);
    assert_eq!(return_gap_ids, ["D", "F"]);
}
