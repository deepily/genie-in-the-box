import src.lib.util as du

# Create main method
if __name__ == "__main__":

    path = du.get_project_root() + "/src/prompts/data/synthetic-data-search-in-current-tab.txt"
    lines = du.get_file_as_list( path, clean=True )
    
    print( "Total number of prompts: {}".format( len( lines ) ) )
    
    lines = [ line.split( ". " )[ 1 ].replace( '"', '' ) for line in lines ]
    
    for line in lines[ 0:5 ]:
        print( line )

    # Write lines back to the same file
    du.write_lines_to_file( path, lines )