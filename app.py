import hmac
import logging

import pandas as pd
import streamlit as st

from attendance import STATUSES, export_csv, parse_workbook, recurring_people, sheet_names
from storage import connect, load_records, save_records, load_imports
from dashboard import render_dashboard

st.set_page_config(page_title='Polk County | Attendance', page_icon='📋', layout='wide')
st.markdown('''<style>
.block-container {max-width:1320px;padding-top:2rem;}
[data-testid="stAppViewContainer"] {background:#f7f9fd;}
[data-testid="stSidebar"] {background:#eef2fa;border-right:1px solid #e0e7f1;}
h1 {letter-spacing:-.055em;font-weight:800 !important;color:#152442;}
h2,h3 {color:#213354;letter-spacing:-.025em;}
[data-testid="stMetric"] {background:white;padding:1.25rem;border-radius:16px;border:1px solid #e2e8f3;border-top:4px solid #5b7cfa;box-shadow:0 4px 18px #1e3a5f08;}
[data-testid="stMetricLabel"] {color:#65718a;}
[data-testid="stMetricValue"] {color:#152442;font-weight:750;font-size:2.2rem;}
[data-testid="stVerticalBlockBorderWrapper"]>div {border-radius:16px !important;background:white;}
.stButton button[kind="primary"] {background:#4f6ef7;border-color:#4f6ef7;border-radius:10px;}
.credit {text-align:center;color:#64748b;padding:2rem 0;font-size:.9rem;}
@media (prefers-color-scheme:dark) {
[data-testid="stAppViewContainer"] {background:#101827;}
[data-testid="stSidebar"] {background:#152035;border-color:#29364d;}
h1,h2,h3 {color:#e5ecfa;}
[data-testid="stMetric"], [data-testid="stVerticalBlockBorderWrapper"]>div {background:#18253a;border-color:#2c3b55;}
[data-testid="stMetricValue"] {color:#e5ecfa;}
[data-testid="stMetricLabel"] {color:#afbed6;}
}
</style>''', unsafe_allow_html=True)
st.title('Polk County Attendance')
st.caption('No shows, late cancellations and recurring incidents — all in one place.')
# Render before any stop so attribution also appears on login/setup screens.
st.sidebar.markdown('---')
st.sidebar.caption('Hecho con Love por Rodrigo Bermudez')

try:
    settings = st.secrets.to_dict()
except FileNotFoundError:
    settings = {}
password = settings.get('app_password', '')
if not password or password.startswith('REPLACE'):
    st.info('Setup required: add your access password and Firebase service account to Streamlit Secrets.')
    st.caption('See README.md and .streamlit/secrets.toml.example for deployment settings.')
    st.stop()
if not st.session_state.get('authenticated'):
    st.subheader('Sign in')
    with st.form('login'):
        entered = st.text_input('Access password', type='password')
        if st.form_submit_button('Sign in', type='primary'):
            if hmac.compare_digest(entered.encode(), password.encode()):
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error('Incorrect password.')
    st.stop()
if st.sidebar.button('Sign out'):
    st.session_state.clear()
    st.rerun()

@st.cache_resource
def database(config):
    return connect(config)

client = None
try:
    if 'firebase' in settings:
        client = database(dict(settings['firebase']))
except Exception:
    logging.exception('Firebase initialization failed')
    st.warning('Firebase connection failed. Check service account credentials. Import previews remain available.')
if client is None:
    st.info('Firebase is not connected. You can preview a workbook; saving and history require Firebase Secrets.')

records = []
history_loaded = False
if client is not None:
    try:
        records = load_records(client)
        history_loaded = True
    except Exception:
        logging.exception('History read failed')
        st.error('History could not be loaded. Check Firebase access and refresh.')

page = st.sidebar.radio('Workspace', ['Attendance Report', 'Import Excel', 'Recurring People', 'History'])
st.sidebar.caption('District: Polk County')
if history_loaded:
    st.sidebar.success('Cloud history connected')
    st.sidebar.caption(f'{len(records):,} saved incidents · refreshed on each page load')
else:
    st.sidebar.warning('Cloud history unavailable')
if st.sidebar.button('Refresh history'):
    st.rerun()


DISPLAY = {'name': 'Employee', 'ats_id': 'ATS / KSN ID', 'email': 'Email', 'date': 'Incident date',
           'status': 'Incident type', 'school': 'School', 'case_number': 'Case / Confirmation #',
           'source_type': 'Source type', 'notes': 'Notes'}


def table(rows, filename):
    if not rows:
        st.info('No records to display.')
        return
    display = [{label: r.get(key, '') for key, label in DISPLAY.items()} for r in rows]
    st.dataframe(pd.DataFrame(display), hide_index=True, width='stretch')
    st.download_button('Download CSV', export_csv(display), filename, 'text/csv')


if page == 'Import Excel':
    st.subheader('Import Excel')
    st.write('Upload the tracker or a daily import workbook. Only Polk County records will be included.')
    uploaded = st.file_uploader('Attendance workbook', type=['xlsx', 'xlsm'])
    st.caption('Macros are not executed. Use Occurrence Log to import existing history; use a daily import sheet for new records.')
    if uploaded:
        try:
            data = uploaded.getvalue()
            available = sheet_names(data)
            if not available:
                st.error('No supported sheets found. Expected Occurrence Log, Assisted, Unassisted or No Show Import.')
            else:
                sheet = st.selectbox('Source sheet', available)
                preview, summary, errors = parse_workbook(data, sheet)
                st.subheader('Import review')
                st.dataframe(pd.DataFrame([{'Check': key, 'Count': value} for key, value in summary.items()]),
                             hide_index=True, width='stretch')
                st.caption('Unassisted cancellations count as Late Cancellation. Other districts and template rows are excluded.')
                if summary.get('Name-based identities'):
                    st.warning('Some employees have no ATS / KSN ID and are matched by normalized name. Check for same-name employees and name changes before saving.')
                exclude_errors = False
                if errors:
                    st.warning('These Polk rows cannot be imported. Correct them in the workbook or explicitly exclude them.')
                    st.dataframe(pd.DataFrame(errors), hide_index=True)
                    exclude_errors = st.checkbox(f'Exclude these {len(errors)} invalid rows and save valid incidents only')
                table(preview, 'polkcounty_import_preview.csv')
                if history_loaded:
                    existing_ids = {r['id'] for r in records}
                    repeats = sum(r['id'] in existing_ids for r in preview)
                    st.info(f'{len(preview) - repeats} new incidents; {repeats} existing incidents will be updated.')
                st.caption('One occurrence per employee, incident date and incident type. Reimporting will not increase counts.')
                if st.button('Save to history', type='primary', disabled=not preview or (bool(errors) and not exclude_errors) or not history_loaded):
                    confirmed = [0]
                    progress = st.progress(0)
                    def on_progress(count):
                        confirmed[0] = count
                        progress.progress(count / len(preview))
                    try:
                        saved = save_records(client, preview, on_progress, import_info={'filename': uploaded.name, 'sheet': sheet, 'excluded_invalid_rows': len(errors)})
                        st.session_state['save_notice'] = f'Saved {saved} incidents to Firebase.'
                        st.rerun()
                    except Exception:
                        logging.exception('Import save failed')
                        st.error(f'Save interrupted after {confirmed[0]} confirmed records. Retry the same workbook safely.')
        except Exception:
            logging.exception('Workbook parse failed')
            st.error('Could not read this workbook. Check the sheet format and dates.')
    if st.session_state.get('save_notice'):
        st.success(st.session_state.pop('save_notice'))
elif page == 'Attendance Report':
    st.subheader('Attendance Report')
    if not history_loaded:
        st.info('Connect Firebase to view your report.')
    elif not records:
        st.info('Your history is empty. Import an Excel workbook to begin.')
    else:
        render_dashboard(records, table)
elif page == 'Recurring People':
    st.subheader('Recurring People')
    st.caption('Employees with repeated incidents across all saved Polk County history. Updated automatically after each import.')
    threshold = st.number_input('Minimum incidents', min_value=2, value=2)
    result = recurring_people(records, int(threshold)) if history_loaded else []
    if not history_loaded:
        st.info('Connect Firebase to view recurring people.')
    elif not result:
        st.info('No employees meet this threshold.')
    else:
        st.metric('Recurring employees', len(result))
        st.dataframe(pd.DataFrame(result), hide_index=True, width='stretch')
        st.download_button('Download recurring people', export_csv(result), 'polkcounty_recurring.csv', 'text/csv')
else:
    st.subheader('History')
    st.caption('All imported Polk County incidents. Data is stored in Firebase Firestore.')
    types = st.multiselect('Incident types', STATUSES, default=list(STATUSES))
    search = st.text_input('Search employee, ATS / KSN ID or school').strip().casefold()
    selected = [r for r in records if r['status'] in types and
                (not search or search in ' '.join([r.get('name',''), r.get('ats_id',''), r.get('school','')]).casefold())]
    if history_loaded:
        table(sorted(selected, key=lambda r: r['date'], reverse=True), 'polkcounty_history.csv')
        with st.expander('Import history'):
            try:
                imports = load_imports(client)
                if imports:
                    st.dataframe(pd.DataFrame(imports), hide_index=True, width='stretch')
                else:
                    st.caption('No import logs yet. New uploads will appear here.')
            except Exception:
                st.warning('Import log unavailable. Saved incidents are still displayed above.')
    else:
        st.info('Connect Firebase to view history.')

st.markdown('<div class="credit">Hecho con Love por Rodrigo Bermudez</div>', unsafe_allow_html=True)
