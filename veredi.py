#!python3 -*- coding: utf-8 -*-

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
    parser.add_argument(
        '--verbose', '-v',
        action='count',
        default=0,
        help=("Verbosity Level. Use multiple times for more verbose, "
              "e.g. '-vvv'."))

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help=('Set dry-run flag if script should not make any '
              'changes to the saved data.'))

    # Â§-TODO-Â§ [2020-04-21]: repository pattern type
    #   e..g.? "file/yaml", "db/sqlite3"?


def _init_subcommands(parser):
    '''Has all subcommands register themselves with the parser.

    Args:
      parser: argparse.ArgumentParser

    Returns:
      argparse.ArgumentParser with arguments added

    '''
    # Â§-TODO-Â§ [2020-04-21]: this?
    subparsers = parser.add_subparsers(help='sub-command help')
    #  - title - title for the sub-parser group in help output; by default
    #            “subcommands” if description is provided, otherwise uses title
    #            for positional arguments
    #
    #  - description - description for the sub-parser group in help output, by
    #                  default None
    #
    #  - prog - usage information that will be displayed with sub-command help,
    #           by default the name of the program and any positional arguments
    #           before the subparser argument
    #
    #  - parser_class - class which will be used to create sub-parser instances,
    #                   by default the class of the current parser
    #                   (e.g. ArgumentParser)
    #
    #  - action - the basic type of action to be taken when this argument is
    #             encountered at the command line
    #
    #  - dest - name of the attribute under which sub-command name will be
    #           stored; by default None and no value is stored
    #
    #  - required - Whether or not a subcommand must be provided, by default
    #               False (added in 3.7)
    #
    #  - help - help for sub-parser group in help output, by default None
    #
    #  - metavar - string presenting available sub-commands in help; by default
    #              it is None and presents sub-commands in form {cmd1, cmd2, ..}

    _init_cmd_roll(subparsers)


def _init_cmd_roll(subparsers):

    roll_parser = subparsers.add_parser(
        'roll',
        help=("Takes a dice expression (e.g. '3d20 + 12 + d6 - d10 / 2'),"
              "rolls the dice, does the math, and returns the results."))

    # Arg for type/system (e.g. d20)?
    # §-TODO-§ [2020-04-26]: type/system?

    roll_parser.add_argument('expression', nargs='*')
    roll_parser.set_defaults(func=roll)


def _init_parser():
    '''Initializes argparse parser for this script.

    Returns:
      argparse.ArgumentParser ready to go

    '''
    parser = argparse.ArgumentParser(description=PARSER_DESC)

    _init_args(parser)
    _init_subcommands(parser)

    return parser


def _parse_args(parser):
    '''Parse command line input.

    Args:
      parser: argparse.ArgumentParser

    Returns:
      args (output of argparse.ArgumentParser.parse_args())

    '''
    return parser.parse_args()


# ------------------------------------------------------------------------------
# Sub-command Entry Points
# ------------------------------------------------------------------------------

def roll(args):
    from roll.parsing.d20.parser import parse_input

    expression = ' '.join(args.expression)
    print("input: ", expression)
    print("rolled:", parse_input(expression))


# -----------------------------------Veredi------------------------------------
# --                     Main Command Line Entry Point                       --
# -----------------------------------------------------------------------------

if __name__ == '__main__':
    # ---
    # Setup
    # ---
    # Setup parser and read command inputs into `_args`.
    parser = _init_parser()
    args = _parse_args(parser)

    # ---
    # Run
    # ---
    args.func(args)
    # print("-" * 10)
    # print("Veredi dice roller:")
    # print("-" * 10)
    # user_data = input("roll> ")
