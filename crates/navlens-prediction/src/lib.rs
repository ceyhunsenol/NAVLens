//! Model-independent request, result, and provenance contracts for predictions.

mod error;
mod model_descriptor;
mod request;
mod return_prediction;
mod utc_timestamp;

pub use error::{PredictionError, PredictionMetadataField};
pub use model_descriptor::ModelDescriptor;
pub use request::PredictionRequest;
pub use return_prediction::ReturnPrediction;
pub use utc_timestamp::UtcTimestamp;
