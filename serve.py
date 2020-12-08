# coding: utf-8

'''
Veredi.

All packaged up in one file.

Creates a game engine and server mediator based on a config file.
'''


# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

# ---
# Type Hinting Imports
# ---
from typing import Union, Mapping, NamedTuple


# ---
# Python Imports
# ---
import argparse
import pathlib
import multiprocessing
import multiprocessing.connection
import enum
import signal
import time
from sys import exit


# ---
# Veredi Imports
# ---
from veredi.logger                             import (log,
                                                       log_server,
                                                       log_client)

from veredi.data.exceptions                    import ConfigError
from veredi.data.config.config                 import Configuration
from veredi.game.engine                        import (Engine,
                                                       EngineTickCycle)
from veredi.debug.const                        import DebugFlag


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

# TODO: put these in config?
WAIT_SLEEP_TIME_SEC = 5.0
'''Main process will wait/sleep on the game_over flag for this long each go.'''

GRACEFUL_SHUTDOWN_TIME_SEC = 15.0
'''
Main process will give the game/mediator this long to gracefully shutdown.
If they take longer, it will just terminate them.
'''


@enum.unique
class ProcessType(enum.Enum):
    ENGINE   = 'veredi.run.engine'
    MEDIATOR = 'veredi.run.mediator'
    LOGS     = 'veredi.run.logs'
    MAIN     = 'veredi.run'


class Processes(NamedTuple):
    '''
    Container for info, comms to processes for main proc to hold on to.
    '''
    proc: Mapping[ProcessType, multiprocessing.Process]
    game_end:  multiprocessing.Event
    logs_end:  multiprocessing.Event


# -----------------------------------------------------------------------------
# Veredi Container Init
# -----------------------------------------------------------------------------

def init(config_path: Union[pathlib.Path, str],
         game_data:   Mapping[str, str],
         log_level:   Union[log.Level, int]) -> None:
    '''
    Starts our processes for a game of Veredi:
    The logs server, game engine, and game client/engine mediator.

    Sub-processes create their configuration with the supplied `config_path`.
    Throws if config_path or config file is bad.
    '''
    # Multiprocess set-up.
    mediator_conn, engine_conn = multiprocessing.Pipe()
    processes = Processes({},
                          multiprocessing.Event(),
                          multiprocessing.Event())

    # Set up our processes.
    processes.proc[ProcessType.LOGS] = _init_log(processes.logs_end)

    _check_config(config_path)
    processes.proc[ProcessType.ENGINE] = _init_engine(engine_conn,
                                                      config_path,
                                                      game_data,
                                                      log_level,
                                                      processes.game_end)

    processes.proc[ProcessType.MEDIATOR] = _init_mediator(mediator_conn,
                                                          config_path,
                                                          log_level,
                                                          processes.game_end)

    # Start our own log client now that all the kids are made.
    log_client.init("outdated", log_level)

    return processes


def _init_log(end_flag: multiprocessing.Event) -> None:
    '''
    Initialize Veredi's logger for running a full game.
    '''
    return multiprocessing.Process(
        target=run_logs,
        name=ProcessType.LOGS.value,
        kwargs={
            'shutdown_flag': end_flag,
        })


def _check_config(config_path: Union[pathlib.Path, str]) -> None:
    '''
    Checks config path; doesn't load. Leaves loading up to child processes.
    '''
    # Could be a string; so make sure it's a path.
    config_path = pathlib.Path(config_path)
    if not config_path or not config_path.is_file():
        msg = ("No config path supplied, or config path doesn't point to a "
               f"file: {str(config_path)} "
               f"{'(file does not exist)' if config_path else ''}")
        error = ConfigError(msg,
                            data={
                                'config_path': str(config_path),
                                'is_file': config_path.is_file(),
                            })
        raise log.exception(
            error,
            "No config path supplied, or config path doesn't point to a "
            f"file: {str(config_path)} "
            f"{'(file does not exist)' if config_path else ''}")


def _init_engine(conn:        multiprocessing.connection.Connection,
                 config_path: pathlib.Path,
                 game_data:   Mapping[str, str],
                 log_level:   Union[log.Level, int],
                 end_flag:    multiprocessing.Event) -> None:
    '''
    Initialize Veredi's engine now that we have config data.
    '''
    return multiprocessing.Process(
        target=run_engine,
        name=ProcessType.ENGINE.value,
        kwargs={
            'conn':        conn,
            'config_path': config_path,
            'game_data':   game_data,
            'log_level':   log_level,
            'shutdown_flag': end_flag,
        })


def _init_mediator(conn:        multiprocessing.connection.Connection,
                   config_path: pathlib.Path,
                   log_level:   Union[log.Level, int],
                   end_flag:    multiprocessing.Event) -> None:
    '''
    Initialize Veredi's client/server IO interface mediator.
    '''
    return multiprocessing.Process(
        target=run_mediator,
        name=ProcessType.MEDIATOR.value,
        kwargs={
            'conn':        conn,
            'config_path': config_path,
            'log_level':   log_level,
            'shutdown_flag': end_flag,
        })


# -------------------------------------------------------------------------
# Process Entry Methods
# -------------------------------------------------------------------------

def start(processes: Mapping[str, multiprocessing.Process]) -> None:
    '''
    Tell all the processes to go.
    '''
    # Let it all run and wait for the game to end...
    for each in processes.proc:
        processes.proc[each].start()


def _sigint_ignore() -> None:
    # Child processes will ignore sigint and rely on the main process to
    # tell them to stop.
    signal.signal(signal.SIGINT, signal.SIG_IGN)


def run_logs(shutdown_flag: multiprocessing.Event = None) -> None:
    '''
    Inits and runs logging server.
    '''
    _sigint_ignore()
    server = log_server.init()

    # log_server.run() should never return - it just listens on the socket
    # connection for logs to process forever.
    log_server.run(server, ProcessType.LOGS.value)


def run_mediator(conn:          multiprocessing.connection.Connection = None,
                 config_path:   Union[pathlib.Path, str] = None,
                 log_level:     Union[log.Level, int] = None,
                 shutdown_flag: multiprocessing.Event = None) -> None:
    '''
    Init and run client/engine IO mediator.
    '''
    _sigint_ignore()
    log_client.init("outdated mediator", log_level)

    if not conn:
        lumberjack = log.get_logger(ProcessType.MEDIATOR.value)
        raise log.exception(
            ConfigError,
            "Mediator requires a pipe connection; received None.",
            veredi_logger=lumberjack)
    if not config_path:
        lumberjack = log.get_logger(ProcessType.MEDIATOR.value)
        raise log.exception(
            ConfigError,
            "Mediator requires a config file; received no path to one.",
            veredi_logger=lumberjack)
    if not log_level:
        lumberjack = log.get_logger(ProcessType.MEDIATOR.value)
        raise log.exception(
            ConfigError,
            "Mediator requires a default log level (int); received None.",
            veredi_logger=lumberjack)

    log.get_logger(ProcessType.MEDIATOR.value).critical(
        "todo... server/mediator")
    # mediator = Mediator(config, conn)


def run_engine(conn:          multiprocessing.connection.Connection = None,
               config_path:   Union[pathlib.Path, str] = None,
               game_data:     Mapping[str, str] = None,
               log_level:     Union[log.Level, int] = None,
               shutdown_flag: multiprocessing.Event = None) -> None:
    '''
    Init engine. Starts engine. Runs engine...
    '''
    _sigint_ignore()
    log_client.init("outdated engine", log_level)
    lumberjack = log.get_logger(ProcessType.ENGINE.value)

    if not conn:
        raise log.exception(
            ConfigError,
            "Engine requires a pipe connection; received None.",
            veredi_logger=lumberjack)
    if not config_path:
        raise log.exception(
            ConfigError,
            "Engine requires a config file; received no path to one.",
            veredi_logger=lumberjack)
    if not log_level:
        raise log.exception(
            ConfigError,
            "Engine requires a default log level (int); received None.",
            veredi_logger=lumberjack)

    # Make our config object...
    config = Configuration(config_path=config_path)

    # TODO [2020-07-19]: Better game_data fields? A context or something
    # engine can use.
    owner = game_data.get('owner', None)
    campaign = game_data.get('campaign', None)
    debug_list = game_data.get('debug', [])
    debug_flags = None
    for each in debug_list:
        # Create or add to debug_flags
        if not debug_flags:
            debug_flags = DebugFlag[each.upper()]
        else:
            debug_flags |= DebugFlag[each.upper()]

    log.info(
        "Game engine starting with: debug: {}, meta: {}",
        debug_flags, game_data,
        veredi_logger=lumberjack)

    # The engine will create the ECS managers and required ECS systems.
    engine = Engine(owner, campaign, config,
                    debug=debug_flags)

    # Do each stage of engine's life.
    cycle = EngineTickCycle.START
    log.info("Game engine running {}...", cycle,
             veredi_logger=lumberjack)
    engine.run(cycle)
    log.info("Game engine finished {}.", cycle,
             veredi_logger=lumberjack)

    # We should be stuck in this one for a good while...
    cycle = EngineTickCycle.RUN
    log.info("Game engine running {}...", cycle,
             veredi_logger=lumberjack)
    engine.run(cycle)
    log.info("Game engine finished {}.", cycle,
             veredi_logger=lumberjack)

    # And finally on to a structured shut-down when the engine decides it's
    # done running.
    cycle = EngineTickCycle.STOP
    log.info("Game engine running {}...", cycle,
             veredi_logger=lumberjack)
    engine.run(cycle)
    log.info("Game engine finished {}.", cycle,
             veredi_logger=lumberjack)


# -----------------------------------------------------------------------------
# Wait Idle Loop...
# -----------------------------------------------------------------------------

def _game_running(
        processes: Mapping[str, multiprocessing.Process]) -> bool:
    '''
    Checks to see if game_end flag has been set.

    Returns /not/ game_end. That is, returns 'game_is_running' instead of
    `game_end` by inverting `game_end`.
    '''
    return not processes.game_end.wait(timeout=WAIT_SLEEP_TIME_SEC)


def _game_over(
        processes: Mapping[str, multiprocessing.Process]) -> bool:
    '''
    Sets the game_end flag. Engine and Mediator should notice and go into
    graceful shutdown.
    '''
    lumberjack = log.get_logger(ProcessType.MAIN.value)

    # Set the game_end flag. They should notice soon and start doing
    # their shutdown.
    log.info("Asking engine/mediator to end the game gracefully...",
             veredi_logger=lumberjack)
    processes.game_end.set()

    # Wait on engine and mediator processes to be done.
    # Wait on mediator first, since I think it'll take less long?
    log.info("Waiting for mediator to complete structured shutdown...",
             veredi_logger=lumberjack)
    processes.proc[ProcessType.MEDIATOR].join(GRACEFUL_SHUTDOWN_TIME_SEC)
    if processes.proc[ProcessType.MEDIATOR].exitcode is None:
        log.error("Mediator did not shut down in time. Data may be lost...",
                  veredi_logger=lumberjack)
    else:
        log.info("Mediator shut down complete.",
                 veredi_logger=lumberjack)

    # Now wait on the engine.
    log.info("Waiting for engine to complete structured shutdown...",
             veredi_logger=lumberjack)
    processes.proc[ProcessType.ENGINE].join(GRACEFUL_SHUTDOWN_TIME_SEC)
    if processes.proc[ProcessType.ENGINE].exitcode is None:
        log.error("Engine did not shut down in time. Data may be lost...",
                  veredi_logger=lumberjack)
    else:
        log.info("Engine shut down complete.",
                 veredi_logger=lumberjack)


def _logs_over(
        processes: Mapping[str, multiprocessing.Process]) -> bool:
    '''
    Sets the logs_end flag. Logs server should notice and gracefully shut down.
    '''
    lumberjack = log.get_logger(ProcessType.MAIN.value)

    # Set the game_end flag. They should notice soon and start doing
    # their shutdown.
    log.info("Asking logs server to end gracefully...",
             veredi_logger=lumberjack)
    processes.logs_end.set()

    # Wait on engine and mediator processes to be done.
    # Wait on mediator first, since I think it'll take less long?
    log.info("Waiting for logs server to complete structured shutdown...",
             veredi_logger=lumberjack)
    processes.proc[ProcessType.LOGS].join(GRACEFUL_SHUTDOWN_TIME_SEC)
    if processes.proc[ProcessType.LOGS].exitcode is None:
        log.error("Logs server did not shut down in time. "
                  "Logs may be lost? IDK...",
                  veredi_logger=lumberjack)
    else:
        log.info("Logs server shut down complete.",
                 veredi_logger=lumberjack)


def wait(processes: Mapping[str, multiprocessing.Process]) -> None:
    '''
    Waits forever. Kills server on Ctrl-C/SIGINT.

    Returns 0 if all exitcodes are 0.
    Returns None or some int if all exitcodes are not 0.
    '''
    lumberjack = log.get_logger(ProcessType.MAIN.value)
    log.info("Waiting for game to finish...",
             veredi_logger=lumberjack)

    try:
        game_running = _game_running(processes)
        while game_running:
            # Do nothing and take namps forever until SIGINT received or game
            # finished.
            game_running = _game_running(processes)

    except KeyboardInterrupt:
        # First, ask for a gentle, graceful shutdown...
        log.warning("Received SIGINT.",
                    veredi_logger=lumberjack)

    # Finally, end the game.
    _game_over(processes)
    _logs_over(processes)

    # Give up and ask for the terminator... If necessary.
    for each in processes.proc:
        if processes.proc[each].exitcode is None:
            # Still not exited; terminate them.
            processes.proc[each].terminate()

    # Figure out our exitcode return value.
    time.sleep(0.1)  # Short nap for our kids to clean up...
    retval = 0
    for each in processes.proc:
        exited = processes.proc[each].exitcode
        if exited is None:
            # Might have to print instead of log this?
            log.warning(
                "Process '{}' is still running slightly after termination...",
                each.value,
                veredi_logger=lumberjack)

            retval = None
        elif exited == 0:
            # Do nothing; only get a retval exit code of 0 if all of them
            # hit this case and do nothing and leave it at its original 0.
            pass
        elif retval is not None:
            # Don't override 'None'... that indicates someone's still alive and
            # kicking...
            retval = exited

    return retval


# -----------------------------------Veredi------------------------------------
# --                            See Veredi play.                             --
# -----------------------------Run, Veredi, run!-------------------------------

def make_parser() -> argparse.ArgumentParser:
    '''
    The argv parser for this module.
    '''
    DESCRIPTION = ("Run a game of veredi with a server to talk to users and "
                   "a logs server, each in their own process.")
    parser = argparse.ArgumentParser(description=DESCRIPTION)
    parser.add_argument('--verbose', '-v',
                        action='count',
                        default=2,
                        help=("Logging Verbosity Level. Use multiple times "
                              "for more verbose, e.g. '-vv'."))

    parser.add_argument('--owner', '-o',
                        required=True,
                        type=str,
                        help=("Owner ID/key for game."))

    parser.add_argument('--campaign', '-c',
                        required=True,
                        type=str,
                        help=("Campaign name/key for game."))

    parser.add_argument('config',
                        type=pathlib.Path,
                        help=("Logging Verbosity Level. Use multiple times "
                              "for more verbose, e.g. '-vv'."))
    return parser


def get_log_level(args: argparse.Namespace) -> log.Level:
    '''
    Convert log verbosity arg into log level.
    '''
    # High 'verbose' == more logs.
    # Low 'verbose'  == less logs.
    # ...which is the opposite of python's logging levels, so... translation.
    log_level = None
    if args.verbose >= 5:
        log_level = log.Level.DEBUG
    elif args.verbose == 4:
        log_level = log.Level.INFO
    elif args.verbose == 3:
        log_level = log.Level.WARNING
    elif args.verbose == 2:
        log_level = log.Level.ERROR
    elif args.verbose <= 1:
        log_level = log.Level.CRITICAL

    return log_level


def get_game_data(args: argparse.Namespace) -> Mapping[str, str]:
    '''
    Converts args into game data mapping.
    '''
    data = {}

    # Required fields:
    data['owner'] = args.owner
    data['campaign'] = args.campaign
    if not data or not data['owner'] or not data['campaign']:
        raise ValueError(
            "Missing required input fields: "
            f"owner: '{data['owner']}', campaign: '{data['campaign']}'",
            data)

    return data


def get_config_path(args: argparse.Namespace) -> pathlib.Path:
    '''
    Shouldn't need to convert or anything? Just check if file exists.
    '''
    config_path = args.config
    if not config_path or not config_path.is_file():
        raise FileNotFoundError(
            "No config path supplied, or config path doesn't point to a "
            f"file: '{str(config_path)}' "
            f"{'(file does not exist)' if config_path else ''} "
            f"{str(config_path.resolve()) if config_path else ''}",
            config_path)

    return config_path


def run() -> None:
    '''
    Run a game of veredi with a server to talk to users and a logs server, each
    in their own process.
    '''
    # Argparse Stuff.
    parser = make_parser()
    args = parser.parse_args()

    # Parse the args...
    log_level = get_log_level(args)
    game_data = get_game_data(args)
    config_path = get_config_path(args)

    # Init our processes... Receive a Processes NamedTuple for the rest
    # of the steps.
    processes = init(config_path,
                     game_data,
                     log_level)

    # Start them running.
    start(processes)

    # Go into our own infinite loop of waiting...
    exit_value = wait(processes)
    # ...and then exit with however well the end of the waiting went.
    exit(exit_value)


if __name__ == '__main__':
    run()


# Run like:
#   doc-veredi python -m veredi.veredi -o hi -c hi veredi/zest/zata/functional/config/config.veredi.yaml
