import configparser
import os
import sys

lib_path = "/var/ampe/src/lib"
if lib_path not in sys.path:
    sys.path.append( lib_path )

import lib.utils.util as du

# Idea for the "singleton" decorator: https://stackabuse.com/creating-a-singleton-in-python/
def singleton( cls ):
    
    instances = { }
    
    def wrapper( *args, **kwargs ):
        
        if cls not in instances:
            print( "Instantiating ConfigurationManager() singleton...", end="\n\n" )
            instances[ cls ] = cls( *args, **kwargs )
        else:
            print( "Reusing ConfigurationManager() singleton..." )
            
        return instances[ cls ]
    
    return wrapper

@singleton
class ConfigurationManager():
    
    def __init__( self, env_var_name=None, config_path=None, splainer_path=None, config_block_id="default", debug=False, verbose=False, silent=False, cli_args=None ):

        """
        Instantiates configuration manager object
        
        :param env_var_name: If set, then the configuration manager will look for three environment variables: config_path, splainer_path and config_block_id

        :param config_path: Fully qualified path to configuration file
        
        :param splainer_path: Fully qualified path to splainer file

        :param config_block_id: [Text identifying which block to read from] Defaults to global 'default' block

        :param debug: Defaults to False

        :param verbose: Defaults to False

        :param silent: Shuts off *all* configuration/startup output to console.  Use when you're sure that your configuration is solid.
        """
        self.debug           = debug
        self.verbose         = verbose
        self.silent          = silent
        
        if env_var_name is not None:
            
            print( f"Using environment variables to instantiate configuration manager" )
            
            if env_var_name not in os.environ: raise ValueError( f"[{env_var_name}] is NOT set" )
            
            # Three arguments need to be set when using env_var_name variables
            cli_args = os.environ[ env_var_name ].split( " " )
            cli_args = du.get_name_value_pairs( cli_args )
            
            self.config_path     = du.get_project_root() + cli_args[ "config_path" ]
            self.splainer_path   = du.get_project_root() + cli_args[ "splainer_path" ]
            
            self.config_block_id = cli_args[ "config_block_id" ]
            
            # Now delete those three keys from cli_args
            del cli_args[ "config_path" ]
            del cli_args[ "splainer_path" ]
            del cli_args[ "config_block_id" ]
        
        else:
            self.config_path     = config_path
            self.splainer_path   = splainer_path
            self.config_block_id = config_block_id

        # set by call below
        self.config          = None
        self.splainer        = None
        
        self.init(
            config_block_id=self.config_block_id, config_path=self.config_path, splainer_path=self.splainer_path, debug=debug, verbose=verbose, silent=silent, cli_args=cli_args
        )

    def init( self, config_block_id=None, config_path=None, splainer_path=None, silent=False, debug=False, verbose=False, cli_args=None ):

        # update paths, if provided
        if config_path is not None:
            self.config_path = config_path.strip()
        if splainer_path is not None:
            self.splainer_path = splainer_path.strip()

        du.sanity_check_file_path( self.config_path,   silent=silent )
        du.sanity_check_file_path( self.splainer_path, silent=silent )
        
        if not self.silent:
            du.print_banner( f"Initializing configuration_manager [{self.config_path}]", prepend_nl=True, end="\n" )
            print( f"Splainer path [{self.splainer_path}]", end="\n\n" )

        self.silent          = silent
        self.config          = configparser.ConfigParser()
        if config_block_id is not None:
            self.config_block_id = config_block_id

        self.config.read( self.config_path )

        self._sanity_check_config_block( self.config_block_id )

        if self.debug and self.verbose and not self.silent:
            print( "Path:", config_path )
            print( "Block ID:", config_block_id, end="\n\n" )

        if not self.silent: self.print_sections()
        self._calculate_inheritance()
        self._calculate_defaults()
        self._override_configuration( cli_args )
        self._load_splainer_definitions()

    def _override_configuration( self, cli_args ):

        """
        Overrides configuration based on file key=value pairs

        :param cli_args: Dictionary containing overriding key=value pairs

        :return: None
        """

        # overwrite current configuration values if the cli_args {} has anything to add...
        if cli_args is not None and len( cli_args ) > 0:

            for key in cli_args.keys():

                # ...but don't override config_path and config_block_id, they're immutable
                if key != "config_path" and key != "config_block_id":

                    print( "Overriding [{0}] with [{1}]".format( key, cli_args[ key ] ) )
                    self.set_config( key, cli_args[ key ] )

                elif key == "config_path":
                    print( "Skipping override of [config_path], it's immutable" )
                else:
                    print( "Skipping override of [config_block_id], it's immutable" )
            print()

        else:

            if self.debug: print( "Skipping cli_args processing" )

    def _calculate_defaults( self ):

        if not self.silent: du.print_banner( "Calculating defaults...", prepend_nl=True )

        # All configurations get default values, except for the default config
        if self.config_block_id != "default":

            for key in self.config.options( "default" ):

                if self.debug and self.verbose: print( "Inserting default key [{0}] = [{1}] into [{2}]".format( key, self.config.get( "default", key ), self.config_block_id ) )
                self.config.set( self.config_block_id, key, self.config.get( "default", key ) )

        else:
            if not self.silent: print( "Not adding default key=pair values because we're already in the 'default' block" )

    def _calculate_inheritance( self ):

        if not self.silent: du.print_banner( "Calculating inheritance... * = parent block" )

        parent_block_keys = self.config.options( self.config_block_id )

        if "inherits" in parent_block_keys:

            inherits_from = self.get( "inherits" )

            # Only sanity check inheritance if it's not a file
            if not os.path.isfile( inherits_from ):

                self._sanity_check_config_block( inherits_from )
                inheritance_list = [ inherits_from ]
            else:
                inheritance_list = []

            if not self.silent: print( "* [{0}] inherits from [{1}]".format( self.config_block_id, inherits_from ) )

            # Entry point for recursive list building is the originally specified configuration block ID's inherits key
            inheritance_list = self._build_inheritance_list( inherits_from, inheritance_list )

            # flip it...
            inheritance_list.reverse()

            key_value_pairs = dict()
            if self.debug and self.verbose: print( "Reading key=value pairs in inheritance_list, reversed:", end="\n\n" )

            # iterate blocks, grabbing key=value pairs and stashing them in a dictionary
            for idx, block_id in enumerate( inheritance_list ):

                if self.debug and self.verbose: print( "[{0}]th block id [{1}]".format( idx, block_id ) )

                if os.path.isfile( block_id ):

                    key_value_pairs = self._load_key_value_pairs_from_file( block_id, key_value_pairs )

                else:

                    keys = self.config.options( block_id )

                    for key in keys:

                        key_value_pairs[ key ] = self.config.get( block_id, key )
                        if self.debug and self.verbose: print(
                            "[{0}]th block id [{1}] [{2}]=[{3}]".format( idx, block_id, key, key_value_pairs[ key ] ) )

            # print()
            self._scan_and_update_keys( key_value_pairs, parent_block_keys )

        else:

            if not self.silent: print( "No inheritance flag found" )

        # print()

    def _load_key_value_pairs_from_file( self, config_path, key_value_pairs ):

        """
        Loads key value pairs from a file

        :param config_path: path to config file

        :param key_value_pairs: Dictionary to hold new key value pairs

        :return: Dictionary of updated key value pairs
        """

        if self.verbose and self.debug: print( "_load_key_value_pairs_from_file(...) called" )
        temp_config = configparser.ConfigParser()
        temp_config.read( config_path )

        # Assumes that "base" is the default block
        block_id = "base"

        # Sanity check: is the base block present?
        fail_msg = "Configuration block doesn't exist: [{0}] Check spelling?".format( block_id )
        assert block_id in temp_config.sections(), fail_msg

        keys = temp_config.options( "base" )

        # Iterate and update key value pairs
        if self.debug and self.verbose: print()
        for key in keys:

            value = temp_config.get( block_id, key )
            key_value_pairs[ key ] = value
            if self.debug and self.verbose: print( "  From [{0}], [{1}] = [{2}]".format( config_path, key, value ) )

        if self.debug and self.verbose: print()

        return key_value_pairs

    def _scan_and_update_keys( self, key_value_pairs, parent_block_keys ):

        """
        Scans keys and adds them to the parent block

        NOTE: Only adds keys to the parent block if they do not violate immutability and scoping rules

        :param key_value_pairs: key=value pairs found *outside* of the parent block. Candidates to be added to the parent config block ID

        :param parent_block_keys: key=value pairs found *inside* the parent block

        :return: None
        """

        if not self.silent: print( "Scanning for immutable keys..." )
        found = False

        # Scan parent_block keys for immutables found outside default block
        rule = "{0} [{1}]: Keys that start with '@_' -- outside of the 'default' block -- violate immutability and scoping rule"
        keys = self.config.options( self.config_block_id )
        for key in keys:
            if key.startswith( "@_" ):
                if not found: print()
                print( rule.format( "Removing", key ) )
                self.config.remove_option( self.config_block_id, key )
                found = True

        # Now that we've got all the inherited values, add them to config block ID...
        # ...Taking care not to overwrite values in config block ID
        for key in key_value_pairs.keys():

            if key.startswith( "@_" ):
                if not found: print()
                print( rule.format( "Ignoring", key ) )
                found = True
            elif key not in parent_block_keys:
                self.config.set( self.config_block_id, key, key_value_pairs[ key ] )
            else:
                if self.debug and self.verbose: print( "Skipping key [{0}], it's already set in [{1}]".format( key, self.config_block_id ) )

        if found: print()
        if not self.silent: print( "Scanning for immutable keys... Done!" )

    def _build_inheritance_list( self, block_id, inheritance_list ):

        if self.debug and self.verbose: print( "_build_inheritance_list() called for [{0}]...".format( block_id ) )

        # kludgey little Short circuit for when the block ID is a file reference
        if os.path.isfile( block_id ):

            if not self.debug and self.verbose: print( "block_id is a file [{0}]".format( block_id ) )
            # TODO: Why is this necessary? block ID was being added twice to this list!?!
            if block_id not in inheritance_list:
                inheritance_list.append( block_id )
            # else:
                # print( "Skipping adding [{0}], it's already in the inheritance list?!?".format( block_id ) )

            return inheritance_list

        # Continue with standard inheritance this building
        this_blocks_keys = self.config.options( block_id )

        if "inherits" not in this_blocks_keys:

            if self.debug and self.verbose: print( "No inheritance flag found in [{0}]".format( block_id ) )

        else:

            inherits_from = self.config.get( block_id, "inherits" )

            # Perform sanity check if it's not a file
            if not os.path.isfile( inherits_from ):
                self._sanity_check_config_block( inherits_from )

            inheritance_list.append( inherits_from )
            if not self.silent: print( "  [{0}] inherits from [{1}]".format( block_id, inherits_from ) )

            inheritance_list = self._build_inheritance_list( inherits_from, inheritance_list )

        return inheritance_list

    def _sanity_check_config_block( self, block_id ):

        """
        Verifies that a config block ID exists

        NOTE: Also detects if a block ID looks like a file path for a file that doesn't exist

        :param block_id: Block ID to be checked

        :return: None

        :raises: FileNotFoundError or AssertionError when block ID doesn't exist in configuration
        """

        if block_id.startswith( "/var/ampe/" ) and not os.path.isfile( block_id ):

            raise FileNotFoundError( "File NOT found [{0}] Update & try again?".format( block_id ) )

        fail_msg = "Configuration block doesn't exist: [{0}] Check spelling?".format( block_id )
        assert block_id in self.config.sections(), fail_msg

    def print_sections( self ):

        sections = self.config.sections()
        sections.sort()

        du.print_banner( "Sections, '*' = current block ID" )

        for section in sections:

            if section == self.config_block_id:
                print( "*", section )
            else:
                print( " ", section )

        print()

    def set_config( self, config_key, value ):

        """
        Sets or updates key=value pairs in the current_block_id

        This is *super* helpful when you want to make minor temporary tweaks to a particular modeling session, or if you
        want to compare two customized sessions whose only diffs are the values set at runtime by this method.

        :param config_key: The 'key' part of the 'key=value' configuration pair

        :param value: The 'value' part of the 'key=value' configuration pair

        :return: None
        """

        self.config.set( self.config_block_id, config_key, str( value ) )

    def in_config( self, config_key ):

        """
        Checks to see if config_key exists in current config_block_id

        Using this in conjunction w/ the get_value( "foo" ) method allows us to create optional key=value configuration pairs

        :param config_key: The 'key' part of the configuration 'key=value' pair found in this sessions config_block_id

        :return: True | False
        """

        return config_key in self.config.options( self.config_block_id )


    def print_configuration( self, brackets=True, include_sections=True, prefixes=None ):

        """
        High level wrapper to _print_configuration_to_stdout()

        Prints current configuration key=value pairs to console, sorted & segregated by stems

        :param brackets: Formatting option that adds brackets to name=value pairs

        :param include_sections: What section is this configuration based on? Defaults to True

        :param prefixes: array of prefixes to match

        :return: None, prints to console

        Example:
        <pre><code>
        %autoreload

        # force silent configuration object update
        ampe.init_configuration( config_block_id, silent=True )

        # print out the goodies
        ampe.print_configuration( brackets=False )

        @_default_analysis_type          = retention
        @_default_creds_db_path          = /var/ampe/src/creds/credentials-db-seu.json
        @_default_creds_s3_path          = /var/ampe/src/creds/credentials-s3-seu.txt
        @_default_model_type             = classification
        @_default_pred_features_table    = iss_rruiz.retention_model_features
        @_default_predictions_table      = iss_rruiz.retention_predictions
        @_default_s3_bucket_name         = ste-stg
        @_default_s3_to_redshift_sql     = /var/ampe/src/sql/load-s3-predictions-into-redshift.sql
        @_default_s3_user_name           = rruiz
        @_default_target_name            = enrolled_next_fall

        clean_values_to_exclude          = Fall 2020

        feature_new_target_name          = enrolled_next_fall

        # Remaining configuration output truncated
        </code></pre>
        """

        # Let them know what this configuration set is based on
        if include_sections: self.print_sections()

        keys     = self.config.options( self.config_block_id )
        block_id = self.config_block_id

        # filter by prefixes?
        # Using None as the default to address the 'prefixes is mutable object' objection:
        # https://stackoverflow.com/questions/41686829/warning-about-mutable-default-argument-in-pycharm
        if prefixes is not None and len( prefixes ) > 0:

            matches = []

            for key in keys:
                for prefix in prefixes:
                    if key.startswith( prefix ):
                        matches.append( key )

            # reduce dupes?
            keys = list( set( matches ) )

            # bail if there's nothing to print
            if len( keys ) == 0:
                print( "No configuration keys to print" )
                return

        du.print_banner( "Configuration for [{0}]".format( self.config_block_id ), end="\n" )
        self.print_configuration_to_stdout( keys, self.config, block_id, brackets )

    def get_keys( self ):

        """
        Gets keys for current session configuration

        :return: list of keys
        """

        return self.config.options( self.config_block_id )

    def print_configuration_to_stdout( self, keys, configuration, block_id, brackets=True ):

        """
        Private abstracted view of printing configuration key=value pairs

        Prints sorted contents of configuration object to the console

        :param keys: List of keys to be looked up in the configuration object

        :param configuration: Object

        :param block_id: Title of config block to be used

        :param brackets: Do we want the 'value' half of the 'key=value' pair to be bracketed? Good for debugging [expected_values]

        :returns: None
        """

        keys.sort()

        # brackets, by default
        lb = "["
        rb = "]"

        # remove brackets?
        if not brackets: lb = rb = ""

        # get max key len for left justification
        max_len = max( len( key ) for key in keys )
        last_stem = ""

        for key in keys:

            # inserts blank line between different stems
            stem = key.split( "_" )[ 0 ]
            if stem != last_stem: print()
            last_stem = stem

            value = configuration.get( block_id, key )
            print( "{0} = {1}{2}{3}".format( key.ljust( max_len, ' ' ), lb, value, rb ) )
            
        print()

    # def get( self, key, default="@@@_None_@@@", silent=False, return_type="string" )
    def get( self, key, default="@@@_None_@@@", silent=False, return_type="string" ):
    
        """
        Wrapper for accessing configuration object
    
        Designed to catch missing keys in the current configuration file and explain them according to the contents of
        the splainer-doc.ini file.  If no key is found, and after giving you splainer feedback, it returns None to the
        calling code, which then fails.  Hopefully this will help you to understand why it failed.
    
        :param key: The 'key' half of the 'key=value' pair
    
        :param default: Allows you to specify a value to return when there's no value to be found in the 'key=value' pair
        NOTE: current default="@@@_None_@@@", essentially making "@@@_None_@@@" a reserved word, ¡OJO!
    
        :param silent: Turn off the 'splainer messaging, useful for stealth feature addition.  Defaults to False
    
        :param return_type: Which of the five types should this value be returned as? Accepts: 'boolean', 'float', 'int/integer',
        'str/string' and 'list-string' Defaults to 'string'
    
        :return: Typed representation of the 'value' half of the 'key=value' pair
        """
    
        if self.in_config( key ):
    
            # Get the value
            value = self.config.get( self.config_block_id, key )
            # value = self.config.get( key )
    
            return self._get_typed_value( value, return_type )
    
        else:
    
            # If there's a default specified, then return it
            if default != "@@@_None_@@@":
    
                # only 'splain them when called for
                if not silent and not self.mute_splainer:
    
                    du.print_banner( "Key [{0}] NOT found, returning default [{1}]".format( key, default ), end="\n" )
                    self.splain_me( key )
    
                # return typed default
                return self._get_typed_value( default, return_type )
    
            else:
            
                print()
                du.print_banner( "Key [{0}] NOT found".format( key ), end="\n" )
                self.splain_me( key )
    
                return None

    def _get_typed_value( self, value, return_type ):

        """
        Casts the string value to the requested type. Helper method for get(...)

        :param value: String representing the raw value

        :param return_type: Which of the five types should this value be returned as? Accepts: 'boolean', 'float', 'int/integer',
            'str/string' and 'list-string' Throws ValueError if not one of these five. NOT case sensitive.

        :return: Input value cast to specified type
        """
        # Force return type to lowercase
        return_type = return_type.lower()

        if return_type == "boolean":
            # Allow the default value to be passed in as a Boolean or as a string
            return value == "True" or value is True
        elif return_type == "float":
            return float( value )
        elif return_type.startswith( "int" ):
            return int( value )
        elif return_type.startswith( "str" ):
            return value
        elif return_type == "list-string":
            return value.split( ", " )
        else:
            raise ValueError( f"Return type [{return_type}] is invalid.  Accepts: 'boolean', 'float', 'int', 'string' and 'list-string'".format( return_type ) )
        
    def splain_me( self, key, end="\n\n" ):

        """
        Colloquial lookup of configuration key definitions, prints to console.

        :param key: Term to lookup in the splainer dictionary

        :param end: Formatting option, use "\n" for one carriage return

        :return: None

        Example:
        <pre><code>
        ampe.splain_me( "42" )

        [42] = I'm sorry Dave, I'm afraid I can't tell you that.  You could ask Douglas Adams though.

        ampe.splain_me( "flux_capacitor" )

        [flux_capacitor] = A Y-shaped electronic device that's essential to time travel
        </code></pre>
        """

        if key in self.splainer.options( "default" ):

            definition = self.splainer.get( "default", key )
            print()
            print( "'Splainer says: [{0}] = {1}".format( key, definition ), end=end )

        else:

            print( "\n'Splainer says: ¿WUH? The key [{0}] NOT found in the 'splainer.ini file. "
                   "Check spelling and/or contact the AMPE project maintainer?".format( key ), end=end )

    def _load_splainer_definitions( self ):

        """
        Loads the splainer doc

        :param splainer_path: Where's the 'splainer file located?

        :return: None
        """

        splainer = configparser.ConfigParser()
        splainer.read( du.get_project_root() + self.splainer_path )

        self.splainer = splainer
    
if __name__ == "__main__":

    # for key, value in os.environ.items():
    #     print( f"{key} = {value}" )
    # print()
    # print( "GIB_CONFIG_MGR_CLI_ARGS" in os.environ )
    
    # config_path     = du.get_project_root() + "/src/conf/gib-app.ini"
    # splainer_path   = du.get_project_root() + "/src/conf/gib-app-splainer.ini"
    # config_block_id = "Genie in the Box: Development"
    # config_manager  = ConfigurationManager( config_path, splainer_path, config_block_id=config_block_id, debug=False, verbose=False, silent=False )
    
    config_manager  = ConfigurationManager( env_var_name="GIB_CONFIG_MGR_CLI_ARGS" )

    foo_mgr         = ConfigurationManager( env_var_name="GIB_CONFIG_MGR_CLI_ARGS" )
    
    # foo_mgr         = ConfigurationManager( config_path, splainer_path, config_block_id=config_block_id, debug=False, verbose=False, silent=False )
    
    # config_manager.print_configuration( brackets=True )
    #
    # foo = config_manager.get( "foo" )
    # print( f"foo: [{foo}] type: [{type( foo )}]" )
