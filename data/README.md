# Local data workspace

NAVLens source code is MIT licensed, but downloaded market data retains the
terms of its provider. Real datasets are therefore local by default.

```text
data/
├── raw/        # Unmodified provider downloads; ignored by Git
└── processed/  # Reproducible derived datasets; ignored by Git
```

Commit only small synthetic fixtures under a test directory. Dataset provenance
such as source name, fund code, requested period, retrieval timestamp, and
transformation version should be stored separately from model code.
