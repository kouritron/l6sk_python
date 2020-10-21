# -*- coding: utf-8 -*-
"""
Web App Init system. This module manages lifecycle, config knobs, and others for various subsystem.
Basically build out a particular DBL, a particular logger, and start the Web server.
"""

import os
from pathlib import Path
import shutil
import threading

from l6sk.dbl.dao_sqlite import DAO_SQLITE
from l6sk.dbl.dbl_dispatch import DBL_REQUEST_DISPATCH, dbl_service_thread_entry
from l6sk import knobman as km
from l6sk import lg36

# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================
def webapp_init():

    # start by reading in the knobs.
    print(f"webapp_init: starting litech4t web server ... pid: {os.getpid()}")
    km.init_knob_man()

    # ******************** Init logging
    # it should lazy init.
    lg36.info("lg36 should be good to go now.")
    lg36.dbg(f"Current knobs: {km.get_dbg_snapshot_as_json_string()}")

    # ******************** CHOOSE DAO
    lg36.info("Building out DBL Using the sqlite3 dao")

    dao_kwargs = {"db_filename": km.get_knob("DBL_SQLITE_DB_FILENAME")}
    dao_maker_callable = lambda: DAO_SQLITE(**dao_kwargs)

    # ******************** request dispatch
    dispatch = DBL_REQUEST_DISPATCH()

    # Create DBL worker thread. This is the "DBL service". And give it pointers to the dispatch queues.
    t = threading.Thread(target=dbl_service_thread_entry,
                         name=km.get_knob("DBL_WORKER_THREAD_NAME"),
                         args=(dao_maker_callable, dispatch))

    # TODO there is unresolved question here. I dont think DBL should be daemonized
    # t.setDaemon(True)
    t.start()


if "__main__" == __name__:
    webapp_init()
