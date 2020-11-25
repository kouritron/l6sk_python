""" dao_sqlite.py
This module provides implementation of the l6sk Database Layer using a in-memory sqlite instance.
Everything is ephemeral here.
"""

import os
import sys
import time
import sqlite3
import errno
import threading

from l6sk.dbl.dbl_dispatch import DBL_REQ
from l6sk.dbl.dbl_api import DBL_API, DBL_FAIL_CAUSE

from l6sk.crypt_util import get_auth_kdf

from l6sk import knobman as km
from l6sk import log_util as log


class MemSqliteDAO:
    """ l6sk DAO interface backed by in-mem sqlite3. """

    def __init__(self):
        super().__init__()

        log.info("Initializing memory sqlite DAO ...")

        # MemSqliteDAO means database is in memory and in process.
        # this makes memory based look aside buffers, and connection pooling, reconnecting meaningless.
        # This DAO supports none of them.

        # This is the memory dao. so ":memory:" shouldnt be a parameter.
        # isolation_level=None means autocommit. Absolutely no desire to have some library code insert "BEGIN"
        # before our queries if we didnt ask for it.
        self._db_conn = sqlite3.connect(":memory:", isolation_level=None)

        log.dbg("MemSqliteDAO is initialized.")

    # ==================================================================================================================
    # ==================================================================================================================
    # ========================================================================================== top level request entry
    def serve_req(self, req: DBL_REQ):
        """ Serve the DB request contained in req, and set the result or cause of failure on it when done. """

        # TODO: if we are doing, asyncio.Event to wake up on the result, then this function may have to tell
        # the tornado main loop to do a event.set() on the main thread for us. instead of directly doing it here,
        # we would pass a one liner lambda to the main loop to invoke it in the next cycle.

        # NOTE: reminder that if either one of <req.fail_cause, req.succ_data> is not None, req to be treated as done.

        try:
            result = self._decode_and_exec_req(req)
            req.succ_data = result
            # TODO maybe:
            # "... mainthread.schedule_soon ..."(lambda: event.set())
            # Done, could return here.
        # maybe extra except clauses to catch specific errors and set corresponding msgs and http codes.
        except Exception as ex:
            req.fail_cause = DBL_FAIL_CAUSE(http_err_code=500,
                                            user_msg='Internal Server Error',
                                            dbg_info_string=str(ex))

    def _decode_and_exec_req(self, req: DBL_REQ):

        # request args: <req.op, req.data>
        # result: <req.fail_cause, req.succ_data> if either is not None, request is to be treated as finished

        if req.op in {DBL_API.HEALTH_CHK_1}:
            return self.health_check_v1()

        if req.op in {DBL_API.HEALTH_CHK_2}:
            return self.health_check_v2()

        if req.op in {DBL_API.HEALTH_CHK_3}:
            return self.health_check_v3()

    # ==================================================================================================================
    # ==================================================================================================================
    # ==================================================================================================================


    # ==================================================================================================================
    # ==================================================================================================================
    # ============================================================================================ Health Check Services
    # Various health checks exist, because they have varying degrees of how deep they go for a healthcheck.
    # the most basic one is just a test for reaching the DAO from the client/process management tools/web layer.
    def health_check_v1(self) -> str:
        """ Return a non empty string indicating healthy communication to the DAO. """

        return "DBL health check: OK"

    def health_check_v2(self):
        pass

    def health_check_v3(self):
        pass


# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================
def main():
    pass


if '__main__' == __name__:
    main()
