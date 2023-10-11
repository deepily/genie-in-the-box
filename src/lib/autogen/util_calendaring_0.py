import pandas as pd
from datetime import datetime
def get_todays_events_by_type(df, **kwargs):
    event_type = kwargs.get('event_type')
    today = pd.Timestamp(datetime.now()).normalize()
    events_today = df[(df['event_type'] == event_type) & (df['start_date'] <= today) & (df['end_date'] >= today)]
    return events_today.to_json(orient='records', lines=True)