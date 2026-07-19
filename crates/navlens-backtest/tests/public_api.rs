use navlens_backtest::{BacktestError, BacktestSeries, Observation, evaluate};
use navlens_calendar::MarketDate;
use navlens_core::{ConfidenceLevel, DecimalReturn, FundId, PredictionInterval};

fn date(year: i32, month: u8, day: u8) -> MarketDate {
    MarketDate::new(year, month, day).expect("test date should be valid")
}

fn return_of(value: f64) -> DecimalReturn {
    DecimalReturn::new(value).expect("test return should be finite")
}

fn observation(
    prediction_date: MarketDate,
    target_date: MarketDate,
    predicted: f64,
    actual: f64,
) -> Observation {
    Observation::new(
        prediction_date,
        target_date,
        return_of(predicted),
        return_of(actual),
    )
    .expect("test observation should be valid")
}

fn fund_id() -> FundId {
    FundId::new("ABC").expect("test fund identifier should be valid")
}

fn interval(lower: f64, upper: f64, confidence: f64) -> PredictionInterval {
    PredictionInterval::new(
        return_of(lower),
        return_of(upper),
        ConfidenceLevel::new(confidence).expect("test confidence should be valid"),
    )
    .expect("test interval should be valid")
}

#[test]
fn evaluates_prediction_metrics() {
    let observations = vec![
        observation(date(2026, 7, 14), date(2026, 7, 15), 0.01, 0.02),
        observation(date(2026, 7, 15), date(2026, 7, 16), -0.02, -0.01),
        observation(date(2026, 7, 16), date(2026, 7, 17), 0.01, -0.01),
    ];
    let series = BacktestSeries::new(fund_id(), observations).expect("valid series");

    let metrics = evaluate(&series);
    assert_eq!(metrics.sample_count, 3);
    assert!((metrics.mean_absolute_error - (0.04 / 3.0)).abs() < 1e-12);
    assert!(metrics.mean_error.abs() < 1e-12);
    assert!((metrics.root_mean_squared_error - (0.0006_f64 / 3.0).sqrt()).abs() < 1e-12);
    assert!((metrics.direction_accuracy - (2.0 / 3.0)).abs() < 1e-12);
    assert_eq!(metrics.interval, None);
}

#[test]
fn evaluates_prediction_interval_metrics() {
    let observations = vec![
        observation(date(2026, 7, 14), date(2026, 7, 15), 0.01, 0.02)
            .with_prediction_interval(interval(-0.01, 0.03, 0.9)),
        observation(date(2026, 7, 15), date(2026, 7, 16), 0.01, 0.05)
            .with_prediction_interval(interval(-0.01, 0.03, 0.9)),
        observation(date(2026, 7, 16), date(2026, 7, 17), -0.01, -0.02)
            .with_prediction_interval(interval(-0.03, 0.01, 0.9)),
    ];
    let series = BacktestSeries::new(fund_id(), observations).expect("valid series");
    let metrics = evaluate(&series).interval.expect("interval metrics");

    assert_eq!(metrics.sample_count, 3);
    assert!((metrics.confidence_level.value() - 0.9).abs() < f64::EPSILON);
    assert!((metrics.coverage - (2.0 / 3.0)).abs() < 1e-12);
    assert!((metrics.mean_width - 0.04).abs() < 1e-12);
}

#[test]
fn rejects_mixed_confidence_levels() {
    let observations = vec![
        observation(date(2026, 7, 14), date(2026, 7, 15), 0.01, 0.02)
            .with_prediction_interval(interval(-0.01, 0.03, 0.9)),
        observation(date(2026, 7, 15), date(2026, 7, 16), 0.01, 0.02)
            .with_prediction_interval(interval(-0.01, 0.03, 0.95)),
    ];

    assert_eq!(
        BacktestSeries::new(fund_id(), observations),
        Err(BacktestError::MixedConfidenceLevels {
            expected: ConfidenceLevel::new(0.9).expect("valid confidence"),
            actual: ConfidenceLevel::new(0.95).expect("valid confidence"),
        })
    );
}

#[test]
fn rejects_prediction_on_or_after_target_date() {
    let same_date = date(2026, 7, 15);

    assert_eq!(
        Observation::new(same_date, same_date, return_of(0.01), return_of(0.02)),
        Err(BacktestError::PredictionNotBeforeTarget {
            prediction: same_date,
            target: same_date,
        })
    );
}

#[test]
fn rejects_empty_backtest_series() {
    assert_eq!(
        BacktestSeries::new(fund_id(), vec![]),
        Err(BacktestError::NoObservations)
    );
}

#[test]
fn rejects_duplicate_target_dates() {
    let target = date(2026, 7, 16);
    let observations = vec![
        observation(date(2026, 7, 14), target, 0.01, 0.02),
        observation(date(2026, 7, 15), target, 0.02, 0.03),
    ];

    assert_eq!(
        BacktestSeries::new(fund_id(), observations),
        Err(BacktestError::DuplicateTargetDate(target))
    );
}

#[test]
fn rejects_non_chronological_target_dates() {
    let previous = date(2026, 7, 17);
    let current = date(2026, 7, 16);
    let observations = vec![
        observation(date(2026, 7, 14), previous, 0.01, 0.02),
        observation(date(2026, 7, 15), current, 0.02, 0.03),
    ];

    assert_eq!(
        BacktestSeries::new(fund_id(), observations),
        Err(BacktestError::NonChronologicalTargetDate { previous, current })
    );
}

#[test]
fn rejects_non_chronological_prediction_dates() {
    let previous = date(2026, 7, 15);
    let current = date(2026, 7, 14);
    let observations = vec![
        observation(previous, date(2026, 7, 16), 0.01, 0.02),
        observation(current, date(2026, 7, 17), 0.02, 0.03),
    ];

    assert_eq!(
        BacktestSeries::new(fund_id(), observations),
        Err(BacktestError::NonChronologicalPredictionDate { previous, current })
    );
}

#[test]
fn treats_positive_negative_and_flat_as_distinct_directions() {
    let observations = vec![
        observation(date(2026, 7, 14), date(2026, 7, 15), 0.0, -0.0),
        observation(date(2026, 7, 15), date(2026, 7, 16), 0.0, 0.01),
    ];
    let series = BacktestSeries::new(fund_id(), observations).expect("valid series");

    assert!((evaluate(&series).direction_accuracy - 0.5).abs() < 1e-12);
}
