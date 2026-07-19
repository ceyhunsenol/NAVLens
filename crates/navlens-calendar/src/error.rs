use crate::MarketDate;
use std::error::Error;
use std::fmt::{Display, Formatter};

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum CalendarError {
    DuplicateSessionDate(MarketDate),
    InvalidDate { year: i32, month: u8, day: u8 },
    NoFutureOpenDate,
}

impl Display for CalendarError {
    fn fmt(&self, formatter: &mut Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::DuplicateSessionDate(date) => {
                write!(formatter, "duplicate session override for {date}")
            }
            Self::InvalidDate { year, month, day } => {
                write!(
                    formatter,
                    "invalid Gregorian date: {year:04}-{month:02}-{day:02}"
                )
            }
            Self::NoFutureOpenDate => formatter.write_str("no future open date is representable"),
        }
    }
}

impl Error for CalendarError {}
