#!python3

'''
Command line entry point for Veredi.

For usage:
$ ./veredi.py help
'''


# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

# ---
# Python
# ---
import argparse


# ---
# Veredi: Dice
# ---


# ---
# Commands
# ---


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

PARSER_DESC = (
    "Runs inputs through Veredi and returns results."
)


# -----------------------------------------------------------------------------
# Script Helper Functions
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Parser Setup Functions
# -----------------------------------------------------------------------------

def _init_args(parser):
    '''Adds arguments to ArgumentParser `parser`.

    Args:
      parser: argparse.ArgumentParser

    Returns:
      argparse.ArgumentParser with arguments added

    '''
    _parser.add_argument(
        '--verbose', '-v',
        action='count',
        default=0,
        help=("Verbosity Level. Use multiple times for more verbose, "
              "e.g. '-vvv'."))

    _parser.add_argument(
        '--dry-run',
        action='store_true',
        help=('Set dry-run flag if script should not make any '
              'changes to the saved data.'))

    # §-TODO-§ [2020-04-21]: repository pattern type
    #   e..g.? "file/yaml", "db/sqlite3"?


def _init_subcommands(parser):
    '''Has all subcommands register themselves with the parser.

    Args:
      parser: argparse.ArgumentParser

    Returns:
      argparse.ArgumentParser with arguments added

    '''
    # §-TODO-§ [2020-04-21]: this?
    pass


def _init_parser():
    '''Initializes argparse parser for this script.

    Returns:
      argparse.ArgumentParser ready to go

    '''
    _parser = argparse.ArgumentParser(description=PARSER_DESC)

    _init_args(_parser)
    _init_subcommands(_parser)

    return _parser


def _parse_args(parser):
    '''Parse command line input.

    Args:
      parser: argparse.ArgumentParser

    Returns:
      args (output of argparse.ArgumentParser.parse_args())

    '''
    return parser.parse_args()

# -----------------------------------Veredi------------------------------------
# --                     Main Command Line Entry Point                       --
# -----------------------------------------------------------------------------

if __name__ == '__main__':
    # ---
    # Setup
    # ---
    # Setup parser and read command inputs into `_args`.
    _parser = _init_parser()
    _args = _parse_args(_parser)

    # ---
    # Run
    # ---
    print("Hello there.")
