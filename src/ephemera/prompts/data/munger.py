import lib.utils.util as du

def remove_line_numbers( path, write_back=True ):
    
    lines = du.get_file_as_list( path, clean=True )
    
    print( "Total number of lines: [{}]".format( len( lines ) ) )
    
    # This assumes "number dot space" formatting. removes extraneous double quotes too
    lines = [ line.split( ". " )[ 1 ].replace( '"', '' ) for line in lines ]
    
    for line in lines[ 0:5 ]:
        print( line )
    
    # Write lines back to the same file
    if write_back:
        du.write_lines_to_file( path, lines )

def remove_zero_length_strings( path ):
    
    lines = du.get_file_as_list( path, clean=True )
    
    # Using list comprehension to test for and reject zero length strings
    print( " PRE: Total number of lines: [{}]".format( len( lines ) ) )
    lines = [ line for line in lines if len( line ) > 0 ]
    print( "POST: Total number of lines: [{}]".format( len( lines ) ) )
    
    # Write lines back to the same file
    du.write_lines_to_file( path, lines )

def get_agent_synonyms():
    
    agent_synonyms = {
        "receptionist" : [ "receptionist", "front desk", "administrator", "secretary", "office assistant", "operator" ],
        "timekeeper"   : [ "timekeeper", "scheduler", "time manager", "clock watcher", "chronologist", "time coordinator" ],
        "meteorologist": [ "meteorologist", "weather forecaster", "climatologist", "weather scientist", "atmospheric scientist", "weatherman" ],
        "todo list"    : [ "todo list", "task manager", "list coordinator", "list organizer", "activity overseer", "duty administrator" ],
        "calendaring"  : [ "calendaring", "schedule manager", "date planner", "event organizer", "social secretary", "appointment scheduler" ]
    }
    return agent_synonyms

# Create main method
if __name__ == "__main__":
    
    # remove_zero_length_strings( path=du.get_project_root() + "/src/ephemera/prompts/data/synthetic-data-agent-routing-todo-lists.txt" )
    # remove_zero_length_strings( path=du.get_project_root() + "/src/ephemera/prompts/data/placeholders-cities-and-countries.txt")
    remove_zero_length_strings( path=du.get_project_root() + "/src/ephemera/prompts/data/placeholders-calendaring-places.txt" )
    
    # remove_line_numbers( path = du.get_project_root() + "/src/prompts/data/synthetic-data-search-in-current-tab.txt", write_back=True )
    # remove_line_numbers( path = du.get_project_root() + "/src/prompts/data/synthetic-data-search-google-in-current-tab.txt", write_back=True )
    # remove_line_numbers( path = du.get_project_root() + "/src/prompts/data/synthetic-data-search-google-scholar-in-current-tab.txt", write_back=True )
    # remove_line_numbers( path = du.get_project_root() + "/src/prompts/data/synthetic-data-search-in-new-tab.txt", write_back=True )
    # remove_line_numbers( path = du.get_project_root() + "/src/prompts/data/synthetic-data-search-google-in-new-tab.txt", write_back=True )
    # remove_line_numbers( path = du.get_project_root() + "/src/prompts/data/synthetic-data-search-google-scholar-in-new-tab.txt", write_back=True )
    # remove_line_numbers( path = du.get_project_root() + "/src/prompts/data/synthetic-data-none-of-the-above.txt", write_back=True )

    # pass