use navlens_core::DecimalReturn;

#[derive(Clone, Copy, Debug, PartialEq)]
pub struct Observation {
    pub predicted: DecimalReturn,
    pub actual: DecimalReturn,
}
