# Features

## Implemented
- English application; requested Spanish attribution: Hecho con Love por Rodrigo Bermudez.
- Sign in with shared team password before any data access.
- XLSX / XLSM imports; macros never executed; headers detected automatically.
- Occurrence Log / Assisted / Unassisted / No Show Import compatibility.
- Polk County only; other districts excluded.
- No Show and Late Cancellation reports; Unassisted included in Late Cancellation.
- Import preview, excluded-row counts; invalid rows require correction or explicit exclusion.
- ATS / KSN identity with normalized-name fallback warning.
- Deterministic employee/date/type deduplication and safe repeat imports.
- Firebase project subparty, collection polkcounty_incidents, merged writes.
- Date-filtered counts, monthly chart, employee count and CSV export.
- Historical recurring people, default 2 combined incidents, adjustable threshold.
- Searchable history; CSV formula injection protection.

## Limitations / pending
- Shared password, no individual identities or audit users.
- Name-based matching may merge same-name people; ID changes require reconciliation.
- No full assignment denominator, so no attendance rate.
- Addressed and dashboard summaries are not imported as incidents.
- Firebase console currently unavailable to the browser account; no content deleted.
- Real Firebase credentials and Streamlit deployment remain user setup steps.
- Hosted read/write must be verified after setup.

Keep this file updated when behavior changes.

## Validation
- 8 automated tests passed: parsing, filtering, deduplication, invalid rows, recurrence, CSV protection, sign-in/sign-out and report UI with synthetic history.
- Source workbook: 617 valid unique Polk incidents (23 No Show; 594 Late Cancellation, including 207 Unassisted), 2 duplicates, 7 invalid rows without employee identity; 99 recurring identities at threshold 2.
- Dates: August 11 through October 6, 2026. Real workbook and personal data are excluded from Git.
