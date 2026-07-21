/// Provider-neutral class of an asset held by a fund.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
#[non_exhaustive]
pub enum AssetClass {
    Equity,
    DebtSecurity,
    Repo,
    Deposit,
    InvestmentFund,
    ExchangeTradedFund,
    PreciousMetal,
    Derivative,
    Cash,
    Other,
}
