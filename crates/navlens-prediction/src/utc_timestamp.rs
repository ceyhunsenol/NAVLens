/// A UTC instant represented as seconds since the Unix epoch.
///
/// Conversion to formatted timestamps belongs to boundary adapters. Keeping the
/// representation explicit prevents local-time values from crossing the domain
/// boundary accidentally.
#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub struct UtcTimestamp(i64);

impl UtcTimestamp {
    #[must_use]
    pub const fn from_unix_seconds(value: i64) -> Self {
        Self(value)
    }

    #[must_use]
    pub const fn unix_seconds(self) -> i64 {
        self.0
    }
}
