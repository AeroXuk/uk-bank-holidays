# Regions

The dataset has three region flags, each `true`/`false` per row:

| Flag | Covers |
|---|---|
| `england_and_wales` | England and Wales (one legal jurisdiction) |
| `scotland` | Scotland |
| `northern_ireland` | Northern Ireland |

These are the UK's three legal jurisdictions, so together they cover the whole United Kingdom. GOV.UK's
bank holiday feed uses the same split (`england-and-wales`, `scotland`, `northern-ireland`), and so did the original
blog post and the Banking and Financial Dealings Act 1971.

Not covered: the Crown Dependencies (Jersey, Guernsey, Isle of Man) and the Overseas Territories. They are not part of
the UK and set their own holidays.

England and Wales are one flag because every rule so far applies to both. If they ever diverge, the flag would be
split in a documented schema change.

## Per-region files

`data/uk_bank_holidays_<region>.{json,csv}` contain only the rows where that region's flag is true, without the
three flag columns. They are generated with `generate --region <region>`.

## Unverified region scope

Royal proclamations in the original post had no region information. They are currently flagged for the whole UK and
marked `verified: false` until a primary source confirms it.
