# Save the function to a .py file
import random
from datetime import datetime
import json
from pprint import pprint
import csv
import src.lib.util as du


def generate_events( num_events, start_date_str, end_date_str ):
    
    # Generate a list of people's first name plus
    # a list of people's last name
    names = [
        "Bob (brother)",
        "Leroy Ruiz (father)",
        "Barbara Jane Ruiz (mother)",
        "Sally (sister)",
        "Sue (sister)",
        "Tom Ruiz (brother)",
        "Alice (aunt)",
        "Pablo (friend)",
        "Gregorio (friend)",
        "Inash (girlfriend)",
        "Jenny (coworker)",
        "John (coworker)",
        "Juan (Neighbor)",
    ]
    # Event types and their specific properties
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
        "Task"        : { "recurrent": False, "all_day": False },
        "TODO"        : { "recurrent": False, "all_day": False }
    }
    
    priority_levels = [ "none", "low", "medium", "high", "highest" ]
    
    # Setting start and end dates
    start_date = datetime.strptime( start_date_str, "%Y-%m-%d" )
    end_date = datetime.strptime( end_date_str, "%Y-%m-%d" )
    
    data = [ ]
    for i in range( num_events ):
        # Randomly select an event type
        event_type, properties = random.choice( list( event_types.items() ) )
        
        # Generate random date within the given range
        date = start_date + (end_date - start_date) * random.random()
        
        # If the event is all day, then the start and end times are set to cover the whole day
        if properties[ "all_day" ]:
            start_time = "00:00"
            end_time = "23:59"
        else:
            start_time = f"{random.randint( 0, 23 ):02d}:{random.randint( 0, 59 ):02d}"
            end_time = f"{random.randint( 0, 23 ):02d}:{random.randint( 0, 59 ):02d}"
            
            # If the event is recurrent, generate a random recurrence interval
        if properties[ "recurrent" ]:
            if event_type in [ "Birthday", "Anniversary" ]:
                recurrence_interval = "1 year"
            elif event_type == "Subscription":
                recurrence_interval = f"{random.randint( 1, 5 )} {random.choice( [ 'month', 'year' ] )}"
        else:
            recurrence_interval = None
        
        # Generate a random priority level
        priority_level = random.choice( priority_levels )
        
        # Create a description for the event
        if event_type == "Birthday":
            description = f"{random.choice( names )}'s {event_type.lower()}"
        else:
            description = f"This is a {event_type.lower()}"
            
        # Create the dictionary representing the event
        event = {
            "date"               : date.strftime( "%Y-%m-%d" ),
            "start_time"         : start_time,
            "end_time"           : end_time,
            "event_type"         : event_type,
            "recurrent"          : properties[ "recurrent" ],
            "recurrence_interval": recurrence_interval,
            "description"        : description,
            "priority_level"     : priority_level
        }
        
        data.append( event )
        
    # Sort the data list by date
    data.sort( key=lambda x: x[ "date" ] )
    
    return data


def write_output( data, output_type, path ):
    
    if output_type == 'jsonl':
        # Convert the list of dictionaries to a JSONL string
        jsonl_data = [ json.dumps( event ) for event in data ]
        du.write_lines_to_file( path, jsonl_data )
    elif output_type == 'csv':
        keys = data[ 0 ].keys()
        with open( path, 'w', newline='' ) as output_file:
            dict_writer = csv.DictWriter( output_file, keys )
            dict_writer.writeheader()
            dict_writer.writerows( data )


# Test the function
data = generate_events( 50, "2023-07-17", "2023-09-30" )
# pprint( data )
write_output( data, 'jsonl', du.get_project_root() + "/src/conf/long-term-memory/events.jsonl" )
write_output( data, 'csv',   du.get_project_root() + "/src/conf/long-term-memory/events.csv" )
