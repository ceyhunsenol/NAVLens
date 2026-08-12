from importlib.metadata import EntryPoint, distribution

EXPECTED_CONSOLE_SCRIPTS = {
    "navlens-align-holdings-csv": "navlens.alignment.cli:main",
    "navlens-backtest-batch": "navlens.evaluation.tefas_batch_cli:main",
    "navlens-backtest-tefas": "navlens.evaluation.tefas_cli:main",
    "navlens-evaluate-historical-fx-reconciliation-csv": (
        "navlens.reconciliation.historical_fx_cli:main"
    ),
    "navlens-evaluate-historical-prediction-csv": ("navlens.prediction.historical_cli:main"),
    "navlens-evaluate-historical-reconciliation-csv": (
        "navlens.reconciliation.historical_cli:main"
    ),
    "navlens-fetch-tefas": "navlens.sources.tefas.cli:main",
    "navlens-fx-reconcile-fund-csv": "navlens.reconciliation.fx_cli:main",
    "navlens-fx-return-contribution-csv": ("navlens.alignment.fx_return_contribution_cli:main"),
    "navlens-predict-fund-csv": "navlens.prediction.cli:main",
    "navlens-predict-tefas": "navlens.prediction.tefas_cli:main",
    "navlens-predict-tefas-batch": "navlens.prediction.tefas_batch_cli:main",
    "navlens-reconcile-fund-csv": "navlens.reconciliation.cli:main",
    "navlens-return-contribution-csv": ("navlens.alignment.return_contribution_cli:main"),
}


def _navlens_console_scripts() -> dict[str, EntryPoint]:
    return {
        entry_point.name: entry_point
        for entry_point in distribution("navlens").entry_points
        if entry_point.group == "console_scripts"
    }


def test_published_console_script_contract_is_complete() -> None:
    entry_points = _navlens_console_scripts()

    assert {
        name: entry_point.value for name, entry_point in entry_points.items()
    } == EXPECTED_CONSOLE_SCRIPTS


def test_published_console_scripts_resolve_to_callable_entry_points() -> None:
    entry_points = _navlens_console_scripts()

    for name in sorted(entry_points):
        assert callable(entry_points[name].load()), name
