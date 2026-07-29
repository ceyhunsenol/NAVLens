/// The economic type of an exchange rate distinguishing non-cash and physical banknote rates.
#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub enum FxRateKind {
    /// Rate applied to non-cash transfers (buying rate for foreign currency).
    NonCashBuying,
    /// Rate applied to non-cash transfers (selling rate for foreign currency).
    NonCashSelling,
    /// Rate applied to physical banknote transactions (buying rate for foreign currency).
    CashBuying,
    /// Rate applied to physical banknote transactions (selling rate for foreign currency).
    CashSelling,
}
