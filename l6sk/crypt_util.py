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
# ===================================================================================================== Unique random ID
# NOTE 1: constants in this class arent really knobs. they are just constants. Its the UID class's concern how
# to generate UID. the only knob for knobman is to decide if uuid is going be fast, slow, v1, v2, ....
class UUIDGen:
    def __init__(self, uuid_version: str, uuid_num_bytes=18) -> None:

        # assert minimum sensible defaults, disallow things that would break this implementation.

        # uuid less than 12 bytes is not going to be unique.
        assert uuid_num_bytes >= 12
        assert uuid_num_bytes < 64

        # diff versions trade spped for extra randomness caution. but they are really fast anyways.
        assert uuid_version in {'v1', 'v2', 'v3'}

        self._uuid_num_bytes = uuid_num_bytes
        self._uuid_version = uuid_version

        # v3 is paranoid. keeps a counter for extra safety against collisions
        self._uuid_v3_counter = 1

    # ------------------------------------------------------------------------------------------------------------------
    # v1 just os rand. approx 1 micro second (10 to the -6) not milli
    def _uuid_v1(self) -> bytes:
        return os.urandom(self._uuid_num_bytes)

    # v2 os rand + system clock + timing between multiple syscalls
    # approx 7 micro second (10 to the -6) not milli
    def _uuid_v2(self) -> bytes:

        # v2 is a bit paranoid about collisions.
        buf_bytes = str(time.time()).encode('ascii')
        buf_bytes += os.urandom(256)
        return hashlib.sha3_512(buf_bytes).digest()[:self._uuid_num_bytes]

    # v3 very paranoid
    # approx 25 micro seconds (10 to the -6) not milli
    def _uuid_v3(self) -> bytes:

        self._uuid_v3_counter += 1
        buf_bytes = os.urandom(32)
        buf_bytes += str(time.time()).encode('ascii')

        for _ in range(16):
            buf_bytes += os.urandom(16)
            self._uuid_v3_counter += 1

        buf_bytes += str(self._uuid_v3_counter).encode('ascii')
        return hashlib.sha3_512(buf_bytes).digest()[:self._uuid_num_bytes]

    # ------------------------------------------------------------------------------------------------------------------
    def get_l6sk_uuid_b64(self) -> str:

        uuid_bytes = None

        if self._uuid_version in {'v2'}:
            uuid_bytes = self._uuid_v2()
        elif self._uuid_version in {'v3'}:
            uuid_bytes = self._uuid_v3()
        else:
            uuid_bytes = self._uuid_v1()

        return base64.urlsafe_b64encode(uuid_bytes).decode('ascii')


# ======================================================================================================================
# ======================================================================================================================
# ================================================================================================================== KDF
class AuthKDF:
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
        log.dbg(f'AUTH_KDF details:\n{self}')

    def __str__(self) -> str:
        str_builder = f"<AUTH_KDF: {self._salt}, {self._scrypt_n}, {self._scrypt_r}, {self._pbkdf2_prf}, "
        str_builder += f"{self._dklen}, {self._kdf_method}"

        return str_builder

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
_crypt_util_initialized = False
_auth_kdf_singleton = None
_uuid_singleton = None


def init_crypt_util():

    global _crypt_util_initialized
    global _auth_kdf_singleton
    global _uuid_singleton

    # ***** get AUTH_KDF params and init one copy.
    _auth_kdf_singleton = AuthKDF(
        salt=km.get_knob("CU_AUTH_KDF__SALT"),
        scrypt_n=km.get_knob("CU_AUTH_KDF__SCRYPT_N"),
        scrypt_r=km.get_knob("CU_AUTH_KDF__SCRYPT_R"),
        pbkdf2_iters=km.get_knob("CU_AUTH_KDF__PBKDF2_HMAC_ITERATIONS"),
        dklen=km.get_knob("CU_AUTH_KDF__DKLEN"),
        kdf_method=km.get_knob('CU_AUTH_KDF__METHOD').lower(),
    )

    # ***** get UUID generator params and init one copy.
    _uuid_singleton = UUIDGen(
        uuid_version=km.get_knob("CU__UUID_VERSION"),
        uuid_num_bytes=km.get_knob("CU__UUID_NUM_BYTES"),
    )

    _crypt_util_initialized = True


def get_auth_kdf() -> AuthKDF:
    """ Return the default AUTH_KDF instance. """

    if not _crypt_util_initialized:
        init_crypt_util()

    return _auth_kdf_singleton


def get_uuid_generator() -> UUIDGen:
    """ Return the default UUIDGen instance. """

    if not _crypt_util_initialized:
        init_crypt_util()

    return _uuid_singleton


# ======================================================================================================================
# ======================================================================================================================
# ============================================================================================================== DBG DEV
# timeit module doesnt really make for less code here. roughly same number of lines.
def _dbg_becnh_kdf():

    # do the init to avoid, getting lazy init into benchmark
    init_crypt_util()

    iterations = 20

    start_time = time.perf_counter()
    for _ in range(iterations):
        get_auth_kdf().get_pw_shadow_b64('hello world')
    elapsed_time = time.perf_counter() - start_time

    print(f"total time: {elapsed_time:.2f} seconds  --  iterations: {iterations}")
    print(f"time per call {(elapsed_time/float(iterations))*1000:.4f} ms")
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

    # do the init to avoid, getting lazy init into benchmark
    init_crypt_util()

    # v1
    print('\n----------------------------- mini bench for v1: ')
    count = 1 * 1000
    start_time = time.perf_counter()
    for _ in range(count):
        get_uuid_generator()._uuid_v1()  # pylint: disable=protected-access
    elapsed_time = time.perf_counter() - start_time

    print(f"total time: {elapsed_time:.4f} seconds  --  iterations: {count}")
    print(f"time per call {(elapsed_time/float(count))*1000*1000:.4f} micro seconds")

    # v2
    print('\n----------------------------- mini bench for v2: ')
    count = 1 * 1000
    start_time = time.perf_counter()
    for _ in range(count):
        get_uuid_generator()._uuid_v2()  # pylint: disable=protected-access
    elapsed_time = time.perf_counter() - start_time

    print(f"total time: {elapsed_time:.4f} seconds  --  iterations: {count}")
    print(f"time per call {(elapsed_time/float(count))*1000*1000:.4f} micro seconds")

    # v3
    print('\n----------------------------- mini bench for v3: ')
    count = 1 * 1000
    start_time = time.perf_counter()
    for _ in range(count):
        get_uuid_generator()._uuid_v3()  # pylint: disable=protected-access
    elapsed_time = time.perf_counter() - start_time

    print(f"total time: {elapsed_time:.4f} seconds  --  iterations: {count}")
    print(f"time per call {(elapsed_time/float(count))*1000*1000:.4f} micro seconds")

# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================
if '__main__' == __name__:
    _dbg_bench_uuid()
    # _dbg_becnh_kdf()
