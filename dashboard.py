"""Summary-first visuals using the same filtered incidents as the detail table."""
import altair as alt
import pandas as pd
import streamlit as st

from attendance import STATUSES, recurring_people

COLORS = ['#f97373', '#5b7cfa']


def render_dashboard(records, table):
    if not records:
        st.info('Your saved history is empty. Import a workbook to build your dashboard.')
        return
    frame = pd.DataFrame(records)
    dates = pd.to_datetime(frame['date'])
    with st.container(border=True):
        cols = st.columns([1, 1, 2])
        start = cols[0].date_input('From', dates.min().date())
        end = cols[1].date_input('To', dates.max().date())
        schools = sorted({r.get('school') or 'Unspecified school' for r in records})
        school = cols[2].selectbox('School', ['All schools'] + schools)
    if start > end:
        st.error('From must be on or before To.')
        return
    selected = [r for r in records if start.isoformat() <= r['date'] <= end.isoformat()
                and (school == 'All schools' or (r.get('school') or 'Unspecified school') == school)]
    st.caption(f'Polk County · {start:%b %d, %Y} – {end:%b %d, %Y} · {school}')
    for col, (label, count) in zip(st.columns(4), [
        ('Total incidents', len(selected)), ('No Show', sum(r['status'] == 'No Show' for r in selected)),
        ('Late Cancellation', sum(r['status'] == 'Late Cancellation' for r in selected)),
        ('Employees affected', len({r['person_id'] for r in selected}))]):
        col.metric(label, f'{count:,}')
    if not selected:
        st.info('No incidents match this date range and school.')
        return
    filtered = pd.DataFrame(selected)
    filtered['Day'] = pd.to_datetime(filtered['date'])
    filtered['School'] = filtered.get('school', pd.Series('', index=filtered.index)).fillna('').replace('', 'Unspecified school')
    color = alt.Color('status:N', title='Incident type', scale=alt.Scale(domain=list(STATUSES), range=COLORS))
    left, right = st.columns([2, 1])
    with left.container(border=True):
        st.subheader('Incident trend')
        st.caption('Weekly totals within your selected dates')
        chart = alt.Chart(filtered).mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4).encode(
            x=alt.X('yearweek(Day):T', title=None, axis=alt.Axis(format='%b %d', labelAngle=0)),
            y=alt.Y('count():Q', title='Incidents', axis=alt.Axis(tickMinStep=1)), color=color,
            tooltip=[alt.Tooltip('yearweek(Day):T', title='Week', format='%b %d, %Y'),
                     alt.Tooltip('status:N', title='Type'), alt.Tooltip('count():Q', title='Incidents')])
        st.altair_chart(chart.properties(height=270).configure_view(stroke=None), use_container_width=True)
    with right.container(border=True):
        st.subheader('Incident mix')
        st.caption('Share of recorded incidents')
        mix = alt.Chart(filtered).mark_arc(innerRadius=75, outerRadius=110).encode(
            theta=alt.Theta('count():Q'), color=color,
            tooltip=[alt.Tooltip('status:N', title='Type'), alt.Tooltip('count():Q', title='Incidents')])
        st.altair_chart(mix.properties(height=270).configure_view(stroke=None), use_container_width=True)
    left, right = st.columns([1.4, 1])
    with left.container(border=True):
        st.subheader('Schools with most incidents')
        top = filtered.groupby('School').size().sort_values(ascending=False).head(8).reset_index(name='Incidents')
        chart = alt.Chart(top).mark_bar(color='#5b7cfa', cornerRadiusEnd=4).encode(
            x=alt.X('Incidents:Q', axis=alt.Axis(tickMinStep=1)),
            y=alt.Y('School:N', sort='-x', title=None), tooltip=['School:N', 'Incidents:Q'])
        st.altair_chart(chart.properties(height=250).configure_view(stroke=None), use_container_width=True)
    with right.container(border=True):
        st.subheader('Repeat incidents')
        repeat = recurring_people(selected)
        st.metric('Recurring employees', len(repeat))
        st.caption('At least 2 incidents in the selected dates and school. The Recurring People page shows full history.')
        if repeat:
            st.dataframe(pd.DataFrame(repeat)[['Name', 'Incidents', 'Last incident']].head(5),
                         hide_index=True, width='stretch')
        else:
            st.info('No repeated incidents in this selection.')
    st.caption('Source: saved Polk County incident history. No attendance rate is calculated because attended assignments are not in this tracker.')
    with st.expander('Explore incident details'):
        table(sorted(selected, key=lambda r: r['date'], reverse=True), 'polkcounty_report.csv')
