import datetime as dt

class Stopwatch:
    
    def __init__( self, msg=None, silent=False  ):
        
        # This is helpful for suppressing/halving output when it's essentially going to be reproduced later when a task is completed
        if msg and not silent: print( msg )
        
        self.init_msg   = msg
        self.silent     = silent
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
        
        # build msg argument
        if msg is None and self.init_msg is None:
            msg = "Finished"
        elif msg is None and self.init_msg is not None:
            msg = self.init_msg
        elif msg is not None and self.init_msg is not None:
            msg = self.init_msg + " " + msg
        
        # preformat output
        if prepend_nl and not self.silent: print()
        
        if use_millis:
            
            # From: https://stackoverflow.com/questions/766335/python-speed-testing-time-difference-milliseconds
            delta = dt.datetime.now() - self.start_time
            millis = int( delta.total_seconds() * 1000 )
            
            if not self.silent: print( "{0} in {1:,} ms".format( msg, millis ), end=end )
        
        elif seconds > 59:
            
            # From: https://stackoverflow.com/questions/775049/how-do-i-convert-seconds-to-hours-minutes-and-seconds
            minutes, seconds = divmod( seconds, 60 )
            if not self.silent: print( "{0} in {1:02d}:{2:02d}".format( msg, minutes, seconds ), end=end )
        
        else:
            if not self.silent: print( "{0} in {1:,} seconds".format( msg, seconds ), end=end )
    
    def get_delta_ms( self ):
    
        """
        Calculate the delta between now and when this object was instantiated

        :return: Time delta in milliseconds
        """
        self.end_time     = dt.datetime.now()
        self.elapsed_time = self.end_time - self.start_time
        self.delta_ms     = int( self.elapsed_time.total_seconds() * 1000 )
        
        return self.delta_ms
    

if __name__ == '__main__':
    
    timer = Stopwatch()
    timer.print( "Finished doing foo" )
    timer.print( None )
    timer.print()


