/// Component whose decimal return supplies a gross-return factor.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum GrossReturnComponent {
    /// Return of the underlying security.
    Security,
    /// Return of the foreign-exchange rate.
    ForeignExchange,
}
