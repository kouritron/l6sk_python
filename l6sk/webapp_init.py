"""
Web App Init system. This module manages lifecycle, config knobs, and others for various subsystem.
Basically build out a particular DBL, a particular logger, and start the Web server.
"""

import os
import threading
from pathlib import Path
import shutil

from l6sk.dbl.dao_sqlite import DAO_SQLITE
from l6sk.dbl.dbl_dispatch import DBL_REQUEST_DISPATCH, dbl_service_thread_entry
from l6sk import knobman as km
from l6sk import log_util as log

# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================
def webapp_init():

    # start by reading in the knobs.
    print(f"Starting l6sk web server ... pid: {os.getpid()}\n\n")

    km.init_knob_man()
    log.info("knobman initialized.")
    log.dbg(f"Current knobs: {km.get_dbg_snapshot_as_json_string()}")

    # ******************** CHOOSE DAO
    log.info("Building out DBL Using the sqlite3 dao")

    dao_kwargs = {"db_filename": km.get_knob("DBL_SQLITE_DB_FILENAME")}
    dao_maker_callable = lambda: DAO_SQLITE(**dao_kwargs)

    # ******************** request dispatch
    dispatch = DBL_REQUEST_DISPATCH()

    # Create DBL worker thread. This is the "DBL service". And give it pointers to the dispatch queues.
    t = threading.Thread(target=dbl_service_thread_entry,
                         name=km.get_knob("DBL_WORKER_THREAD_NAME"),
                         args=(dao_maker_callable, dispatch))

    # TODO there is unresolved question here. Daemonizing DBL simply means if main thread is gone, no dbl is needed
    t.setDaemon(True)
    t.start()


if "__main__" == __name__:
    webapp_init()
