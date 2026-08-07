use crate::calculate_return_contribution::CalculateReturnContributionError;
use navlens_calendar::FxRateSeries;
use navlens_core::{CurrencyPair, FxRateKind};
use std::collections::HashMap;

const FX_RATE_KINDS: [FxRateKind; 4] = [
    FxRateKind::NonCashBuying,
    FxRateKind::NonCashSelling,
    FxRateKind::CashBuying,
    FxRateKind::CashSelling,
];

pub(super) struct FxCandidateIndex<'a> {
    by_identity: HashMap<(CurrencyPair, FxRateKind), &'a FxRateSeries>,
}

impl<'a> FxCandidateIndex<'a> {
    pub(super) fn new(
        candidates: &'a [FxRateSeries],
    ) -> Result<Self, CalculateReturnContributionError> {
        let mut by_identity = HashMap::with_capacity(candidates.len());
        for candidate in candidates {
            let pair = candidate.pair().clone();
            let kind = candidate.kind();
            if by_identity
                .insert((pair.clone(), kind), candidate)
                .is_some()
            {
                return Err(CalculateReturnContributionError::DuplicateFxCandidate { pair, kind });
            }
        }
        Ok(Self { by_identity })
    }

    pub(super) fn get(&self, pair: &CurrencyPair, kind: FxRateKind) -> Option<&'a FxRateSeries> {
        self.by_identity.get(&(pair.clone(), kind)).copied()
    }

    pub(super) fn available_kinds(&self, pair: &CurrencyPair) -> Vec<FxRateKind> {
        FX_RATE_KINDS
            .into_iter()
            .filter(|kind| self.by_identity.contains_key(&(pair.clone(), *kind)))
            .collect()
    }
}
