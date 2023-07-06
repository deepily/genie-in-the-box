import src.lib.util as du

def remove_line_numbers( path, write_back=True ):
    
    lines = du.get_file_as_list( path, clean=True )
    
    print( "Total number of lines: [{}]".format( len( lines ) ) )
    
    # This assumes "number dot space" formatting plus remove extraneous double quotes
    lines = [ line.split( ". " )[ 1 ].replace( '"', '' ) for line in lines ]
    
    for line in lines[ 0:5 ]:
        print( line )
    
    # Write lines back to the same file
    if write_back:
        du.write_lines_to_file( path, lines )

# Create main method
if __name__ == "__main__":

    # remove_line_numbers( path = du.get_project_root() + "/src/prompts/data/synthetic-data-search-in-current-tab.txt", write_back=True )
    # remove_line_numbers( path = du.get_project_root() + "/src/prompts/data/synthetic-data-search-google-in-current-tab.txt", write_back=True )
    # remove_line_numbers( path = du.get_project_root() + "/src/prompts/data/synthetic-data-search-google-scholar-in-current-tab.txt", write_back=True )
    # remove_line_numbers( path = du.get_project_root() + "/src/prompts/data/synthetic-data-search-in-new-tab.txt", write_back=True )
    # remove_line_numbers( path = du.get_project_root() + "/src/prompts/data/synthetic-data-search-google-in-new-tab.txt", write_back=True )
    # remove_line_numbers( path = du.get_project_root() + "/src/prompts/data/synthetic-data-search-google-scholar-in-new-tab.txt", write_back=True )

    pass