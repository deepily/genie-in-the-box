import csv

foo = {
    'lc'    : 1,
    'type'  : 'constructor',
    'id'    : [ 'langchain', 'prompts', 'prompt', 'PromptTemplate' ],
    'kwargs': {
        'input_variables'  : [ 'input', 'agent_scratchpad' ],
        'output_parser'    : None,
        'partial_variables': {
            'df_head': '|    | start_date   | end_date   | start_time   | end_time   | event_type   | recurrent   |   recurrence_interval | priority_level   | name       | relationship   | description_who_what_where                      |\n|---:|:-------------|:-----------|:-------------|:-----------|:-------------|:------------|----------------------:|:-----------------|:-----------|:---------------|:------------------------------------------------|\n|  0 | 2023-07-01   | 2023-07-04 | 00:00        | 23:59      | Concert      | False       |                   nan | none             | Jenny      | coworker       | Concert of Jenny at the city center             |\n|  1 | 2023-07-01   | 2023-07-01 | 05:25        | 17:22      | TODO         | False       |                   nan | highest          | Gregorio   | friend         | Send out invitations for the party for Gregorio |\n|  2 | 2023-07-01   | 2023-07-01 | 13:27        | 01:59      | Appointment  | False       |                   nan | high             | Leroy Ruiz | father         | Appointment with Leroy Ruiz at the clinic       |\n|  3 | 2023-07-02   | 2023-07-03 | 13:18        | 02:40      | Interview    | False       |                   nan | highest          | John       | coworker       | Job interview with John at Google               |\n|  4 | 2023-07-03   | 2023-07-04 | 00:00        | 23:59      | Performance  | False       |                   nan | medium           | Sue        | sister         | Theatre performance with Sue                    |'
        },
        'template'         : '\nYou are working with a pandas dataframe in Python. The name of the dataframe is `df`.\nYou should use the tools below to answer the question posed of you:\n\npython_repl_ast: A Python shell. Use this to execute python commands. Input should be a valid python command. When using this tool, sometimes output is abbreviated - make sure it does not look abbreviated before using it in your answer.\n\nUse the following format:\n\nQuestion: the input question you must answer\nThought: you should always think about what to do\nAction: the action to take, should be one of [python_repl_ast]\nAction Input: the input to the action\nObservation: the result of the action\n... (this Thought/Action/Action Input/Observation can repeat N times)\nThought: I now know the final answer\nFinal Answer: the final answer to the original input question\n\n\nThis is the result of `print(df.head())`:\n{df_head}\n\nBegin!\nQuestion: {input}\n{agent_scratchpad}',
        'template_format'  : 'f-string',
        'validate_template': True
    }
}
# print( foo[ 'kwargs' ][ 'template' ])

import pandas as pd
import lib.util as du

pd.set_option( 'display.max_columns', None )
pd.set_option( 'display.max_colwidth', None )

df = pd.read_csv( du.get_project_root() + "/src/conf/long-term-memory/events.csv" )

df[ 'recurrence_interval' ] = df[ 'recurrence_interval' ].fillna( '' )
df.loc[ df.recurrence_interval.str.endswith( "year" ), "recurrence_interval" ] = "1 year"

annual_df = df[ (df.recurrent == True | ~df.recurrence_interval.isna() ) ].copy()
# print(        df.head( 3 ).to_string( index=False ) )
# print( annual_df.head( 3 ).to_string( index=False ) )
#
# print(        df.head( 3 ).to_csv( index=False, sep=',', lineterminator='\n', quoting=csv.QUOTE_NONNUMERIC ) )
# print( annual_df.head( 3 ).to_csv( index=False, sep=',', lineterminator='\n', quoting=csv.QUOTE_NONNUMERIC ) )

df_head = """
start_date   end_date start_time end_time  event_type  recurrent recurrence_interval priority_level       name relationship                      description_who_what_where
2023-07-01 2023-07-01      13:27    01:59 Appointment      False                               high Leroy Ruiz       father       Appointment with Leroy Ruiz at the clinic
2023-07-02 2023-07-03      13:18    02:40   Interview      False                            highest       John     coworker               Job interview with John at Google
2023-07-03 2023-07-04      00:00    23:59 Performance      False                             medium        Sue       sister                    Theatre performance with Sue
2023-07-03 2023-07-04      00:00    23:59 Subscription       True              1 year        highest Leroy Ruiz       father             Renewal of Leroy Ruiz's subscription
2023-07-03 2023-07-04      00:00    23:59  Anniversary       True              4 week           none       Juan     neighbor       Juan's anniversary celebration at the park
2023-07-04 2023-07-04      00:00    23:59  Anniversary       True              4 week         medium Leroy Ruiz       father Leroy Ruiz's anniversary celebration at the park"""

csv_head = """
"start_date","end_date","start_time","end_time","event_type","recurrent","recurrence_interval","priority_level","name","relationship","description_who_what_where"
"2023-07-01","2023-07-04","00:00","23:59","Concert",False,"","none","Jenny","coworker","Concert of Jenny at the city center"
"2023-07-01","2023-07-01","05:25","17:22","TODO",False,"","highest","Gregorio","friend","Send out invitations for the party for Gregorio"
"2023-07-01","2023-07-01","13:27","01:59","Appointment",False,"","high","Leroy Ruiz","father","Appointment with Leroy Ruiz at the clinic"
"2023-07-03","2023-07-04","00:00","23:59","Subscription",True,"1 year","highest","Leroy Ruiz","father","Renewal of Leroy Ruiz's subscription"
"2023-07-03","2023-07-04","00:00","23:59","Anniversary",True,"4 week","none","Juan","neighbor","Juan's anniversary celebration at the park"
"2023-07-04","2023-07-04","00:00","23:59","Anniversary",True,"4 week","medium","Leroy Ruiz","father","Leroy Ruiz's anniversary celebration at the park\""""

print( csv_head )

print( raw)