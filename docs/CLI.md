# Command-line interface

The `navlens` binary is the first executable adapter for NAVLens. It parses
transport input, creates application commands, invokes one use case, and formats
the result. It does not implement financial calculations.

`main.rs` remains a process composition boundary only: parse arguments, invoke
the command dispatcher, write output/error, and select an exit code. Command
definitions, mapping, formatting, and use-case behavior live in focused modules
or inner crates.

## Estimate a weighted portfolio return

Each `--component` uses `WEIGHT:DECIMAL_RETURN` format. Weights must sum to one.
Returns and the daily expense rate use decimal units.

```shell
cargo run -p navlens-cli -- estimate \
  --component 0.7:0.02 \
  --component 0.2:-0.01 \
  --component 0.1:0.001 \
  --daily-expense-rate 0.0001
```

Expected output:

```text
estimated_return_decimal=0.0120000000
estimated_return_percent=1.200000%
```

The command flow is:

```text
CLI arguments
    → EstimatePortfolioReturnCommand
    → navlens-application use case
    → navlens-core domain calculation
    → application result
    → CLI output
```

Invalid syntax is reported by `clap`. Domain violations such as negative or
out-of-range weights are mapped to application errors and result in a non-zero
process exit code.
