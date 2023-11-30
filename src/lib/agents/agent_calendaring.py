import json
import re
import xml.etree.ElementTree as et

import lib.utils.util as du
import lib.utils.util_pandas as dup
import lib.utils.util_stopwatch as sw
from lib.memory import solution_snapshot as ss

from lib.agents.agent import Agent

import pandas as pd

class CalendaringAgent( Agent ):
    
    def __init__( self, path_to_df, question="", default_model=Agent.PHIND_34B_v2, push_counter=-1, debug=False, verbose=False ):
        
        super().__init__( debug=debug, verbose=verbose )
        
        # self.debug      = debug
        # self.verbose    = verbose
        
        self.path_to_df = du.get_project_root() + path_to_df
        self.df         = pd.read_csv( self.path_to_df )
        self.df         = dup.cast_to_datetime( self.df )
        
        self.default_model         = default_model
        
        self.last_question_asked   = question
        self.question              = ss.SolutionSnapshot.clean_question( question )
        
        if self.default_model == Agent.PHIND_34B_v2:
            self.system_message    = self._get_system_message_phind()
        else:
            self.system_message    = self._get_system_message()
        
        # Added to allow behavioral compatibility with solution snapshot object
        self.run_date              = ss.SolutionSnapshot.get_timestamp()
        self.push_counter          = push_counter
        self.id_hash               = ss.SolutionSnapshot.generate_id_hash( self.push_counter, self.run_date )

        self.user_message          = None
        
        # We'll set these later
        self.answer_conversational = None
        # self.prompt_response              = None
        # self.prompt_response_dict         = None
        # self.error                 = None
    
    def get_html( self ):
        
        return f"<li id='{self.id_hash}'>{self.run_date} Q: {self.question}</li>"
    
    def _get_system_message_phind( self ):
        
        csv = self.df.head( 3 ).to_csv( header=True, index=False )
        csv = csv + self.df.tail( 3 ).to_csv( header=False, index=False )
        
        pandas_system_prompt = f"""
        You are a cheerfully helpful assistant, with proven expertise in Python using pandas dataframes containing calendaring and events information. The name of the dataframe is `df`.

        This is the ouput from `print(df.head().to_csv())`, in CSV format:

        {csv}

        This is the output from `print(self.df.event_type.value_counts())`:

        {self.df.event_type.value_counts()}

        BEFORE you generate the python code needed to answer the question below, I want you to:

        1) Question: Ask yourself if you understand the question that I am asking you. ` Pay attention to the details!
        
        2) Think: Before you do anything, think out loud about what I am asking you to do, including what are the steps that you will need to take to solve this problem. Be critical of your thought process!
        
        3) Code: Generate an XML document containing the Python code that you used to arrive at your answer. The code must be complete, syntactically correct, and capable of running to completion. The last line of your code must be be `return solution`.
        
        4) Return: Report on the object type of the variable `solution` in your last line of code. Use one word to represent the object type.
        
        5) Example: Create a one line example of how to call your code.
        
        6) Explain: Explain how your code works, including any assumptions that you made.
        
        Question: {self.question}

        Format: return your response as an XML document with the following fields:
        
        <response>
            <question>{self.question}</question>
            <thoughts>Your thoughts</thoughts>
            <code>
                <line>import foo</line>
                <line>def function_name_here( ... ):</line>
                <line>    return solution</line>
            </code>
            <returns>Object type of the variable `solution`</returns>
            <example>One-line example of how to call your code: solution = function_name_here( arguments )</example>
            <explanation>Explanation of how the code works</explanation>
            <error>Description of any issues or errors that you encountered while attempting to fulfill this request</error>
        </response>
        
        Hint: An event that I have today may have started before today and may end tomorrow or next week, so be careful how you filter on dates.
        Hint: When filtering by dates, use `pd.Timestamp( day )` to convert a Python datetime object into a Pandas `datetime64[ns]` value.
        Hint: If your solution variable is a dataframe, it should include all columns in the dataframe.
        Hint: If you cannot answer the question, explain why in the `error` field
        Hint: Allow for the possibility that your query may return no results.
        """
        
        return pandas_system_prompt
        
    
    def _get_system_message( self ):
        
        csv = self.df.head( 3 ).to_csv( header=True, index=False )
        csv = csv + self.df.tail( 3 ).to_csv( header=False, index=False )
        
        pandas_system_prompt = f"""
        You are an expert software engineer working with a pandas dataframe in Python containing calendaring and events information. The name of the dataframe is `df`.

        This is the ouput from `print(df.head().to_csv())`, in CSV format:

        {csv}

        This is the output from `print(self.df.event_type.value_counts())`:

        {self.df.event_type.value_counts()}

        As you generate the python code needed to answer the events and calendaring question asked of you below, I want you to:

        1) Question: Ask yourself if you understand the question that I am asking you.  Pay attention to the details!
        2) Think: Before you do anything, think out loud about what I'm asking you to do, including what are the steps that you will need to take to solve this problem. Be critical of your thought process!
        3) Code: Generate a verbatim list of code that you used to arrive at your answer, one line of code per item on the list. The code must be complete, syntactically correct, and capable of runnning to completion. The last line of your code must be the variable `solution`, which represents the answer. Make sure that any filtering you perform matches the question asked of you by the user!
        4) Return: Report on the object type of the variable `solution` in your last line of code. Use one word to represent the object type.
        5) Example: One-line example of how to call your code: solution = function_name_here( arguments )
        6) Explain: Briefly and succinctly explain your code in plain English.

        Format: return your response as a JSON object in the following fields:
        {{
            "question": "The question, verbatim and without modification",
            "thoughts": "Your thoughts",
            "code": [],
            "returns": "Object type of the variable `solution`",
            "example": "One-line example of how to call your code: solution = function_name_here( arguments )",
            "explanation": "A brief explanation of your code",
            "error": "Your description of any issues or errors that you encountered while attempting to answer the question"
        }}

        Hint: An event that I have today may have started before today and may end tomorrow or next week, so be careful how you filter on dates.
        Hint: When filtering by dates, use `pd.Timestamp( day )` to convert a Python datetime object into a Pandas `datetime64[ns]` value.
        Hint: If your solution variable is a dataframe, it should include all columns in the dataframe.
        Hint: If you cannot answer the question, explain why in the `error` field
        Hint: Allow for the possibility that your query may return no results.
        """
        
        return pandas_system_prompt
    
    def _get_user_message( self, question="" ):
        
        # Odd little two-step sanity check: allows us to set the question when instantiated or when run_prompt is called
        if question != "":
            self.question = question
            
        if self.question == "":
            raise ValueError( "No question was provided!" )
        
        return self.question
        
    def is_promptable( self ):
        
        du.print_banner( "TODO: Implement is_promptable()", expletive=True )
        return True
    
    def is_runnable( self ):
        
        du.print_banner( "TODO: Implement is_runnable()", expletive=True )
        return True
    
    def validate_xml( xml_string ):
        
        # TODO: This is a hacky way to validate XML. We should use a proper XML parser instead.
        # From: https://www.phind.com/agent?cache=clplcnojm0004l2087q5mn10z
        class MalformedXmlError( Exception ):
            pass
        
        def validate( xml_string ):
            try:
                root = et.fromstring( xml_string )
            except et.ParseError:
                raise MalformedXmlError( "The XML is malformed." )
            
            expected_tags = [ "question", "thoughts", "code", "returns", "example", "explanation", "error" ]
            for tag in expected_tags:
                if root.find( tag ) is None:
                    raise MalformedXmlError( f"The XML is missing the <{tag}> tag." )
            
            code_tag = root.find( "code" )
            if code_tag is None or len( code_tag.findall( "line" ) ) == 0:
                raise MalformedXmlError( "The XML is missing the <line> tag inside the <code> tag." )
        
        try:
            validate( xml_string )
        except MalformedXmlError as e:
            du.print_banner( e, expletive=True )
            print( xml_string )
            raise ValueError( e )
    
    def run_prompt( self, question="" ):
        
        prompt_model      = Agent.PHIND_34B_v2
        self.user_message = self._get_user_message( question )
        
        self._print_token_count( self.system_message, message_name="system_message", model=prompt_model )
        self._print_token_count( self.user_message,   message_name="user_message",   model=prompt_model )
        
        self.prompt_response = self._query_llm( self.system_message, self.user_message, model=prompt_model, debug=self.debug )
        
        if prompt_model == Agent.PHIND_34B_v2:
            self.validate_xml( self.prompt_response )
            self.prompt_response_dict = self._get_prompt_response_dict( self.prompt_response )
        else:
            self.prompt_response_dict = json.loads( self.prompt_response )
        
        if self.debug and self.verbose: print( json.dumps( self.prompt_response_dict, indent=4 ) )
        
        # Test for no code returned
        if self.prompt_response_dict[ "code" ] == [ ]:
            self.error = self.prompt_response_dict[ "error" ]
            raise ValueError( "No code was returned, please check the logs" )
        
        return self.prompt_response_dict
    
    # ¡OJO! Something tells me this should live somewhere else?
    def _get_prompt_response_dict( self, xml_string, debug=False ):

        def _get_value_by_tag_name( xml_string, name, default_value=f"Error: `{{name}}` not found in xml_string" ):

            if f"<{name}>" not in xml_string or f"</{name}>" not in xml_string:
                return default_value.format( name=name )

            return xml_string.split( f"<{name}>" )[ 1 ].split( f"</{name}>" )[ 0 ]

        def _get_code( xml_string, debug=False ):

            # Matches all text between the opening and closing line tags, including the white space after the opening line tag
            pattern   = re.compile( r"<line>(.*?)</line>" )
            code      = _get_value_by_tag_name( xml_string, "code" )
            code_list = []

            for line in code.split( "\n" ):

                match = pattern.search( line )
                if match:
                    line = match.group( 1 )
                    code_list.append( line )
                    if debug: print( line )
                else:
                    if debug: print( "[]" )

            return code_list

        # Trim everything down to only what's contained between the response open and close tags'
        xml_string = _get_value_by_tag_name( xml_string, "response" )

        response_dict = {
               # "answer": _get_value_by_tag_name( xml_string, "answer", default_value="" ),
               "question": _get_value_by_tag_name( xml_string, "question" ),
               "thoughts": _get_value_by_tag_name( xml_string, "thoughts" ),
                   "code": _get_code( xml_string, debug=debug ),
                "returns": _get_value_by_tag_name( xml_string, "returns" ),
                "example": _get_value_by_tag_name( xml_string, "example" ),
            "explanation": _get_value_by_tag_name( xml_string, "explanation" ),
                  "error": _get_value_by_tag_name( xml_string, "error" )
        }
        return response_dict
    
    def format_output( self ):
        
        format_model = Agent.PHIND_34B_v2
        preamble     = self._get_formatting_preamble()
        instructions = self._get_formatting_instructions()
        
        self._print_token_count( preamble, message_name="formatting preamble", model=format_model )
        self._print_token_count( instructions, message_name="formatting instructions", model=format_model )
        
        self.answer_conversational = self._query_llm( preamble, instructions, model=format_model, debug=self.debug )
        
        # if we've just received an xml-esque string then pull `<rephrased_answer>` from it. Otherwise, just return the string
        self.answer_conversational = du.get_value_by_xml_tag_name(
            self.answer_conversational, "rephrased_answer", default_value=self.answer_conversational
        )
        return self.answer_conversational
    
if __name__ == "__main__":
    
    # import huggingface_hub as hf
    # print( "hf.__version__", hf.__version__ )
    
    agent = CalendaringAgent( path_to_df="/src/conf/long-term-memory/events.csv", debug=True, verbose=True )

    # question         = "What todo items do I have on my calendar for this week?"
    # question         = "What todo items do I have on my calendar for today?"
    # question         = "Do I have any birthdays on my calendar this week?"
    # question         = "When is Juan's birthday?"
    # question         = "When is Jimmy's birthday?"
    # question         = "When is my birthday?"
    # question           = "What is the date today?"
    # question           = "What time is it in Washington DC? I'm not interested in superfluous precision, so you can omit seconds and milliseconds"
    # question           = "What day of the week is today?"
    question           = "What's today's date?"
    timer            = sw.Stopwatch( msg=f"Processing [{question}]..." )
    response_dict    = agent.run_prompt( question )
    
    # agent.print_code()
    
    code_response    = agent.run_code()
    formatted_output = agent.format_output()
    #
    timer.print( use_millis=True )
    #
    du.print_banner( question, prepend_nl=False )
    for line in formatted_output.split( "\n" ):
        print( line )
        
    