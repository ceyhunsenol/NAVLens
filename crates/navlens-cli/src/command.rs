use crate::estimate;
use clap::{Args, Parser, Subcommand};
use navlens_application::ApplicationError;
use std::str::FromStr;

#[derive(Debug, Parser)]
#[command(
    name = "navlens",
    version,
    about = "Explainable investment fund research toolkit"
)]
pub struct Cli {
    #[command(subcommand)]
    command: Command,
}

#[derive(Debug, Subcommand)]
enum Command {
    /// Estimate a fund return from weighted market components.
    Estimate(EstimateArgs),
}

#[derive(Clone, Debug, Args)]
pub struct EstimateArgs {
    /// Weighted component in `WEIGHT:DECIMAL_RETURN` format.
    #[arg(long = "component", required = true, value_name = "WEIGHT:RETURN")]
    pub components: Vec<ComponentArg>,

    /// Daily expense rate in decimal units.
    #[arg(long, default_value_t = 0.0)]
    pub daily_expense_rate: f64,
}

#[derive(Clone, Copy, Debug, PartialEq)]
pub struct ComponentArg {
    pub weight: f64,
    pub market_return: f64,
}

impl FromStr for ComponentArg {
    type Err = String;

    fn from_str(value: &str) -> Result<Self, Self::Err> {
        let (weight, market_return) = value
            .split_once(':')
            .ok_or_else(|| "component must use WEIGHT:RETURN format".to_owned())?;

        Ok(Self {
            weight: weight
                .parse()
                .map_err(|_| format!("invalid component weight: {weight}"))?,
            market_return: market_return
                .parse()
                .map_err(|_| format!("invalid component return: {market_return}"))?,
        })
    }
}

pub fn execute(cli: Cli) -> Result<String, ApplicationError> {
    match cli.command {
        Command::Estimate(arguments) => estimate::execute(arguments),
    }
}
