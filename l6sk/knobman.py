# knobs manager.
# put all the config options here.
# we r doing it as python file, as opposed to JSON, or dev.env prod.env, .....
# This has the advantage that you can generate some options programmatically if need be. For example by
# querying EC2 metadata endpoint and finding out which AZ you are in. Or generate random numbers ....

# Dont import anything outside stdlib here.

import os
import sys
import time
import json
import shutil

from dataclasses import dataclass
import typing

from pathlib import Path
import enum

# ======================================================================================================================
# ======================================================================================================================
# ==================================================================================================== GLOBAL KNOBS DICT
# this will be a lazy init singleton. All the knobs will be stored here eventually possbily after getting constructed
# inside that lazy init. The lazy init could also be called explicitely. work with users who dont init, if they do,
# let them control when it happens.
_KNOBMAN_INITIALIZED = False
_KNOBS = {}

# ======================================================================================================================
# ======================================================================================================================
# ============================================================================================================ DBL Knobs
# Two dicts can be unioned with dict_a.update(dict_b). duplicate keys will resolve in favor of the update argument.

_KNOBS.update({

    # ******************** BASIC DBL options
    # thread name is useful for debugging.
    "DBL_WORKER_THREAD_NAME": "dbl_worker_thread",

    # sleep wait timeout for the DBL worker thread, in seconds i.e. 0.01 equals 10 milli seconds.
    # This value might not be the same as the timeout for request handlers waiting for DBL results.
    "DBL_WORKER_THREAD_SLEEP_WAIT_TIMEOUT": 0.01,

    # dbl dipatcher will not sleep between requests, unless this many attempts face empty queues. In that case
    # it will start sleep waiting for the next request until there is a new request which will reset counter to 0.
    "DBL_DISPATCH_IDLE_COUNTER_THRESHOLD": 10,

    # ******************** Crypto

    # kdf method. one of "scrypt_then_pbkdf2_hmac", "pbkdf2_hmac", "scrypt"
    # scrypt_then_pbkdf2_hmac (with 16 MB mem) and 12000 rounds of pbkdf2 gets about 50 milliseconds,
    # or 5 sec for 100 hashes. Thats on 4.3 GHz zen+ AWS time probably goes up 2x
    "KRPTO_KDF_METHOD": 'scrypt_then_pbkdf2_hmac',

    # scrypt params, generally must be powers of two.
    # N is work factor, R is block size
    # memory usage: 128 * r * N >>>>>>> here we get 128 * 8 * 16 * 1024 = 16 MB
    "KRPTO_SCRYPT_PARAMS_N": 16 * 1024,
    "KRPTO_SCRYPT_PARAMS_R": 8,

    # pbkdf2 params. set low if scrypt_then_pbkdf2_hmac. otherwise set higher.
    # of course users can just use a bit more than 8-10 chars and this wont be important.
    "KRPTO_PBKDF2_HMAC_ITERATIONS": 12000,

    # Salt for auth subsystem. We might have other salts for other subsystems. This is avoid sharing secrets
    # between subsystems but enable them to get seeded from one secret. For example, we might encrypt and/or sign
    # client side cookies. We might also have an API for challenge/response for something. The DB might provide
    # a single session secret that these subsystems can use to derive their own subsystem secrets from.
    "KRPTO_AUTH_SS_KDF_SALT": b'b261ef47_l6sk_auth_1ea8f2ac',
})

# ******************** On disk sqlite DAO
_KNOBS.update({

    # if retrying, delay this long before reconnecting. Careful this will stall every DAO call. The reconnect
    # is a connection health/lifecycle management feature, not a retry until request is served feature.
    'DAO_SQLITE_FS_RECONNECT_DELAY': 0.01,

    # synchronous off means we are good with a write() once its passed to the OS.
    # unlike PG, this isnt just a dataloss risk, turning this off does risk data corruption.
    "DAO_SQLITE_FS_PRAGMAS": [
        "PRAGMA synchronous = OFF",
    ],

    # drop old files/tables on each run
    "DAO_SQLITE_FS_START_WITH_CLEAN_FILE": True,

    # sqlite db file, disk, ram. must be string.
    "DAO_SQLITE_FS_DB_FILENAME": str((Path(__file__) / '..' / '..' / 'ignored_data' / 'DBL' / 'l6sk.db').resolve()),

})

# ******************** in mem sqlite DAO
_KNOBS.update({
    # TODO fill in.
    "DAO_SQLITE_MEM_XXXX": "YYYYYYYYY",

})

# ******************** Service Limits
# various subsystems may read these limits and refuse service beyond them.
# for example the limits on user name length could be used by the web layer to reject too long or too short names,
# but also could be read and used by DB schema assert them on db records
_KNOBS.update({

    "SL_USER_NAME_LEN_MIN": 3,
    "SL_USER_NAME_LEN_MAX": 64,
})


# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================== Web App knobs
_KNOBS.update({
    'PORT': 6060,
    'LISTEN_HOST': '127.0.0.1',
    'WA_DEBUG_MODE': False,

    # 'WSGI_SERVER': 'cheroot',

    # sleep wait timeout for request handlers that are waiting for DBL results
    "REQUEST_SLEEP_WAIT_TIMEOUT": 0.01,

})


# ======================================================================================================================
# ======================================================================================================================
# ============================================================================================ KNOB MAN INTERFACE / INIT
def init_knob_man():

    print(f"knob man init called. Time now: {time.time():,.4f}")

    # if there is something than needs compute at init time do it here.

    # ******************** deal w/ sqlite db directory and clean start flags.
    db_file_parent_dir = str((Path(_KNOBS["DAO_SQLITE_DISK_DB_FILENAME"]) / '..').resolve())

    # make sqlite db dir if not exists:
    Path(db_file_parent_dir).mkdir(parents=True, exist_ok=True)

    # drop db file, if it exists.
    if _KNOBS["DAO_SQLITE_FS_START_WITH_CLEAN_FILE"]:

        db_file = _KNOBS["DAO_SQLITE_FS_DB_FILENAME"]
        if (":memory:" != db_file) and os.path.exists(db_file):
            try:
                os.remove(db_file)
            except Exception as ex:
                print(f"Caught exception while attempting to reset sqlit db file: {ex}")


    # ******************** static folder path.
    repo_root = (Path(__file__) / '..' / '..').resolve()
    print(f'repo_root appears to be: {repo_root}')

    static_dir_pathname = str((repo_root / 'static').resolve())
    print(f'static folder path resolved to be at: {static_dir_pathname}')

    _KNOBS["STATIC_DIR_PATHNAME"] = static_dir_pathname

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


def update_knobs(new_knobs: dict):
    """ Given a knobs dict (or partial knobs dict), update current knobs. Conflict to be
    resolved in favor of the incoming dict. """

    if not _KNOBMAN_INITIALIZED:
        init_knob_man()

    _KNOBS.update(new_knobs)

# this for dbg info.
def get_dbg_snapshot_as_json_string() -> str:
    """ Try to turn current KNOBS into a JSON string and return this string. Not a reliable
    serializer/deserializer. Might lose info during this process. """

    # with default lambda trick, i dont think exception can occur actually anymore.
    result = json.dumps(_KNOBS, sort_keys=True, indent=4, default=lambda x: str(x))

    return result
