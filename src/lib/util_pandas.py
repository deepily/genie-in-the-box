import pandas as pd

import lib.util as du

def cast_to_datetime( df, debug=False ):
    
    date_columns = df.select_dtypes( include=[ object ] ).columns.tolist()
    
    for column in date_columns:
        if column.endswith( "_date" ):
            if pd.api.types.is_string_dtype( df[ column ] ):
                df[ column ] = pd.to_datetime( df[ column ] )
    
    # if debug:
    #     du.print_banner( "df.dtypes:", prepend_nl=True, end="\n" )
    #     print( df.dtypes )
        
    return df
