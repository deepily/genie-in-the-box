import pandas as pd
from datetime import datetime, timedelta
def get_this_weeks_events_by_type(df, **kwargs):
    event_type = kwargs.get('event_type', None)
    df['start_date'] = pd.to_datetime(df['start_date'])
    df['end_date'] = pd.to_datetime(df['end_date'])
    now = pd.Timestamp.now()
    start_of_week = now - pd.to_timedelta(now.dayofweek, unit='d')
    end_of_week = start_of_week + pd.to_timedelta(6, unit='d')
    if event_type:
        solution = df[(df['event_type'] == event_type) & (df['start_date'] <= end_of_week) & (df['end_date'] >= start_of_week)]
    else:
        solution = df[(df['start_date'] <= end_of_week) & (df['end_date'] >= start_of_week)]
    return solution