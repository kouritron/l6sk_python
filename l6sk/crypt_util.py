import os
import time
import base64
import hashlib

import uuid
# uuid module typicall uses 16 Bytes == 128 bits

from l6sk import knobman as km
from l6sk import log_util as log


# ======================================================================================================================
# ======================================================================================================================
# ================================================================================================================= UUID

# 18 bytes (144 bits), 21, 24, ... aligns with b64 so no trailing '=' is needed.
# choose between 8 and 64. (8 bytes == 64 bits  --  64 bytes == 512 bits)
_UUID_LEN_IN_BYTES = 18

# used by v3
_UUID_V3_COUNTER = 1


# **************************************** v1 just os rand
# approx 1 micro second (10 to the -6) not milli
def _get_rand_bytes_v1() -> bytes:

    return os.urandom(_UUID_LEN_IN_BYTES)


# **************************************** v2 os rand + system clock + timing between syscalls
# approx 7 micro second (10 to the -6) not milli
def _get_rand_bytes_v2() -> bytes:

    buf_bytes = os.urandom(256)

    # if you are paranoid about collisions.
    buf_bytes += str(time.time()).encode('ascii')

    return hashlib.sha3_512(buf_bytes).digest()[:_UUID_LEN_IN_BYTES]


# **************************************** v3: very paranoid
# approx 25 micro seconds (10 to the -6) not milli
def _get_rand_bytes_v3() -> bytes:

    global _UUID_V3_COUNTER
    _UUID_V3_COUNTER += 1

    buf_bytes = os.urandom(32)

    # if you are paranoid about collisions.
    buf_bytes += str(time.time()).encode('ascii')

    for _ in range(16):
        buf_bytes += os.urandom(16)
        _UUID_V3_COUNTER += 1

    buf_bytes += str(_UUID_V3_COUNTER).encode('ascii')

    return hashlib.sha3_512(buf_bytes).digest()[:_UUID_LEN_IN_BYTES]


def dbl_uuid() -> str:

    # return _get_rand_bytes_v1().hex()
    return base64.urlsafe_b64encode(_get_rand_bytes_v3()).decode('ascii')


# ======================================================================================================================
# ======================================================================================================================
# ================================================================================================================== KDF
class AUTH_KDF:
    def __init__(self, salt: bytes, scrypt_n: int, scrypt_r: int, pbkdf2_iters: int, dklen: int, kdf_method: str):

        # allow only acceptable/sensible params, feel free to hard code constants here. These arent really knobs.
        # just crypto util common sense, with relatively broad acceptable ranges.
        # if some one supplied params outside this, they very probably made a mistake. This is just an extra check.
        assert isinstance(salt, bytes)
        assert len(salt) >= 4

        assert 0 == scrypt_n % 2
        assert 0 == scrypt_r % 2
        assert scrypt_n >= 512

        # 8 is really a minimum. A derived key (not user supplied key) w/ len less than is 8 worthless
        assert dklen >= 8

        # 1000 bare minimum. if pbkdf2 is the only kdf, this should be 100k+, no point in pbkdf w/ less than this.
        assert pbkdf2_iters >= 1000

        # only support modes by AUTH_KDF at the moment.
        assert kdf_method in {'pbkdf2', 'pbkdf2_hmac', 'scrypt', 'scrypt_then_pbkdf2_hmac'}

        # ***** scrypt params notes:
        # N – iterations count/work factor, ie 16384 or 2048
        # r – block size, e.g. 8
        # p – parallelism factor, usually 1 everywhere in every language.
        # For Python it especially doesnt make sense to go with anything other than 1. just increase other params
        # if you have time to do more work. This shouldnt even be a knob.

        # memory usage (all assuming p is 1):
        # mem = 128 * N * r bytes
        # example: N=2048, r=8  --  memory usage: 128 * 2048 * 8 * 1 = 2 MB
        # example: N=16384, r=8  --  memory usage: 128 * 2048 * 8 * 1 = 16 MB

        self._salt = salt
        self._scrypt_n = scrypt_n
        self._scrypt_r = scrypt_r

        # we might let this be a knob later. For now, I see no reason, to use anything other than sha512
        self._pbkdf2_prf = 'sha512'
        self._pbkdf2_iters = pbkdf2_iters

        self._dklen = dklen
        self._kdf_method = kdf_method

        log.info(f'Initialized new AUTH_KDF instance. kdf_method: {kdf_method}')
        log.dbg(f'New AUTH_KDF instance initialized w/ params: {self}')

    # ------------------------------------------------------------------------------------------------------------------
    def _get_dk_scrypt(self, pw: bytes) -> bytes:

        # dk is bytes
        # p is always 1. Should not be a knob.
        dk = hashlib.scrypt(pw, salt=self._salt, n=self._scrypt_n, r=self._scrypt_r, p=1, dklen=self._dklen)
        return dk

    def _get_dk_pbkdf2_hmac(self, pw: bytes) -> bytes:

        return hashlib.pbkdf2_hmac(self._pbkdf2_prf, pw, self._salt, self._pbkdf2_iters, dklen=self._dklen)

    def _get_dk(self, pw: bytes) -> bytes:

        if self._kdf_method in {'pbkdf2', 'pbkdf2_hmac'}:
            return self._get_dk_pbkdf2_hmac(pw)

        if self._kdf_method in {'scrypt'}:
            return self._get_dk_scrypt(pw)

        if self._kdf_method in {'scrypt_then_pbkdf2_hmac'}:
            return self._get_dk_pbkdf2_hmac(self._get_dk_scrypt(pw))

        # else: return None to make pylint happy.
        # we have checks in many places to make sure that kdf method is one of these supported modes.
        # This should never happen.
        return None

    # ------------------------------------------------------------------------------------------------------------------
    def get_pw_shadow_b64(self, pw: str) -> str:
        """ Derive and return this AUTH_KDF's output dk for a user password.
        Return value is a string, representing the urlsafe b64 encoding of the dk bytes. """

        pw_bytes = pw.encode('utf8')
        dk_bytes = self._get_dk(pw_bytes)

        return base64.urlsafe_b64encode(dk_bytes).decode('ascii')


# ======================================================================================================================
# ======================================================================================================================
# ================================================================================= Module API + the necessary lazy init
_SUBSYS_INITIALIZED = False
_AUTH_KDF_SINGLETON = None


def init_crypt_util():

    global _SUBSYS_INITIALIZED
    global _AUTH_KDF_SINGLETON

    # ***** get AUTH_KDF params and init one copy.
    _AUTH_KDF_SINGLETON = AUTH_KDF(
        salt=km.get_knob("CU_AUTH_KDF__SALT"),
        scrypt_n=km.get_knob("CU_AUTH_KDF__SCRYPT_N"),
        scrypt_r=km.get_knob("CU_AUTH_KDF__SCRYPT_R"),
        pbkdf2_iters=km.get_knob("CU_AUTH_KDF__PBKDF2_HMAC_ITERATIONS"),
        dklen=km.get_knob("CU_AUTH_KDF__DKLEN"),
        kdf_method=km.get_knob('CU_AUTH_KDF__METHOD').lower(),
    )

    _SUBSYS_INITIALIZED = True


def get_auth_kdf() -> AUTH_KDF:
    """ Return the default AUTH_KDF instance. """

    if not _SUBSYS_INITIALIZED:
        init_crypt_util()

    return _AUTH_KDF_SINGLETON


# ======================================================================================================================
# ======================================================================================================================
# ============================================================================================================== DBG DEV
# TODO: use timeit module for these and cut down.
def _dbg_becnh_kdf():

    iterations = 100

    start_time = time.perf_counter()
    for _ in range(iterations):
        get_auth_kdf().get_pw_shadow_b64('hello world')
    elapsed_time = time.perf_counter() - start_time

    print(f"total time: {elapsed_time}  --  iterations: {iterations}")
    print(f"time per call {elapsed_time/float(iterations)}")
    # we got:
    # <pbkdf, sha512, kdf iter 40k, dklen=32> -->> 30 ms (not micro) per call, ~ 3 seconds for 100 calls
    # <pbkdf, sha512, kdf iter 40k, dklen=16> -->> 30 ms (not micro) per call, ~ 3 seconds for 100 calls

    print("")
    print(f"Example_dk: {get_auth_kdf().get_pw_shadow_b64('hello world')}")
    print(f"Example_dk: {get_auth_kdf().get_pw_shadow_b64('hello world')}")
    print(f"Example_dk: {get_auth_kdf().get_pw_shadow_b64('password123')}")
    print(f"Example_dk: {get_auth_kdf().get_pw_shadow_b64('bluefish')}")
    print(f"Example_dk: {get_auth_kdf().get_pw_shadow_b64(os.urandom(64).hex())}")
    print(f"Example_dk: {get_auth_kdf().get_pw_shadow_b64(os.urandom(64).hex())}")
    print(f"Example_dk: {get_auth_kdf().get_pw_shadow_b64(os.urandom(64).hex())}")
    print(f"Example_dk: {get_auth_kdf().get_pw_shadow_b64(os.urandom(64).hex())}")


# **************************************** uuid
def _dbg_bench_uuid():

    print('----------------------------- mini bench for v1: ')

    count = 1 * 1000

    start_time = time.perf_counter()
    for _ in range(count):
        _get_rand_bytes_v1()
    elapsed_time = time.perf_counter() - start_time

    print(f"total time: {elapsed_time}  --  iterations: {count}")
    print(f"time per call {elapsed_time/float(count)}")

    print('----------------------------- mini bench for v2: ')

    count = 1 * 1000

    start_time = time.perf_counter()
    for _ in range(count):
        _get_rand_bytes_v2()
    elapsed_time = time.perf_counter() - start_time

    print(f"total time: {elapsed_time}  --  iterations: {count}")
    print(f"time per call {elapsed_time/float(count)}")

    print('----------------------------- mini bench for v3: ')

    count = 1 * 1000

    start_time = time.perf_counter()
    for _ in range(count):
        _get_rand_bytes_v3()
    elapsed_time = time.perf_counter() - start_time

    print(f"total time: {elapsed_time}  --  iterations: {count}")
    print(f"time per call {elapsed_time/float(count)}")


# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================
if '__main__' == __name__:
    # _dbg_bench_uuid()
    _dbg_becnh_kdf()
