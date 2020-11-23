# knobs manager.
# put all the config options here.
# we r doing it as python file, as opposed to JSON, YAML, .env file, .....
# This has the advantage that you can generate some options programmatically if need be. For example by
# querying EC2 metadata endpoint and finding out which AZ you are in. Or generate random numbers, or find a path ...
# We could also section this file if we have dev/qa/prod params, ...

import os
import sys
import time
import json

from pathlib import Path

from dataclasses import dataclass
import shutil
import typing
import enum

# Dont import project level modules here. Idea is for knobman to control other files, not the other way around.

# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================
# ================================================================================================================ Knobs

_KNOBS = {

    # ------------------------------------------------------------------------------------------------------------------
    # -------------------------------------------------------------------------------------------------- General options
    # One of the benefits of .py knobs file vs JSON/YAML, is to figure out things at runtime.
    # knobman prefers strings, not other objects like Path. In general, strings are always preferred in knobman.
    "STATIC_DIR_PATHNAME": str((Path(__file__) / '..' / '..' / 'l6sk_webui' / 'static').resolve()),
    "TEMPLATES_DIR_PATHNAME": str((Path(__file__) / '..' / '..' / 'l6sk_webui' / 'templates').resolve()),

    # ------------------------------------------------------------------------------------------------------------------
    # ---------------------------------------------------------------------------------------------- Tornado app options
    # 'PORT': 6060,
    # Port and debug mode is handled by tornado cli option parsing. TODO find out what the listen host is
    # 'LISTEN_HOST': '127.0.0.1',

    # 'WSGI_SERVER': 'cheroot',

    # ------------------------------------------------------------------------------------------------------------------
    # --------------------------------------------------------------------------------------------------------- l6sk API
    # If you need to "sleep wait" inside request handlers (possibly waiting for DBL results) use this.
    # but we found much better solutions than sleep waiting for DBL operations.
    # "L6SK_API__SLEEP_WAIT_TIMEOUT": 0.01,

    # ------------------------------------------------------------------------------------------------------------------
    # ----------------------------------------------------------------------------------------- Crypt Util (system wide)
    # 18 bytes == 144 bits (2 to the -144 is as collision safe as any other space)
    # 18, 21, 24, ... aligns nicely with b64 so no trailing '=' is needed.
    # choose between 8 and 64. (8 bytes == 64 bits  --  64 bytes == 512 bits)
    "CU__UUID_LEN": 18,

    # ------------------------------------------------------------------------------------------------------------------
    # -------------------------------------------------------------------------------------- Crypt Util (AUTH Subsystem)
    # There might be more than 1 KDF later. These are options for the "auth kdf"

    # diff salts for diff subsystem is prudent. Helps avoid sharing secrets between subsystems even
    # if they are seeded from one secret. ie server might encrypt and/or sign client side cookies.
    # It might have an API for challenge/response for something.
    # If you have a generic script that injects just one secret into an env var at runtime (ie session_secret, ...),
    # and dont want to constantly update that script, you could salt it for different subsystems.
    "CU_AUTH_KDF__SALT": b'b261ef47_l6sk_auth_1ea8f2ac',

    # kdf method. one of "scrypt_then_pbkdf2_hmac", "pbkdf2_hmac", "scrypt"
    # scrypt_then_pbkdf2_hmac (with 16 MB mem) and 40k rounds of pbkdf2 takes about 80 milliseconds, on 4GHz zen+
    "CU_AUTH_KDF__METHOD": 'scrypt_then_pbkdf2_hmac',

    # scrypt params, generally must be powers of two.
    # N is work factor, R is block size
    # memory usage: 128 * r * N >>>>>>> here we get 128 * 8 * 16 * 1024 = 16 MB
    "CU_AUTH_KDF__SCRYPT_N": 16 * 1024,
    "CU_AUTH_KDF__SCRYPT_R": 8,

    # pbkdf2 params. if pbkdf2 is all you have, good idea to set this 100k+
    # of course users can just use a bit more than 8-10 chars and this wont be important.
    "CU_AUTH_KDF__PBKDF2_HMAC_ITERATIONS": 40 * 1000,

    # derived key len for auth kdf.
    "CU_AUTH_KDF__DKLEN": 18,

    # ------------------------------------------------------------------------------------------------------------------
    # ------------------------------------------------------------------------------------------------------------- Misc
    # thread name is useful for debugging.
    "DBL_WORKER_THREAD_NAME": "dbl_worker_thread",

    # sleep wait timeout for the DBL worker thread, in seconds i.e. 0.01 equals 10 milli seconds.
    # The idea is that DBL worker will sleep this much, if it hasnt seen a request in a while, instead of
    # of busy waiting/angrily checking the queue for the next req constantly.
    # This is not related to API handlers waiting for DBL results. That problem has better solutions than sleep wait.
    "DBL_WORKER_THREAD_SLEEP_WAIT_TIMEOUT": 0.01,

    # dbl dipatcher will not sleep between requests, unless this many attempts face empty queues. In that case
    # it will start sleep waiting for the next request until there is a new request which will reset counter to 0.
    "DBL_DISPATCH_IDLE_COUNTER_THRESHOLD": 10,

    # ------------------------------------------------------------------------------------------------------------------
    # --------------------------------------------------------------------------------------------------- Service Limits
    # various subsystems may read these limits and refuse service beyond them.
    # for example the limits on user name length could be used by the web layer to reject names that are too long
    # or too short. These can also be used by the DB Layer in case the DB wants to assert such things also.
    # (possibly assert name len twice, in web layer, and db layer)
    # These knobs could also be published for outside world. not just used internally.
    "SL__USER_NAME_LEN_MIN": 2,
    "SL__USER_NAME_LEN_MAX": 96,
    "SL__USER_NAME_LEGAL_CHARS": "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz1234567890_",
    "SL__USER_NAME_LEGAL_CHARS_START": "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz",

    # LGRP = Log Group
    # Each log group is probably:
    #   - A separate sqlite memory db, in case of sqlite memory DAO
    #   - A separate sqlite disk file, in case of sqlite disk DAO
    #   - A separate schema, in case of postgres DAO
    #   - A separate Database, in case of mysql/mariadb DAO
    # PG/Mariadb will probably take issue with db/schema names that are too long (i think upto 63 should be fine)
    # unless you are ok with the overhead of an extra translation table somewhere, you might want to keep
    # these lengths low, and with a restricted charset
    "SL__LGRP_NAME_LEN_MIN": 2,
    "SL__LGRP_NAME_LEN_MAX": 48,
    "SL__LGRP_NAME_LEGAL_CHARS": "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz1234567890_",
    "SL__LGRP_NAME_LEGAL_CHARS_START": "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz",
}

# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================= Optional Knobs
# dict_a.update(dict_b) unions dicts. Duplicate keys will resolve in favor of the update argument.

# ******************** On disk sqlite DAO
# _KNOBS.update({
#     # drop old files/tables on each run
#     "SQLITE_FS_DAO__START_CLEAN": True,

#     # Sqlite db file. must be str. In general you better have good reason to put non-str objects in knobman
#     # keep it in a dedicated parent folder, which will be dropped in case of clean start
#     "SQLITE_FS_DAO__DB_FILENAME": str((Path(__file__) / '..' / '..' / 'ignored_data' / 'DBL' / 'l6sk.db').resolve()),

#     # synchronous off means we are good with a write() once its passed to the OS.
#     # unlike PG, this isnt just a dataloss risk, turning this off does carry some risk of data/db_file corruption.
#     "SQLITE_FS_DAO__PRAGMAS": [
#         "PRAGMA synchronous = OFF",
#     ],
# })

# ******************** MEMORY sqlite DAO
# _KNOBS.update({
#     # TODO fill in.
#     "SQLITE_MEM_DAO__XXXX": "YYYYYYYYY",
# })

# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================
# ================================================================================ Knobman API + the necessary lazy init
_KNOBMAN_INITIALIZED = False


def init_knob_man():

    print(f"knob man init called. Time now: {time.time():,.4f}")
    # if there is something than needs compute at init time, but not import time, do it here.

    # ******************** Sqlite disk DAO, if exists.
    # deal w/ sqlite db directory and clean start flags.
    sqlite_fs_dao_db_file = _KNOBS.get('SQLITE_FS_DAO__DB_FILENAME')

    if sqlite_fs_dao_db_file:
        db_file_parent_dir = str((Path(sqlite_fs_dao_db_file) / '..').resolve())

        # make sqlite db dir if not exists:
        Path(db_file_parent_dir).mkdir(parents=True, exist_ok=True)

        # drop db file, if it exists.
        if _KNOBS["SQLITE_FS_DAO__START_CLEAN"]:
            if (":memory:" != sqlite_fs_dao_db_file) and os.path.exists(sqlite_fs_dao_db_file):
                try:
                    os.remove(sqlite_fs_dao_db_file)
                except Exception as ex:
                    print(f"Exception while trying to reset sqlite db file: {ex}")

    # ******************** Next

    # ******************** dont come bacck here again.
    print(f"knob man init complete. Time now: {time.time():,.4f}")
    global _KNOBMAN_INITIALIZED
    _KNOBMAN_INITIALIZED = True


def get_knob(kkey: str):
    """ Return the value associated with the knob with the given knob key.
    knob key must be str, that will be converted to ALL CAPS, if not already.
    The knob key is always string. The value may be any object.
    None, if key is not found. """

    if not _KNOBMAN_INITIALIZED:
        init_knob_man()

    kkey = kkey.upper()

    # TODO correct behavior is None if not found. lots of ugly try excepts otherwise.
    # but if you want to be alerted during dev if some typo shows up or what not. soln is print warning.
    return _KNOBS.get(kkey)


# this is useful at least in testing.
def set_knob(kkey: str, kval):

    if not _KNOBMAN_INITIALIZED:
        init_knob_man()

    _KNOBS[kkey] = kval


# This shouldnt exist really even for testing. Components need to be testable on their own.
# def update_knobs(new_knobs: dict):
#     """ Given a knobs dict (or partial knobs dict), update current knobs. Conflict to be
#     resolved in favor of the incoming dict. """

#     if not _KNOBMAN_INITIALIZED:
#         init_knob_man()

#     _KNOBS.update(new_knobs)


# this for dbg info.
def get_dbg_snapshot_as_json_string() -> str:
    """ Try to turn current KNOBS into a JSON string and return this string. Not a reliable
    serializer/deserializer. Might lose info during this process. """

    # with default lambda trick, i dont think exception can occur actually anymore.
    result = json.dumps(_KNOBS, sort_keys=True, indent=4, default=lambda x: str(x))

    return result
