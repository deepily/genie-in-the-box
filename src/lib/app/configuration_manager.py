import configparser
import os
import sys

lib_path = "/var/ampe/src/lib"
if lib_path not in sys.path:
    sys.path.append( lib_path )

import lib.utils.util as du

class ConfigurationManager():

    def __init__( self, config_path, config_block_id="default", debug=False, verbose=False, silent=False, cli_args=None ):

        """
        Instantiates configuration manager object

        :param config_path: Fully qualified path to configuration file

        :param config_block_id: [Text identifying which block to read from] Defaults to global 'default' block

        :param debug: Defaults to False

        :param verbose: Defaults to False

        :param silent: Shuts off *all* configuration/startup output to console.  Use when you're sure that your configuration is solid.
        """
        self.debug           = debug
        self.verbose         = verbose

        # set by call below
        self.silent          = None
        self.config          = None
        self.config_path     = None
        self.config_block_id = None

        self.init( config_block_id=config_block_id, config_path=config_path, silent=silent, cli_args=cli_args )

    def init( self, config_block_id="default", config_path=None, silent=False, cli_args=None ):

        # update config_path, if provided
        if config_path is not None:
            self.config_path = config_path.strip()

        du.sanity_check_file_path( self.config_path )

        du.print_banner( "Initializing configuration_manager [{0}]".format( self.config_path ), prepend_nl=True )

        self.silent          = silent
        self.config          = configparser.ConfigParser()
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

        if not self.silent: du.print_banner( "Calculating defaults..." )

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

            inherits_from = self.get_config( "inherits" )

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

        Example:
        <pre><code>
        %autoreload

        ampe.init_configuration( config_block_id, silent=True )

        # turn off predictive binning for now, it takes ~8 minutes for so many numerics!
        ampe.set_config( "feature_bin_numbers_predictive", False )

        # only run basic dimensionality reduction, w/o full-blown vif analysis
        ampe.set_config( "stage_dimensionality_modules", "generic_dimensionality_reduction" )

        # turn off multiple algorithms, just use xgboost for now
        ampe.set_config( "stage_modeling_modules", "generic_model_build_xgb" )

        # reduce the size of the dataset to speed up turnaround, default is 1.0
        ampe.set_config( "clean_row_resample_rate", 0.1 )

        # raw_df       = ampe.run_ingest_stage( sort=True )
        # hm_df        = ampe.run_harmonization_stage( raw_df.copy() )
        # clean_df     = ampe.run_data_cleaning_stage( hm_df.copy() )
        # fe_df        = ampe.run_feature_engineering_stages( clean_df.copy() )
        # culled_df    = ampe.run_dimensionality_reduction_stages( fe_df.copy() )
        # models_list  = ampe.run_modeling_stages( culled_df )
        # models_list  = ampe.run_post_modeling_stages( models_list )
        </code></pre>
        """

        self.config.set( self.config_block_id, config_key, str( value ) )

    def in_config( self, config_key ):

        """
        Checks to see if config_key exists in current config_block_id

        Using this in conjunction w/ the get_value( "foo" ) method allows us to create optional key=value configuration pairs

        :param config_key: The 'key' part of the configuration 'key=value' pair found in this sessions config_block_id

        :return: True | False

        Example:
        <pre><code>
        ingest_module_key = "stage_adhoc_ingest_module"
        if self.in_config( ingest_module_key ) and self.get_config( ingest_module_key ) != "":
            # Do some optional thing
        </code></pre>
        """

        return config_key in self.config.options( self.config_block_id )

    def get_config( self, config_key, default="[{0}] not found" ):

        #  TODO: Remove original missing key handling into this block *before* deprecating the original code
        if config_key in self.config.options( self.config_block_id ):
            return self.config.get( self.config_block_id, config_key )
        else:
            return default.format( config_key )

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

        du.print_banner( "Configuration for [{0}]".format( self.config_block_id ) )
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

def main():

    print( "[{0}] main() called...".format( os.path.basename( __file__ ) ), end="\n\n" )
    print( "cwd", os.getcwd() )
    
    config_path = du.get_project_root() + "/src/conf/flask-app.ini"
    config_manager = ConfigurationManager( config_path, config_block_id="default", debug=True, verbose=True, silent=False )
    
    config_manager.print_configuration( brackets=True )

if __name__ == "__main__":

    main()