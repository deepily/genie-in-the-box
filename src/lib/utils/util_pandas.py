import os

import lib.utils.util as du

import pandas as pd


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

def read_csv( path, *args, **kwargs ):
    
    ddf = DeepilyDataFrame.read_csv( path, *args, **kwargs )
    
    return ddf
    
class DeepilyDataFrame( pd.DataFrame ):
    
    # Path attribute to store the file path
    _metadata = [ '_path' ]
    
    def __init__( self, *args, path=None, **kwargs ):
        super().__init__( *args, **kwargs )
        self._path = path
    
    @property
    def _constructor( self ):
        
        # Informs pandas that any method that is supposed to return a data frame returns a deepily data frame instead
        return DeepilyDataFrame
    
    @classmethod
    def read_csv( cls, path, *args, **kwargs ):
        
        data = pd.read_csv( path, index_col=None, *args, **kwargs )
        
        return cls( data=data, path=path )
    
    def save( self, path=None ):
        # Save DataFrame to its original path or to a specified new path
        if path is None:
            if self._path is None:
                raise ValueError( "Path is not specified" )
            path = self._path
        
        if path.endswith( '.csv' ):
            self.to_csv( path, index=False )
        else:
            raise ValueError( "Unsupported file type" )
        
        # Set world read and write on this path
        os.chmod( path, 0o666 )
        
        return path
    
if __name__ == '__main__':
    
    # df = DeepilyDataFrame.read_csv( du.get_project_root() + "/src/conf/long-term-memory/events.csv" )
    df = read_csv( du.get_project_root() + "/src/conf/long-term-memory/todo.csv" )
    
    # print( type( df ))
    print( df.head() )
    
    # df = df.drop( index=[ 0, 1 ] )
    # print( df.head() )
    
    df.save()
    
    
