def get_birthday_by_name(df, **kwargs):
    name = kwargs.get('name')
    filtered_df = df[(df['event_type'] == 'birthday') & (df['name'] == name)]
    return filtered_df['start_date'].values[0] if not filtered_df.empty else f'No birthday found for {name}'