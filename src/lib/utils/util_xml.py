import re

import lib.utils.util as du

def get_value_by_xml_tag_name( xml_string, name, default_value=f"Error: `{{name}}` not found in xml_string" ):
    
    if f"<{name}>" not in xml_string or f"</{name}>" not in xml_string:
        return default_value.format( name=name )
    
    return xml_string.split( f"<{name}>" )[ 1 ].split( f"</{name}>" )[ 0 ]
    
def get_code_list( xml_string, debug=False ):
    
    skip_list = [ ]  # [ "import pandas", "import datetime" ]
    
    # Matches all text between the opening and closing line tags, including the white space after the opening line tag
    pattern = re.compile( r"<line>(.*?)</line>" )
    code = get_value_by_xml_tag_name( xml_string, "code" )
    code_list = [ ]
    
    for line in code.split( "\n" ):
            
            match = pattern.search( line )
            
            for skip in skip_list:
                if skip in line:
                    if debug: print( f"[SKIPPING '{skip}']" )
                    match = None
                    break
            
            if match:
                line = match.group( 1 )
                line = line.replace( "&gt;", ">" ).replace( "&lt;", "<" ).replace( "&amp;", "&" )
                code_list.append( line )
                if debug: print( line )
            else:
                code_list.append( "" )
                if debug: print( "[]" )
        
    return code_list


def rescue_code_using_tick_tick_tick_syntax( raw_response_text, debug=True ):
    
    if debug: print( f"before: [{raw_response_text}]" )
    raw_response_text = raw_response_text.strip()
    if debug: print( f"after: [{raw_response_text}]" )
    
    if raw_response_text.startswith( "```python" ) and raw_response_text.endswith( "```" ):
        
        msg = "¡Yay! Returning rescued code list using default tick tick tick syntax"
        if debug:
            du.print_banner( msg )
        else:
            print( msg )
        
        lines = raw_response_text.split( "```python" )[ 1 ]
        lines = lines.split( "```" )[ 0 ]
        lines = lines.split( "\n" )
        
        # wrap each line with a xml-esque line tag
        lines = [ f"<line>{line}</line>" for line in lines ]
        lines = "\n".join( lines )
        
        if debug:
            for line in lines.split( "\n" ): print( line )
        
        return lines
    
    else:
        
        if debug:
            du.print_banner( "¡Boo!, no ```python found, either!", expletive=True )
        else:
            print( "¡Boo!, no ```python found, either!" )
            
        return ""
