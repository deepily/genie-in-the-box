
import lib.utils.util as du
import lib.utils.util_xml as dux

from lib.agents.agent import Agent
class CodeAgent( Agent ):
    def __init__( self, debug=True, verbose=True ):
        
        super().__init__( debug=debug, verbose=verbose )
    
    def _get_source_code( self, path ):
        
        source_code = du.get_file_as_list( path )
        
        # iterate through the source code and prepend the line number to each line
        for i in range( len( source_code ) ):
            source_code[ i ] = f"{i + 1:03d} {source_code[ i ]}"
        
        # join the lines back together into a single string
        source_code = "".join( source_code )
        return source_code
    
    # def _update_response_dictionary( self, step, response, prompt_response_dict, tag_names, debug=True ):
    #
    #     if debug: print( f"update_response_dictionary called with step [{step}]..." )
    #
    #     # Parse response and update response dictionary
    #     xml_tags_for_step_n = tag_names[ step ]
    #
    #     for xml_tag in xml_tags_for_step_n:
    #
    #         if debug: print( f"Looking for xml_tag [{xml_tag}]" )
    #
    #         if xml_tag == "code":
    #             # the get_code method expects enclosing tags
    #             xml_string = "<code>" + dux.get_value_by_xml_tag_name( response, xml_tag ) + "</code>"
    #             prompt_response_dict[ xml_tag ] = dux.get_code_list( xml_string, debug=debug )
    #         else:
    #             prompt_response_dict[ xml_tag ] = dux.get_value_by_xml_tag_name( response, xml_tag ).strip()
    #
    #     return prompt_response_dict