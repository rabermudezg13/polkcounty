# Polk County Attendance

English Streamlit app for importing the Late Cancellation Tracker, reporting **No Show** and **Late Cancellation** incidents, retaining history in Firebase Firestore, and identifying recurring employees.

Hecho con Love por Rodrigo Bermudez

## Deploy on Streamlit

1. Create an app at https://share.streamlit.io/ using GitHub repository `rabermudezg13/polkcounty`, branch `main`, entrypoint `app.py`, Python 3.12.
2. Before opening the app, paste the configuration from `.streamlit/secrets.toml.example` into **Advanced settings → Secrets**, replacing every placeholder.
3. Set a strong `app_password`. The app requires **Sign in** before data access. This version uses a shared team password, not individual Google accounts.
4. In Firebase project **subparty**, enable a Firestore database named `(default)` if needed. Obtain a service-account credential with Firestore access and use its fields in the `[firebase]` secrets section. Keep the credential out of GitHub.
5. Open the app, sign in, upload your `.xlsm` or `.xlsx`, select **Occurrence Log**, review the Polk-only preview, then select **Save to history**.
6. Verify **Attendance Report**, **Recurring People**, and **History**. Import the same workbook again to confirm counts do not increase.

The app uses collection `polkcounty_incidents`. It neither deletes nor changes unrelated Firebase content. Do not make Firestore public: Python's server SDK uses service-account IAM permissions, not browser security rules.

## Import rules

- Supported sheets: **Occurrence Log**, **Assisted**, **Unassisted**, **No Show Import**. Headers are detected in the first 15 rows.
- Districts `Polk`, `Polk County`, `Polk County Schools`, and their final pipe-delimited components are included. Other or missing districts are excluded.
- **Unassisted** counts as **Late Cancellation**, preserving the source type for review.
- One incident per employee, date, and incident type. Reimporting merges the same deterministic Firestore document.
- ATS / KSN ID is the employee identity. Missing IDs fall back to normalized employee name, matching the source tracker's convention. Same-name employees and later changes to IDs/names need reconciliation; the app warns before import.
- Recurring employees have at least two incidents by default; the threshold is adjustable. Recurrence uses all saved history, independently of the report date filter.
- Dates use US month/day/year or Excel date values. Invalid Polk rows are displayed for correction; saving requires correcting them or explicitly choosing to exclude them.
- The app reads values and does not execute workbook macros or instructions. It does not import Dashboard, Dashboard Calc or Addressed as incident sources: those are summaries/follow-up records, not additional incidents.
- Reports count incidents, not all assignments. An attendance/no-show rate cannot be calculated from this tracker alone.

## Local development

```sh
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# Replace secrets locally; never commit this file.
streamlit run app.py
```

## Validation

```sh
python -m unittest discover -s tests
python -m compileall app.py attendance.py storage.py
```

Firebase persistence and the hosted deployment must be verified after real credentials are configured. The actual workbook is not committed to this repository.

## Persistent cloud data

- Firestore `(default)` in `subparty` stores incidents in `polkcounty_incidents`. Streamlit sessions and restarts do not own this data.
- `polkcounty_imports` stores import filename, worksheet, excluded invalid count, saved count, timestamps and completion status. Each batch atomically saves incidents and its progress. If interrupted, committed incidents remain available; repeat the upload to finish without duplication.
- `polkcounty_metadata/app` retains schema version and the last successful import.
- Existing cloud history is loaded on every page run. **Refresh history** reloads the current cloud data.
- The dashboard applies date and school filters to cards, charts, recurring counts and details. The separate Recurring People page covers all saved history.
- CSV exports provide a downloadable copy; they are not an automatic database backup.

Published app: https://polkcounty-vv8yth5wdoz98uadkydq2f.streamlit.app/
