use std::process::Command;

#[test]
fn estimates_weighted_return() {
    let output = Command::new(env!("CARGO_BIN_EXE_navlens"))
        .args([
            "estimate",
            "--component",
            "0.7:0.02",
            "--component",
            "0.2:-0.01",
            "--component",
            "0.1:0.001",
            "--daily-expense-rate",
            "0.0001",
        ])
        .output()
        .expect("CLI should run");

    assert!(output.status.success());
    let stdout = String::from_utf8(output.stdout).expect("stdout should be UTF-8");
    assert!(stdout.contains("estimated_return_decimal=0.0120000000"));
    assert!(stdout.contains("estimated_return_percent=1.200000%"));
}

#[test]
fn reports_domain_validation_errors() {
    let output = Command::new(env!("CARGO_BIN_EXE_navlens"))
        .args(["estimate", "--component", "1.2:0.02"])
        .output()
        .expect("CLI should run");

    assert!(!output.status.success());
    let stderr = String::from_utf8(output.stderr).expect("stderr should be UTF-8");
    assert!(stderr.contains("portfolio weight must be between zero and one"));
}
