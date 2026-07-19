mod command;
mod estimate;

use clap::Parser;
use command::Cli;
use std::process::ExitCode;

fn main() -> ExitCode {
    match command::execute(Cli::parse()) {
        Ok(output) => {
            println!("{output}");
            ExitCode::SUCCESS
        }
        Err(error) => {
            eprintln!("error: {error}");
            ExitCode::FAILURE
        }
    }
}
