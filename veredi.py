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
import os

# ---
# Veredi: Misc
# ---
from veredi.logger import log

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

    # parser.set_defaults(func=cmd_base)

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
    _init_cmd_session(subparsers)


def _init_cmd_roll(subparsers):

    roll_parser = subparsers.add_parser(
        'roll',
        help=("Takes a dice expression (e.g. '3d20 + 12 + d6 - d10 / 2'), "
              "rolls the dice, does the math, and returns the results."))

    # Arg for type/system (e.g. d20)?
    # §-TODO-§ [2020-04-26]: type/system?

    roll_parser.add_argument('expression', nargs='*')
    roll_parser.set_defaults(func=cmd_roll)


def _init_cmd_session(subparsers):

    roll_parser = subparsers.add_parser(
        'session',
        help=("Loads a game's/session's data (players, etc). Then takes a dice "
              "expression (e.g. '3d20 + $str_mod + d6 - d10 / 2'), "
              "rolls the dice, does the math, and returns the results."))

    # Arg for type/system (e.g. d20)?
    # §-TODO-§ [2020-04-26]: type/system?

    roll_parser.add_argument('-c', '--campaign',
                             type=str,
                             required=True,
                             help='Name of game/campaign.')

    roll_parser.add_argument('-p', '--player',
                             type=str,
                             action='append',
                             nargs=2,
                             required=True,
                             metavar=('user-name', 'player-name'),
                             help='Name of game/campaign.')

    roll_parser.add_argument('expression', nargs='*')
    roll_parser.set_defaults(func=cmd_session)


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
# Other Setup Functions
# ------------------------------------------------------------------------------

def _init_logging():
    log.init()
    log.debug("test?")

# ------------------------------------------------------------------------------
# Sub-command Entry Points
# ------------------------------------------------------------------------------

# def cmd_base(args):
#     print("Veredi has nothing to do...")


def cmd_roll(args):
    from veredi.roll.d20.parser import parse_input

    expression = ' '.join(args.expression)
    print("input: ", expression)
    print("rolled:", parse_input(expression))


def cmd_session(args):
    import veredi.game.session
    import veredi.repository.player
    # from veredi.roll.d20.parser import parse_input

    # ---
    # Repository Setup
    # ---
    root_data_dir = os.path.join(os.getcwd(),
                                 "..",  # Test dir is sibling of veredi code dir
                                 "test",
                                 "data",
                                 "repository",
                                 "file",
                                 "json")
    root_human_dir = os.path.join(root_data_dir,
                                  "human")
    root_hashed_dir = os.path.join(root_data_dir,
                                   "hashed")
    repo_human = repository.player.PlayerRepository_FileJson(
        root_human_dir,
        repository.player.PathNameOption.HUMAN_SAFE)

    # ---
    # Session Setup
    # ---
    players = [("us1!{er", "jeff")]
    session = game.session.Session("some-forgotten-campaign",
                                   players,
                                   repo_human)

    # ---
    # Roll one thing and throw it all away! ^_^
    # ---
    expression = ' '.join(args.expression)
    print("input: ", expression)
    print("rolled:", session.roll("jeff", expression))


# -----------------------------------Veredi------------------------------------
# --                     Main Command Line Entry Point                       --
# -----------------------------------------------------------------------------

if __name__ == '__main__':
    # ---
    # Setup
    # ---
    _init_logging()

    # Setup parser and read command inputs into `_args`.
    parser = _init_parser()
    args = _parse_args(parser)

    # ---
    # Run
    # ---
    subcommand = getattr(args, 'func', None)
    if subcommand is not None:
        subcommand(args)
    else:
        # No subcommand found - print error message and help to stderr.
        import sys
        print("Sub-command not found.\n", file=sys.stderr)

        # Examples:
        print("Examples:")
        print(' '.join([" ",
                        "doc-veredi python -m veredi",
                        "roll",
                        # dice expression
                        "d20 + 11"]))
        print(' '.join([" ",
                        "doc-veredi python -m veredi",
                        "session",
                        # campaign name
                        "-c some-forgotten-campaign",
                        # player 1
                        "-p 'us1!{er' jeff",
                        # (can do more players...)

                        # dice expression
                        "d20 + '$str_mod'"]))
        print("\n")

        parser.print_help(sys.stderr)
        sys.exit(1)

    # print("-" * 10)
    # print("Veredi dice roller:")
    # print("-" * 10)
    # user_data = input("roll> ")
