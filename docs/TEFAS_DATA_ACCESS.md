# TEFAS data access

TEFAS states that it does not provide a documented public API for the Fund
Information Platform. NAVLens uses the JSON price endpoint consumed by the
official website and isolates that unstable provider contract inside one
adapter.

## Supported workflow

1. `TefasHttpClient` requests one fund's JSON price history over HTTP.
2. The unmodified response is stored atomically under `data/raw/tefas/` with its
   checksum and acquisition context.
3. `navlens.sources.tefas.parser` maps `tarih`, `fonKodu`, and `fiyat` into
   explicit provider records and filters the requested interval.
4. The shared source normalizer maps provider records to Rust
   `PriceObservation` values.
5. Rust validates the observations and calculates decimal returns.

The source response and prepared dataset are local artifacts and are not covered
by the repository's MIT license.

## What was verified

The official fund-returns page offers visible CSV and Excel exports. Its table
contains fund identity, risk, and aggregate return periods such as one month,
three months, and one year. Those aggregate-return values are not unit-price
observations and MUST NOT be substituted for the `unit_price` column.

The website price endpoint accepts one fund code and a fixed look-back period
of 1, 3, 6, 12, 36, or 60 months. The parser accepts only the verified price
fields; unrelated provider fields do not cross the source boundary.

The HTTP contract was last verified on 2026-07-20. A live AAL request returned
the `errorCode`, `errorMessage`, and `resultList` envelope with dated price
records.

## Automation boundary

- Acquisition uses direct HTTP rather than browser automation.
- The provider endpoint and payload names live only in the TEFAS client/query
  modules.
- `AcquireTefasPrices` runs with concurrency one, verifies cached payload
  checksums, and applies bounded retries with explicit delays.
- Transport and payload failures are reported through distinct source errors.
- Borsa Istanbul data products are a separate source and require their own
  access and licensing review.

## Provenance checklist

For every retained response artifact, record at least:

- source page and provider;
- download timestamp and timezone;
- selected fund and date interval;
- original filename and checksum;
- preparation command or script version;
- any rows rejected or changed during preparation.

These values are written to a machine-readable metadata sidecar and must not be
inferred from the file after training.

## Official references

- [TEFAS fund returns and API FAQ](https://www.tefas.gov.tr/tr/fon-getirileri?fundType=YAT)
- [TEFAS platform information and disclaimer](https://www.tefas.gov.tr/tr/hakkimizda)
- [Borsa Istanbul data products](https://www.borsaistanbul.com/tr/sayfa/189/veri-yayin-urunleri)
- [Independent 2026 endpoint implementation](https://github.com/burakyilmaz321/tefas-crawler/blob/main/tefas/crawler.py)
