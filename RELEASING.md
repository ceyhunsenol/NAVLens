# Releasing NAVLens

NAVLens releases are built from annotated version tags. The release workflow
publishes GitHub Release artifacts; it does not publish to PyPI.

## Release preparation

1. Confirm the `master` branch passes Rust CI and Python CI.
2. Set the workspace version in `Cargo.toml` and update `Cargo.lock`.
3. Move the relevant `CHANGELOG.md` entries from `Unreleased` into a dated
   `## [X.Y.Z]` section.
4. Run the `Release` workflow manually. This builds and verifies Linux x86_64,
   Windows x86_64, macOS Apple Silicon, and macOS Intel wheels without
   publishing a release.
5. Install at least one downloaded workflow artifact in a clean environment
   and run the documented historical-prediction example.

## Publishing

Create and push an annotated tag that exactly matches the Cargo workspace
version:

```shell
git tag -a v0.1.0 -m "NAVLens v0.1.0"
git push origin v0.1.0
```

The tag-triggered workflow repeats all quality gates, rebuilds and verifies
every platform wheel, then creates the GitHub Release. A version mismatch or a
missing changelog release section stops publication.

Do not move or recreate a published release tag. Corrections require a new
patch version.
