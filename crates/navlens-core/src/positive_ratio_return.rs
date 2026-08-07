use crate::{CoreError, DecimalReturn};

pub(crate) fn calculate_positive_ratio_return(
    previous: f64,
    current: f64,
) -> Result<DecimalReturn, CoreError> {
    DecimalReturn::new((current / previous) - 1.0)
}
