import datetime as dt
class Stopwatch:
    
    def __init__( self, msg=None  ):
        
        if msg: print( msg )
        self.start_time = dt.datetime.now()
        
    def __enter__( self ):
        
        self.start_time = dt.datetime.now()
        
        return self
    
    def __exit__( self ):
        
        self.end_time = dt.datetime.now()
        self.interval = int( (self.end_time - self.start_time) * 1000 )
        
        print( f"Done in [{self.interval:,}] ms" )
    
    def print( self, msg=None, prepend_nl=False, end="\n\n", use_millis=False ):
        
        """
        Prints time elapsed since instantiation

        If more than 1 minute has passed it uses "mm:ss" format.  Otherwise, it just prints seconds

        ¡OJO!/NOTE: This is fairly simpleminded, it's probably more accurate to use timeit

        :param msg: Text to the output before elapsed time is reported

        :param prepend_nl: Insert a new line before printing to the console, defaults to False

        :param end: Optional text to append to the end of the output, similar to how print works in the standard library.  Defaults to two carriage turns

        :param use_millis: Dump elapsed time in milliseconds to the console. Faults to False

        :return: None, Prince to console only
        """
        
        seconds = (dt.datetime.now() - self.start_time).seconds
        
        # check msg argument
        if msg is None: msg = "Finished"
        
        # preformat output
        if prepend_nl: print()
        
        if use_millis:
            
            # From: https://stackoverflow.com/questions/766335/python-speed-testing-time-difference-milliseconds
            delta = dt.datetime.now() - self.start_time
            millis = int( delta.total_seconds() * 1000 )
            
            print( "{0} in {1:,} ms".format( msg, millis ), end=end )
        
        elif seconds > 59:
            
            # From: https://stackoverflow.com/questions/775049/how-do-i-convert-seconds-to-hours-minutes-and-seconds
            minutes, seconds = divmod( seconds, 60 )
            print( "{0} in {1:02d}:{2:02d}".format( msg, minutes, seconds ), end=end )
        
        else:
            print( "{0} in {1:,} seconds".format( msg, seconds ), end=end )
    
    def get_delta( self ):
        
        """
        Calculate the delta between now and when this object was instantiated

        :return: Time delta in milliseconds
        """
        
        delta = dt.datetime.now() - self.start_time
        millis = int( delta.total_seconds() * 1000 )
        
        return millis

if __name__ == '__main__':
    
    timer = Stopwatch()
    timer.print( "Finished doing foo" )
    timer.print( None )
    timer.print()


