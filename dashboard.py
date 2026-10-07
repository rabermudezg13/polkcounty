"""Summary-first visuals using the same filtered incidents as the detail table."""
import plotly.graph_objects as go
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
    left, right = st.columns([2, 1])
    with left.container(border=True):
        st.subheader('Incident trend')
        st.caption('Weekly totals within your selected dates')
        weekly = filtered.assign(Week=filtered.Day.dt.to_period('W-SUN').dt.start_time)
        totals = weekly.groupby(['Week', 'status']).size().unstack(fill_value=0)
        chart = go.Figure()
        for status, color in zip(STATUSES, COLORS):
            values = totals[status] if status in totals else [0] * len(totals)
            chart.add_bar(x=totals.index, y=values, name=status, marker_color=color)
        chart.update_layout(height=300, barmode='stack', margin=dict(l=10,r=10,t=10,b=10),
                            xaxis_title=None, yaxis_title='Incidents', legend=dict(orientation='h',y=1.15))
        chart.update_yaxes(dtick=1 if len(selected)<20 else None)
        st.plotly_chart(chart, use_container_width=True, config={'displayModeBar':False})
    with right.container(border=True):
        st.subheader('Incident mix')
        st.caption('Share of recorded incidents')
        counts = [sum(r['status']==status for r in selected) for status in STATUSES]
        mix = go.Figure(go.Pie(labels=list(STATUSES), values=counts, hole=.7,
                              marker_colors=COLORS, textinfo='percent', sort=False))
        mix.update_layout(height=300, margin=dict(l=5,r=5,t=10,b=10),
                          legend=dict(orientation='h',y=-.1),
                          annotations=[dict(text=str(len(selected)),x=.5,y=.5,showarrow=False,font_size=28)])
        st.plotly_chart(mix, use_container_width=True, config={'displayModeBar':False})
    left, right = st.columns([1.4, 1])
    with left.container(border=True):
        st.subheader('Schools with most incidents')
        top = filtered.groupby('School').size().sort_values(ascending=False).head(8).reset_index(name='Incidents')
        chart = go.Figure(go.Bar(x=top['Incidents'], y=top['School'], orientation='h', marker_color='#5b7cfa'))
        chart.update_layout(height=270, margin=dict(l=10,r=10,t=10,b=10), xaxis_title='Incidents',
                            yaxis=dict(autorange='reversed'))
        st.plotly_chart(chart, use_container_width=True, config={'displayModeBar':False})
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
