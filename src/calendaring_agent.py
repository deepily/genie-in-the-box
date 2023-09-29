import sys
import os
import json

# os.environ[ "LANGCHAIN_WANDB_TRACING" ] = "true"
# # wandb documentation to configure wandb using env variables
# # https://docs.wandb.ai/guides/track/advanced/environment-variables
# # here we are configuring the wandb project name
# os.environ[ "WANDB_PROJECT" ] = "langchain-dataframe-agent"

# path = "/var/genie-in-the-box/src/lib"
# if path not in sys.path:
#     sys.path.append( path )
# else:
#     print( f"[{path}] already in sys.path" )
#
# print( sys.path )

import lib.util as du
import lib.util_pandas as dup

# path = "/var/genie-in-the-box/src"
# du.add_to_path( path )

import lib.util_stopwatch as sw
# import util_langchain as ulc
import genie_client as gc

from langchain.chat_models import ChatOpenAI
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationalRetrievalChain
from langchain.agents.agent_toolkits.pandas.base import create_pandas_dataframe_agent

from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain

from langchain.schema import (
    AIMessage,
    HumanMessage,
    SystemMessage
)
import langchain

import pandas as pd

class CalendaringAgent:
    
    def __init__( self, path_to_df, debug=False, verbose=False ):
        
        self.langchain         = langchain
        self.path_to_df        = du.get_project_root() + path_to_df
        self.debug             = debug
        self.langchain.debug   = debug
        self.langchain.verbose = verbose
        self.df                = pd.read_csv( self.path_to_df )
        self.df                = dup.cast_to_datetime( self.df )
        
        self.llm_4  = ChatOpenAI( model_name=gc.GPT_4, temperature=0.0 )
        # memory = ConversationBufferMemory( memory_key="chat_history", return_messages=True, verbose=verbose )
        
        self.df_agent = create_pandas_dataframe_agent( self.llm_4, self.df, verbose=verbose )
        template      = self._get_pandas_prompt_template()
        print( template )
        
        prompt = PromptTemplate(
            template=template,
            input_variables=[ "question" ]
        )
        self.llm_chain = LLMChain( prompt=prompt, llm=self.llm_4 )
        # self.df_agent.memory = memory
        
    def run_prompt( self, question ):
        
        timer = sw.Stopwatch( "Running pandas prompt..." )
        question_plus_coda = self._get_question_plus_coda( question )
        self.response      = self.llm_chain.run( question=question_plus_coda )
        timer.print( "Done!" )
        
        return self.response
        
    def _get_pandas_prompt_template( self, question=None):
        
        dtypes = self.df.dtypes
        csv    = self.df.head( 2 ).to_csv( header=True, index=False)
        csv    = csv + self.df.tail( 2 ).to_csv( header=False, index=False )
        
        pandas_prompt_template = f"""
        You are working with a pandas dataframe in Python. The name of the dataframe is `df`.

        This is the ouput from `print(df.head().to_csv())`, in CSV format:

        {csv}
        
        This is the output from `print(df.dtypes)`:

        {dtypes}

        As you generate the python code needed to answer the question asked of you below, I want you to:

        1) Question: Ask yourself if you understand the question that I am asking you
        2) Think: Before you do anything, think out loud about what I'm asking you to do, including what are the steps that you will need to take to solve this problem. Be critical of your thought process!
        3) Code: Generate a verbatim list of code that you used to arrive at your answer, one line of code per item on the list. The code must be complete, syntactically correct, and capable of runnning to completion. The last line of your code must be the variable `solution`, which represents the answer.
        4) Return: Report on the object type of the variable `solution` in your last line of code. Use one word to represent the object type.
        5) Explain: Briefly and succinctly explain your code in plain English.
        
        Format: return your response as a JSON object in the following fields:
        {{
            "question": "The question, verbatim and without modification, that your code attempts to answer",
            "thoughts": "Your thoughts",
            "code": [],
            "return": "Object type of the variable `solution`",
            "explanation": "A brief explanation of your code",
        }}

        Question: {question}
        """
        return pandas_prompt_template
    
    def _get_question_plus_coda( self, event_query ):
        
        question_plus_coda_template = f"""
        {event_query}

        Hint: An event that I have today may have started before today and may end tomorrow or next week, so be careful how you filter on dates.
        Hint: When filtering by dates, use `pd.Timestamp( day )` to convert a Python datetime object into a Pandas `datetime64[ns]` value.
        Hint: If your solution variable is a dataframe, it should include all columns in the dataframe.
        
        Begin!
        """
        return question_plus_coda_template
    
    
# Add main method
if __name__ == "__main__":
    
    agent    = CalendaringAgent( path_to_df="/src/conf/long-term-memory/events.csv", debug=True )
    response = agent.run_prompt( "What concerts do I have today?" )