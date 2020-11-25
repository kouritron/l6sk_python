""" dao_sqlite.py
This module provides a sqlite3 based implementation of the l6sk Database layer.
"""

import os
import sys
import time
import sqlite3
import errno
import threading

from l6sk.dbl.dbl_dispatch import DBL_REQ
from l6sk.dbl.dbl_api import DBL_API

from l6sk.crypt_util import get_auth_kdf

from l6sk import knobman as km
from l6sk import log_util as log


class DAO_SQLITE:
    """ Sqlite implementation of the l6sk DAO interface. """

    # This class should take its knobs as constructor args for consistency and ease of testing.
    # if knobman is used it should be in some sort of module level lazy init function. Not inside this class.
    def __init__(self, db_filename: str):
        super().__init__()

        log.info("Initializing sqlite DAO")

        # We dont open db conn here. DAO interfaces with dbl dispatch and takes dao requests from there.
        # DAO is responsible for conn pooling (if any), conn life cycle, and at least a tiny bit of retrying.
        # Especially for network errors and such, for which it is definitely the correct layer. (remember MOS Book)
        # DAO also is responsible for lookaside buffers. There might be two DAOs implementing mysql using
        # different connectors, look asides, ....

        # A file on disk, managed by knobman. memory probably wouldnt work for too long  w/ reconnect and
        # lifecycle management. Altho its probably fine for long enof to use for dev.
        self._db_filename = db_filename

        # In an old version of this we tried to assert that connection can be opened here even tho we dont want to
        # open just yet. And if fails refuse to init. This is bad idea. You dont want to be that hard to init.
        # dont reach for os._exit() every time there is a network error.

        # conn management bits and buffers.
        self._curr_conn = None

        log.dbg("Sqlite DAO init complete.")

    # ==================================================================================================================
    # ================================================================================================ DB Conn lifecycle
    # ==================================================================================================================
    def _db_reconnect(self):
        """ DB reconnect does two things:
        - close current db connection, if one exists, if possible.
        - create new one, if possible.

        This method should be safe to call in case you face conn related errors and you want to do a retry.
        """

        # close current one if possible, close() can be called as many times as you want on a db conn.
        if self._curr_conn:
            try:
                self._curr_conn.close()
            except Exception as ex:
                log.warn(f"Failed to close db connection. Exception: {ex}")

        # sleep by reconnect delay, if any.
        recon_delay = km.get_knob("DAO_SQLITE_RECONNECT_DELAY")
        if recon_delay:
            log.info(f"Sleeping {recon_delay} seconds before reconnecting to db.")
            time.sleep(recon_delay)

        # create new one, if possible
        try:
            # Defend autocommit at all cost. If you want xaction, issue BEGIN.
            self._curr_conn = sqlite3.connect(self._db_filename, isolation_level=None)
        except Exception as ex:
            # Not critical because we might retry, and it might work next time. I think its not even error
            # because it may be un-related to web app. It might be network or db server related (not for sqlite
            # but in general). warn is reasonable.
            log.warn(f"Failed to open db connection. Exception: {ex}")

    def _get_db_connection(self):

        # If not exists create it.
        if not self._curr_conn:
            self._db_reconnect()

        return self._curr_conn

    # ==================================================================================================================
    # ========================================================================================== top level request entry
    # ==================================================================================================================
    def process_req(self, req: DBL_REQ):
        """ Process the DB request contained in req, and set the result or cause of failure on it also. """

        try:
            result = dao.prcoess_req(next_req)
            next_req.succ_data = result
            # Done, could return here.
        # maybe extra except clauses to catch specific errors and set corresponding msgs and http codes.
        except Exception as ex:
            next_req.fail_cause = DBL_REQ_FAIL_CAUSE(http_err_code=500,
                                                     user_msg='Internal Server Error',
                                                     dbg_data=str(ex))

    def _process_req(self, req: DBL_REQ):

        # request args: <req.op, req.data>
        # result: <req.fail_cause, req.succ_data> if either is not None, request is to be treated as finished

        if req.op in {DBL_API.HEALTH_CHK_1}:
            pass
        elif req.op in {DBL_API.HEALTH_CHK_2}:
            pass
        elif req.op in {DBL_API.HEALTH_CHK_3}:
            pass

    # ==================================================================================================================
    # =============================================================================================== API: Health Checks
    # ==================================================================================================================
    def health_check_v1(self):
        pass

    def health_check_v2(self):
        pass

    def health_check_v3(self):
        pass

    # ==================================================================================================================
    # ==================================================================================== API: GET_USERS (TODO replace)
    # ==================================================================================================================
    def _get_users_list(self):

        cursor = self._get_db_connection().cursor()

        cursor.execute('SELECT uid, u_name FROM User')

        # rows is a list of tuples
        rows = cursor.fetchall()

        result_dict = {}
        result_dict['fields'] = ['uid', 'user name']
        result_dict['users'] = rows

        return result_dict

    def get_users_list(self):

        # if it works, return, all good.
        try:
            return self._get_users_list()
        except Exception as ex:
            log.warn(f"sqlite dao operation caught exception: {ex}")

        # if anything, there is a retry delay here not reconnect delay here
        self._db_reconnect()

        # work or not we are done this time. one retry is all you get.
        try:
            return self._get_users_list()
        except Exception as ex:
            log.warn(f"sqlite dao operation caught exception: {ex}")

    # ---------------------------------------------------

    # TODO the funct mapping between enum GET USER and the DAO method, should do this retry
    # and store result in the req object, or cause of failure.
    #def process_req(self, req):
    #if "GET_USERS" == req:

    # ------------------------------------------------------------------------------------------------------------------
    # ---------------------------------------------------------------------------------------------- user authentication

    def authenticate_user(self, user, password):

        # print( "----------------------------------------------------------"
        # print( "supplied user: " + str(user)
        # print( "supplied pass: " + str(password)

        user_result = {}
        server_result = {}

        current_db_connection = self._get_db_connection()
        cursor = current_db_connection.cursor()

        cursor.execute('SELECT uid, u_name, first_name, last_name, email, pass_hash from User where u_name=?;',
                       (user, ))

        rows = cursor.fetchall()

        # commit the transaction
        current_db_connection.commit()

        if len(rows) >= 1:
            # user was valid. rows[0] is a tuple
            # print( rows[0])
            if get_auth_kdf().get_pw_shadow_b64(password) == rows[0][5]:
                user_result['op_failed'] = False
                server_result['uid'] = rows[0][0]
                server_result['u_name'] = rows[0][1]
                server_result['first_name'] = rows[0][2]
                server_result['last_name'] = rows[0][3]
                server_result['email'] = rows[0][4]
            else:
                user_result['op_failed'] = True
                user_result['op_failed_desc'] = "wrong password."
                user_result['invalid_pass'] = True

        else:
            user_result['op_failed'] = True
            user_result['op_failed_desc'] = "no such user found."
            user_result['invalid_user'] = True

        return user_result, server_result

    # ------------------------------------------------------------------------------------------------------------------
    # ------------------------------------------------------------------------------------------------------------------
    # ------------------------------------------------------------------------------------------------------------------
    # ------------------------------------------------------------------------------------------------------------------
    # -------------------------------------------------------------------------------------------------- private methods


# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================
def main():
    pass

if '__main__' == __name__:
    main()
