use navlens_calendar::MarketDate;
use navlens_core::{ConfidenceLevel, DecimalReturn, FundId, PredictionInterval};
use navlens_prediction::{
    ModelDescriptor, PredictionError, PredictionMetadataField, PredictionRequest, ReturnPrediction,
    UtcTimestamp,
};

fn date(day: u8) -> MarketDate {
    MarketDate::new(2026, 7, day).expect("test date must be valid")
}

fn decimal_return(value: f64) -> DecimalReturn {
    DecimalReturn::new(value).expect("test return must be valid")
}

fn interval(lower: f64, upper: f64) -> PredictionInterval {
    PredictionInterval::new(
        decimal_return(lower),
        decimal_return(upper),
        ConfidenceLevel::new(0.9).expect("test confidence must be valid"),
    )
    .expect("test interval must be valid")
}

#[test]
fn creates_auditable_prediction_request() {
    let request = PredictionRequest::new(
        FundId::new("TRY-FUND-1").expect("test fund id must be valid"),
        date(19),
        date(20),
        UtcTimestamp::from_unix_seconds(2_000),
        UtcTimestamp::from_unix_seconds(1_900),
    )
    .expect("request must be valid");

    assert_eq!(request.fund_id().as_str(), "TRY-FUND-1");
    assert_eq!(request.target_date(), date(20));
    assert_eq!(request.generated_at().unix_seconds(), 2_000);
    assert_eq!(request.data_as_of().unix_seconds(), 1_900);
}

#[test]
fn rejects_target_on_or_before_prediction_date() {
    let result = PredictionRequest::new(
        FundId::new("TRY-FUND-1").expect("test fund id must be valid"),
        date(20),
        date(20),
        UtcTimestamp::from_unix_seconds(2_000),
        UtcTimestamp::from_unix_seconds(1_900),
    );

    assert_eq!(
        result,
        Err(PredictionError::PredictionNotBeforeTarget {
            prediction: date(20),
            target: date(20),
        })
    );
}

#[test]
fn rejects_data_from_after_generation_time() {
    let result = PredictionRequest::new(
        FundId::new("TRY-FUND-1").expect("test fund id must be valid"),
        date(19),
        date(20),
        UtcTimestamp::from_unix_seconds(2_000),
        UtcTimestamp::from_unix_seconds(2_001),
    );

    assert_eq!(
        result,
        Err(PredictionError::DataAfterGeneration {
            data_as_of_unix_seconds: 2_001,
            generated_at_unix_seconds: 2_000,
        })
    );
}

#[test]
fn creates_prediction_with_reproducibility_metadata() {
    let model = ModelDescriptor::new("weighted-baseline", "0.1.0", "market-v1")
        .expect("metadata must be valid");
    let prediction = ReturnPrediction::new(decimal_return(0.01), interval(-0.02, 0.03), model)
        .expect("prediction must be valid");

    assert_eq!(prediction.expected_return(), decimal_return(0.01));
    assert_eq!(
        prediction.interval().confidence_level(),
        ConfidenceLevel::new(0.9).expect("test confidence must be valid")
    );
    assert_eq!(prediction.model().name(), "weighted-baseline");
    assert_eq!(prediction.model().version(), "0.1.0");
    assert_eq!(prediction.model().feature_set_version(), "market-v1");
}

#[test]
fn rejects_point_estimate_outside_interval() {
    let model = ModelDescriptor::new("weighted-baseline", "0.1.0", "market-v1")
        .expect("metadata must be valid");
    let result = ReturnPrediction::new(decimal_return(0.04), interval(-0.02, 0.03), model);

    assert_eq!(
        result,
        Err(PredictionError::ExpectedReturnOutsideInterval {
            expected: 0.04,
            lower: -0.02,
            upper: 0.03,
        })
    );
}

#[test]
fn rejects_blank_or_unsafe_model_metadata() {
    assert_eq!(
        ModelDescriptor::new(" ", "0.1.0", "market-v1"),
        Err(PredictionError::EmptyMetadata(
            PredictionMetadataField::ModelName
        ))
    );
    assert_eq!(
        ModelDescriptor::new("weighted-baseline", "0.1.0\n", "market-v1"),
        Err(PredictionError::MetadataContainsControlCharacter(
            PredictionMetadataField::ModelVersion
        ))
    );
}
