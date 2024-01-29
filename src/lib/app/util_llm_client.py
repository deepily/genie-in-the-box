import re

from lib.utils.util_stopwatch import Stopwatch

def query_llm_in_memory( model, tokenizer, prompt, device="cuda:0", model_name="ACME LLMs, Inc.", max_new_tokens=128, silent=False ):

    timer = Stopwatch( msg=f"Asking LLM [{model_name}]...".format( model_name ), silent=silent )
    
    inputs        = tokenizer( prompt, return_tensors="pt" ).to( device )
    stop_token_id = tokenizer.encode( "</response>" )[ 0 ]
    
    generation_output = model.generate(
        input_ids=inputs[ "input_ids" ],
        attention_mask=inputs[ "attention_mask" ],
        max_new_tokens=max_new_tokens,
        eos_token_id=stop_token_id,
        pad_token_id=stop_token_id
    )
    
    # Skip decoding the prompt part of the output
    input_length = inputs[ "input_ids" ].size( 1 )
    raw_output   = tokenizer.decode( generation_output[ 0 ][ input_length: ] )
    
    timer.print( msg="Done!", use_millis=True, end="\n" )
    # If we don't include the length of the input tokens then we get an artificially inflated TPS value (Relative to the TPS value calculated by hugging faces TGI),
    # so add it back in here
    tokens_per_second = ( len( raw_output ) + input_length ) / ( timer.get_delta_ms() / 1000.0 )
    print( f"Tokens per second [{round( tokens_per_second, 1 )}]" )
    
    # response   = raw_output.split( "### Response:" )[ 1 ]
    
    # Remove the <s> and </s> tags
    response = raw_output.replace( "</s><s>", "" ).strip()
    # Remove white space outside XML tags
    response = re.sub( r'>\s+<', '><', response )
    
    return response