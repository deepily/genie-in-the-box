import random
from datetime import datetime

import pandas as pd

from lib.utils import util as du


# Do something useful here.

def generate_events( num_events, start_date_str, end_date_str ):
    event_types = {
        "Birthday"    : { "recurrent": True, "all_day": True },
        "Subscription": { "recurrent": True, "all_day": True },
        "Anniversary" : { "recurrent": True, "all_day": True },
        "Meeting"     : { "recurrent": False, "all_day": False },
        "Appointment" : { "recurrent": False, "all_day": False },
        "Workshop"    : { "recurrent": False, "all_day": False },
        "Conference"  : { "recurrent": False, "all_day": True },
        "Interview"   : { "recurrent": False, "all_day": False },
        "Workout"     : { "recurrent": False, "all_day": False },
        "Concert"     : { "recurrent": False, "all_day": True },
        "Performance" : { "recurrent": False, "all_day": True },
        "TODO"        : { "recurrent": False, "all_day": False }
    }
    # generate a list of men's and women's names, + what kind of relationship? e.g. : wife friend colleague etc.
    names = [
        "Bob",
        "Leroy Ruiz",
        "Barbara Jane Ruiz",
        "Sally",
        "Sue",
        "Tom Ruiz",
        "Alice",
        "Pablo",
        "Gregorio",
        "Inash",
        "Jenny",
        "John",
        "Juan"
    ]
    
    relationships = [
        "brother",
        "father",
        "mother",
        "sister",
        "sister",
        "brother",
        "aunt",
        "friend",
        "friend",
        "girlfriend",
        "coworker",
        "coworker",
        "neighbor"
    ]
    event_descriptions = {
        "Birthday"    : "{}'s birthday party at their favorite bar",
        "Subscription": "Renewal of {}'s subscription",
        "Anniversary" : "{}'s anniversary celebration at the park",
        "Meeting"     : "Another boring meeting with {}",
        "Appointment" : "Appointment with {} at the clinic",
        "Workshop"    : "Exciting workshop with {} on AGI",
        "Conference"  : "Conference with {} on AI advancements",
        "Interview"   : "Job interview with {} at Google",
        "Workout"     : "Workout session with {} at the gym",
        "Concert"     : "Concert of {} at the city center",
        "Performance" : "Theatre performance with {}",
        "TODO"        : "TODO item for {}"
    }
    
    todo_descriptions = [
        "Pick up groceries",
        "Pay electric bill",
        "Clean the bathroom",
        "Finish the report",
        "Call the bank",
        "Schedule a doctor's appointment",
        "Buy birthday gift",
        "Book flight tickets for vacation",
        "Prepare presentation for next week's meeting",
        "Send out invitations for the party",
        "Fix the leaky faucet",
        "Take the car for servicing",
        "Update resume",
        "Return library books",
        "Plan meals for the week",
        "Order new shoes online",
        "Renew gym membership",
        "Drop off dry cleaning"
    ]
    
    def generate_event_description( event_type, name, relationship ):
        
        if event_type == "TODO":
            return f"{random.choice( todo_descriptions )} for {name} ({relationship})"
        elif event_type in event_descriptions:
            return event_descriptions[ event_type ].format( name )
        else:
            return f"This is a {event_type.lower()}."
    
    priority_levels = [ "none", "low", "medium", "high", "highest" ]
    
    # Setting start and end dates
    start_date = datetime.strptime( start_date_str, "%Y-%m-%d" )
    end_date = datetime.strptime( end_date_str, "%Y-%m-%d" )
    
    print( f"Generating {num_events} events between {start_date_str} and {end_date_str}..." )
    
    data = [ ]
    days_diff = (end_date - start_date).days
    print( f"Days difference between {end_date_str} and {start_date_str}: {days_diff}" )
    
    for i in range( num_events ):
        # Randomly select an event type
        event_type, properties = random.choice( list( event_types.items() ) )
        
        index = random.randint( 0, len( names ) - 1 )
        name = names[ index ]
        relationship = relationships[ index ]
        description_who_what_where = generate_event_description( event_type, name, relationship )
        
        # Generate random date within the given range
        # start_date = start_date + (end_date - start_date) * random.random()
        new_start_date = start_date + pd.DateOffset( days=random.randint( 0, days_diff ) )
        
        # Generate random end dates between from 0 to 7 days after the start date
        duration = random.randint( 0, 7 )
        # If the duration is even, then the event is not a multi-day event
        if duration % 2 == 0: duration = 0
        # Calculate end date
        end_date = new_start_date + pd.DateOffset( days=duration )
        
        # If the event is all day, then the start and end times are set to cover the whole day
        if properties[ "all_day" ]:
            start_time = "00:00"
            end_time = "23:59"
        else:
            start_time = f"{random.randint( 0, 23 ):02d}:{random.randint( 0, 59 ):02d}"
            end_time = f"{random.randint( 0, 23 ):02d}:{random.randint( 0, 59 ):02d}"
        
        # If the event is recurrent, generate a random recurrence interval
        if properties[ "recurrent" ]:
            if event_type.lower in [ "birthday", "anniversary" ]:
                recurrence_interval = "1 year"
            else:
                recurrence_interval = f"{random.randint( 1, 5 )} {random.choice( [ 'day', 'week', 'month', 'year' ] )}"
        else:
            recurrence_interval = ""
        
        # Generate a random priority level
        priority_level = random.choice( priority_levels )
        
        # Create the dictionary representing the event
        event = {
            "start_date"                : new_start_date.strftime( "%Y-%m-%d" ),
            "end_date"                  : end_date.strftime( "%Y-%m-%d" ),
            "start_time"                : start_time,
            "end_time"                  : end_time,
            "event_type"                : event_type,
            "recurrent"                 : properties[ "recurrent" ],
            "recurrence_interval"       : recurrence_interval,
            "priority_level"            : priority_level,
            "name"                      : name,
            "relationship"              : relationship,
            "description_who_what_where": description_who_what_where
        }
        
        data.append( event )
    #
    # Sort list by date and start time,
    data = sorted( data, key=lambda k: (k[ "start_date" ], k[ "start_time" ]) )
    
    # Convert the list of dictionaries to a DataFrame
    df = pd.DataFrame( data )
    
    return df


# Test the function
# pd.set_option( "display.max_columns", None )
pd.options.display.max_columns = None
df = generate_events( 200, "2023-07-01", "2023-09-01" )
cols = [ "start_date", "start_time", "event_type", "description_who_what_where" ]

print( df[ cols ].head( 10 ) )
print( df[ cols ].tail( 10 ) )

# Write data frame
df.to_csv( du.get_project_root() + "/src/conf/long-term-memory/events.csv", index=False )
df.to_json( du.get_project_root() + "/src/conf/long-term-memory/events.jsonl", orient="records", lines=True )
