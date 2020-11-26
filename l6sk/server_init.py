#!/usr/bin/env python3
"""
Init system for l6sk. This module configures and manages the lifecycle for various subsystem to start an instance
of l6sk.
Its responsible for doing things like build out a particular DBL, a particular logger, ...
and then start the web server.

"""

import os
import threading
from pathlib import Path
import json
import shutil

import tornado.web
import tornado.options as topts
# topts.define >>> to define new options
# topts.parse_command_line  >>> to parse argv
# topts.parse_config_file   >>> to parse a "server.conf" file
# topts.options             >>> Get the options from here

import l6sk.knobman as km
import l6sk.log_util as log

from l6sk.dbl.dao_sqlite_mem import MemSqliteDAO
from l6sk.dbl.dbl_dispatch import DBL_REQUEST_DISPATCH, dbl_service_thread_entry
from l6sk.l6sk_contract import L6SK_ROUTES
from l6sk import crypt_util

# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================
def webapp_init():

    print(f"Starting l6sk web server ... pid: {os.getpid()}")

    # ******************** init knobman and start using log
    km.init_knob_man()
    log.info("knobman initialized.")
    log.dbg(f"knobman debug dump: {km.get_dbg_dump()}")

    # ******************** trigger lazy initializers (optional)
    crypt_util.init_crypt_util()

    # ******************** Choose DAO
    log.info("Starting DB Layer using the sqlite3 DAO")

    # TODO: decide if DBL can just retrieve a default DAO.
    # I think since we may have multiple DAO implementations, it makes sense to not have a default.
    # although we could do it, and then choose the default by setting something in knobman.
    # dao_kwargs = {"db_filename": km.get_knob("DBL_SQLITE_DB_FILENAME")}
    # dao_maker_callable = lambda: MemSqliteDAO(**dao_kwargs)
    dao_maker_callable = lambda: MemSqliteDAO()

    # ******************** request dispatch
    dispatch = DBL_REQUEST_DISPATCH()

    # Create DBL worker thread. This is the "DBL service". And give it pointers to the dispatch queues.
    t = threading.Thread(target=dbl_service_thread_entry,
                         name="dbl_worker_thread",
                         args=(dao_maker_callable, dispatch))

    # NOTE This might be a bit unsettled. Currently I am daemonizing the DBL worker thread
    # which simply means if main thread is gone, no dbl is needed anymore. sounds right.
    # NOTE: What does this do to DAO's stdout and stderr ?? answer seems to be nothing special.
    # stdout and stderr are there and work as normal. however if only daemonic threads are left the process
    # will abruptly terminate and the last few print() calls may not get a chance to flush().
    t.setDaemon(True)
    t.start()

    # ******************** Tornado web server
    # Tornado ppl normally put these on top of the file, but since we have knobman and it solves many problems ...
    topts.define("port", default=km.get_knob('TORNADO__SERVER_PORT'), help="l6sk server port", type=int)
    topts.define("debug", default=km.get_knob('TORNADO__DEBUG_MODE'), help="run in debug mode")

    topts.parse_command_line()

    server_port = topts.options.port

    # --------- settings:
    tor_app_settings = {

        # This will serve static files from the given filesystem path for the URLs:
        # "/static/*", "/favicon.ico", "/robots.txt"
        # if you want to change these loot at: "static_url_prefix" setting
        'static_path': km.get_knob('PATHNAME__STATIC_DIR'),
        'template_path': km.get_knob('PATHNAME__TEMPLATES_DIR'),
        'xsrf_cookies': True,

        # debug=True implies autoreload=True
        'debug': topts.options.debug
    }

    log.info(f"Starting log socket server on: {server_port}")
    log.info(f"Options: \n{json.dumps(tor_app_settings, sort_keys=True, indent=4)}")

    app = tornado.web.Application(L6SK_ROUTES, **tor_app_settings)
    app.listen(server_port)
    tornado.ioloop.IOLoop.current().start()


# ======================================================================================================================
# ======================================================================================================================
if "__main__" == __name__:
    webapp_init()
