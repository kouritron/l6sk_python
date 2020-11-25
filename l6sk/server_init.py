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
# ====================================================================================================== Tornado options
topts.define("port", default=1655, help="l6sk server port", type=int)
topts.define("debug", default=False, help="run in debug mode")


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
    dao_maker_callable = lambda: MemSqliteDAO()

    # ******************** request dispatch
    dispatch = DBL_REQUEST_DISPATCH()

    # Create DBL worker thread. This is the "DBL service". And give it pointers to the dispatch queues.
    t = threading.Thread(target=dbl_service_thread_entry,
                         name=km.get_knob("DBL_WORKER_THREAD_NAME"),
                         args=(dao_maker_callable, dispatch))

    # NOTE This might be a bit unsettled. Currently I am daemonizing the DBL worker thread
    # which simply means if main thread is gone, no dbl is needed anymore. sounds right.
    t.setDaemon(True)
    t.start()

    # ******************** Tornado web server
    topts.parse_command_line()

    # TODO move some of these over to knobman
    repo_root = (Path(__file__) / '..' / '..').resolve()
    static_path = str(repo_root / 'l6sk_webui' / 'static')
    template_path = str(repo_root / 'l6sk_webui' / 'templates')
    server_port = topts.options.port
    server_dbg_mode = topts.options.debug

    # --------- settings:
    tor_app_settings = {

        # This will serve static files from the given filesystem path for the URLs:
        # "/static/*", "/favicon.ico", "/robots.txt"
        # if you want to change these loot at: "static_url_prefix" setting
        'static_path': static_path,
        'template_path': template_path,
        'xsrf_cookies': True,

        # debug=True implies autoreload=True
        'debug': server_dbg_mode
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
