import lib.utils.util as du
import lib.utils.util_xml as dux

from lib.agents.agent_base import AgentBase
from lib.agents.llm   import Llm

class BugInjector( AgentBase ):
    def __init__( self, code, debug=True, verbose=True ):
        
        super().__init__( debug=debug, verbose=verbose )
        
        self.code                 = code
        self.prompt_components    = None
        self.prompt_response_dict = None
    
    def _initialize_prompt_components( self ):
        
        code_with_line_numbers = du.get_source_code_with_line_numbers( self.code.copy(), join_str="\n" )
        
        prompt = f"""
        You are a Python or Pandas code bug injector.
        
        Please introduce one, and only one, Python or Pandas syntax or spelling error inside the function body of the provided source code snippet below.
        
        Source code:
{code_with_line_numbers}
        
        Remember: The error should prevent the program from running.
        
        You must only return only one line of source code that you have modified to fail at runtime
        """
        
        instructions = """
        Format the response as follows, replacing the placeholders with the actual details:
        <response>
            <line-number>[line number where bug is introduced]</line-number>
            <bug>[one line of modified source code with bug in it]</bug>
        </response>
        """
        if self.debug: print( f"prompt: [{prompt}]" )
        
        self.prompt_components = {
                "preamble": prompt,
            "instructions": instructions
        }
        
        return self.prompt_components
    
    def format_output( self ):
        pass
    
    def is_code_runnable( self ):
        pass
    
    def run_prompt( self, question="" ):
        
        print( "BugInjector.run_prompt() called..." )
        
        model = Llm.PHIND_34B_v2  # Asking LLM [TGI/Phind-CodeLlama-34B-v2]... Done! in 1,270 ms
        # model = Llm.GPT_4       # Asking LLM [gpt-4-0613]... Done! in 5,222 ms
        self.prompt_components = self._initialize_prompt_components()
        response               = self._query_llm(
            self.prompt_components[ "preamble" ], self.prompt_components[ "instructions" ], model=model, temperature=2.0, top_k=1000, top_p=0.25, debug=self.debug
        )
        
        line_number = int( dux.get_value_by_xml_tag_name( response, "line-number", default_value="-1" ) )
        bug         =      dux.get_value_by_xml_tag_name( response, "bug",         default_value="" )
        
        if line_number == -1: # or bug == "": # for now, we're going to allow the bug to be an empty string
            du.print_banner( f"Invalid response from [{model}]", expletive=True )
            print( response )
        elif line_number > len( self.code ):
            du.print_banner( f"Invalid response from [{model}]", expletive=True )
            print( f"Line number [{line_number}] out of bounds, code[] length is [{len(self.code)}]" )
            print( response )
        elif line_number == 0:
            du.print_banner( f"Invalid response from [{model}]", expletive=True )
            print( f"Line number [{line_number}] is invalid, line numbers SHOULD start at 1" )
            print( response )
        else:
            if self.debug:
                du.print_banner( "BEFORE: untouched code", prepend_nl=True, end="\n" )
                du.print_list( self.code )
                
            print( f"Bug generated for line_number: [{line_number}], bug: [{bug}]" )
            # prepend a blank line to the code, so that the line numbers align with the line numbers in the prompt
            self.code = [ "" ] + self.code
            # todo: do i need to handle possibly mangled preceding white space? if so see: https://chat.openai.com/c/59098430-c164-482e-a82e-01d6c6769978
            self.code[ line_number ] = bug

        self.prompt_response_dict = {
            "code": self.code,
        }
        if self.debug:
            du.print_banner( "AFTER: updated code", prepend_nl=True, end="\n" )
            du.print_list( self.code )
            
        return self.prompt_response_dict
    
    def _get_user_message( self ):
        pass
    
    def _get_system_message( self ):
        pass
    
    def is_prompt_executable( self ):
        pass


if __name__ == "__main__":
    
    code = [
        "import datetime",
        "import pytz",
        "def get_time():",
        "    import datetime",
        "    now = datetime.datetime.now()",
        "    tz_name = 'America/New_York'",
        "    tz = pytz.timezone( tz_name )",
        "    tz_date = now.astimezone( tz )",
        "    return tz_date.strftime( '%I:%M %p %Z' )",
        "solution = get_time()",
        "print( solution )"
    ]
    
    bug_injector  = BugInjector( code, debug=False, verbose=False )
    response_dict = bug_injector.run_prompt()
    
    du.print_banner( "BugInjector response_dict", prepend_nl=True, end="\n" )
    du.print_list( response_dict[ "code" ] )