# log helper for l6sk's own development.
# since l6sk project itself is about creating a logging system, we dont really want to make it rely on some other
# sophisticated logging mechanism for its own development.
# For this reason l6sk's own logs just go to stdout. No need to collect max info and put it somewhere possibly
# across the network and then do SQL and FTS on it. These things are basicaully l6sk is being created for.
#
# This file just contains some helpers to print things with style and verbosity and allow controlling them
# from in one place.



import os
import time

from dataclasses import dataclass
import multiprocessing
import threading

import inspect
# import traceback

# ======================================================================================================================
# ======================================================================================================================
# ============================================================================================================ Constants

_ANSI_RED = "\u001b[31m"
_ANSI_GREEN = "\u001b[32m"
_ANSI_YELLOW = "\u001b[33m"
_ANSI_BLUE = "\u001b[34m"
_ANSI_MAGENTA = "\u001b[35m"
_ANSI_CYAN = "\u001b[36m"
_ANSI_RESET = "\u001b[0m"

_LOG_LEVELS = {
    "DBUG",
    "INFO",
    "WARN",
    "ERRR",
    "CRIT",
}


# ======================================================================================================================
# ======================================================================================================================
# =========================================================================================================== Log Record
@dataclass(frozen=False)
class LOG_RECORD:

    # timestamp
    ts: float

    # level of this msg. "DBUG", "INFO", ...
    lvl: str

    # the log msg itself.
    log_msg: str

    # caller info, file name, line number and function name, process name, pid, thread name, tid, ...
    filename: str = None
    lineno: str = None
    funcname: str = None
    pname: str = None
    pid: str = None
    tname: str = None
    tid: str = None

    def __post_init__(self):
        assert self.lvl in _LOG_LEVELS, f"unknown log level: {self.lvl}"


def _mk_lgr(msg_lvl, log_msg) -> LOG_RECORD:
    """ Generate a complete log record. This function should be called immediately after a log msg was called on
    mnlogger. (i.e. after a log.dbg(), log.info(), log.warn() call took place). This is because this function
    will look up the call stack to try and locate the stack frame of the function that issued the log call. """

    # inspect docs: https://docs.python.org/3/library/inspect.html
    # inspect.stack() returns a list of FrameInfo Objects, the first one (idx==0) belongs to this function itself
    # _mk_lgr -> idx_0                      (this func)
    # {dbg,info,warn,...} -> idx_1          (this func caller)
    # lg36 user -> idx_2
    tmp_inspect_res = inspect.stack()
    caller_frame_info = tmp_inspect_res[2]

    lgr = LOG_RECORD(ts=time.time(), lvl=msg_lvl, log_msg=log_msg)

    lgr.filename = caller_frame_info.filename
    lgr.lineno = str(caller_frame_info.lineno)
    lgr.funcname = caller_frame_info.function
    # lgr.funcname = inspect.currentframe().f_back.f_back.f_code.co_name

    # this is always going to the one line of code that looks like log.dbg('...')
    # caller_code_cntxt = caller_frame_info.code_context

    cp = multiprocessing.current_process()
    ct = threading.current_thread()

    lgr.pname = cp.name
    lgr.pid = str(cp.pid)
    lgr.tname = ct.name
    lgr.tid = str(ct.ident)

    return lgr


# ======================================================================================================================
# ======================================================================================================================
# =================================================================================================== Filtering decision

def should_filter_lgr(lgr: LOG_RECORD) -> bool:
    """ Return True if log record should be ignored. False to process it.
    This function is the central place within log_util module to make filtering decision.

    Here you have a compelete log record w/ all available information. Feel free to modify this function to:
        - increase/decrease verbosity
        - filter based on levels (dbg, info, warn, ...)
        - filter based on caller filename ...
    """

    # if lgr.lvl in {"DBUG"}:
    #    return True

    return False



# ======================================================================================================================
# ======================================================================================================================
# =============================================================================================================== Format
# all formatting logic should be here. lg36 will use this.
def _get_msg_fmt(lgr: LOG_RECORD) -> str:

    # --------------------------------- clean up filename (dont want full path)
    fbasename = os.path.basename(lgr.filename)

    # jupyter ntbk mess
    if 'ipython' in fbasename:
        fbasename = ""

    loc_in_code = f"{fbasename}:{lgr.lineno}"

    # ultra verbose
    # time_str = str(lgr.ts).ljust(18)  # at least 18 chars, does not shorten
    # msg_builder = f"{time_str}|{fbasename}:{lgr.lineno}"
    # msg_builder += f"|P:{lgr.pname}:{lgr.pid}|T:{lgr.tname}:{lgr.tid}|{lgr.log_msg}"

    # --------------------------------- everything else
    # ts_fmt = f"{lgr.ts:,.4f}"
    ts_fmt = f"{lgr.ts:.2f}"[5:]
    msg_builder = f"{ts_fmt}|{loc_in_code}|{lgr.log_msg}"

    # --------------------------------- handle level + color
    if lgr.lvl in {'DBUG'}:
        msg_builder = f'DBUG|{msg_builder}'
    if lgr.lvl in {'INFO'}:
        msg_builder = f'{_ANSI_GREEN}INFO|{msg_builder}{_ANSI_RESET}'
    if lgr.lvl in {'WARN'}:
        msg_builder = f'{_ANSI_BLUE}WARN|{msg_builder}{_ANSI_RESET}'
    if lgr.lvl in {'ERRR'}:
        msg_builder = f'{_ANSI_YELLOW}ERRR|{msg_builder}{_ANSI_RESET}'
    if lgr.lvl in {'CRIT'}:
        msg_builder = f'{_ANSI_RED}CRIT|{msg_builder}{_ANSI_RESET}'

    return f"{msg_builder}\n"


# ======================================================================================================================
# ======================================================================================================================
# ========================================================================================================= exported API


# def dbg(msg, *args):
def dbg(msg):

    lgr = _mk_lgr("DBUG", msg)
    if not should_filter_lgr(lgr):
        print(_get_msg_fmt(lgr), end="")


def info(msg):

    lgr = _mk_lgr("INFO", msg)
    if not should_filter_lgr(lgr):
        print(_get_msg_fmt(lgr), end="")


def warn(msg):

    lgr = _mk_lgr("WARN", msg)
    if not should_filter_lgr(lgr):
        print(_get_msg_fmt(lgr), end="")


def err(msg):

    lgr = _mk_lgr("ERRR", msg)
    if not should_filter_lgr(lgr):
        print(_get_msg_fmt(lgr), end="")


def crit(msg):

    lgr = _mk_lgr("CRIT", msg)
    if not should_filter_lgr(lgr):
        print(_get_msg_fmt(lgr), end="")


# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================
def main():
    dbg('hello')
    info('hello')
    warn('hello')
    err('hello')
    crit('hello')


if '__main__' == __name__:
    main()
