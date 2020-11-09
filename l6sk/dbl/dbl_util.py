import os
import time
import base64
import hashlib

import uuid
# uuid module typicall uses 16 Bytes == 128 bits

from l6sk import knobman as km

# ======================================================================================================================
# ================================================================================================================= UUID
# ======================================================================================================================

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
def _get_login_key_scrypt(pw: bytes, salt: bytes, n: int, r: int) -> bytes:

    # ***** scrypt rec params
    # N – iterations count/work factor, ie 16384 or 2048
    # r – block size, e.g. 8
    # p – parallelism factor, usually 1 everywhere in every language.
    # For Python it especially doesnt make sense to go with anything other than 1. just increase other params
    # if you have time to do more work. This shouldnt even be a knob.

    # memory usage (all assuming p is 1):
    # mem = 128 * N * r bytes
    # example: N=2048, r=8  --  memory usage: 128 * 2048 * 8 * 1 = 2 MB
    # example: N=16384, r=8  --  memory usage: 128 * 2048 * 8 * 1 = 16 MB

    # dk is bytes
    # 16 bytes 128 bits, no risk of collision.
    # 18 bytes 144 bits, no risk of collision. aligns with b64 so no pad (trailing =) is required.
    # p is always 1. should not be a knob.
    dk = hashlib.scrypt(pw, salt=salt, n=n, r=r, p=1, dklen=18)

    return dk


def _get_login_key_pbkdf2(pw: bytes, salt: bytes, pbkdf2_iters: int) -> bytes:

    # dk is bytes
    # 16 bytes 128 bits, no risk of collision.
    # 18 bytes 144 bits, no risk of collision. aligns with b64 so no pad (trailing =) is required.
    dk = hashlib.pbkdf2_hmac('sha512', pw, salt, pbkdf2_iters, dklen=18)

    return dk


def derive_login_key_from_user_pass(pw: str) -> str:
    ''' Given a user's account password passed to the API derive a key (using a decent kdf) that can be stored
    for persistence Argument must be string and return value is hex encoded string.
    '''

    # salt = b'todo_get_salt_from_conf_system'
    salt = km.get_knob("DBL_KDF_SALT")
    scrypt_n = km.get_knob("DBL_SCRYPT_PARAMS_N")
    scrypt_r = km.get_knob("DBL_SCRYPT_PARAMS_R")
    pbkdf2_iters = km.get_knob("DBL_PBKDF2_HMAC_ITERATIONS")

    pw = pw.encode('utf8')
    derived_key = None

    kdf_method = km.get_knob('DBL_KDF_METHOD').lower()

    if kdf_method in {'pbkdf2', 'pbkdf2_hmac'}:
        derived_key = _get_login_key_pbkdf2(pw, salt=salt, pbkdf2_iters=pbkdf2_iters)

    elif kdf_method in {'scrypt'}:
        derived_key = _get_login_key_scrypt(pw, salt=salt, n=scrypt_n, r=scrypt_r)

    elif kdf_method in {'scrypt_then_pbkdf2_hmac'}:
        scrypt_dk = _get_login_key_scrypt(pw, salt=salt, n=scrypt_n, r=scrypt_r)
        derived_key = _get_login_key_pbkdf2(scrypt_dk, salt=salt, pbkdf2_iters=pbkdf2_iters)

    else:
        msg = "Fatal Error in DBL: Unknown kdf option specified. Can not derive any keys."
        raise Exception(msg)

    return base64.urlsafe_b64encode(derived_key).decode('ascii')


# ======================================================================================================================
# ======================================================================================================================
# ============================================================================================================== DBG DEV


def _dbg_becnh_kdf():

    iterations = 100

    start_time = time.perf_counter()
    for _ in range(iterations):
        derive_login_key_from_user_pass('hello world')
    elapsed_time = time.perf_counter() - start_time

    print(f"total time: {elapsed_time}  --  iterations: {iterations}")
    print(f"time per call {elapsed_time/float(iterations)}")
    # we got:
    # <pbkdf, sha512, kdf iter 40k, dklen=32> -->> 30 ms (not micro) per call, ~ 3 seconds for 100 calls
    # <pbkdf, sha512, kdf iter 40k, dklen=16> -->> 30 ms (not micro) per call, ~ 3 seconds for 100 calls

    print("")
    print(f"Example_dk: {derive_login_key_from_user_pass('hello world')}")
    print(f"Example_dk: {derive_login_key_from_user_pass('hello world')}")
    print(f"Example_dk: {derive_login_key_from_user_pass('password123')}")
    print(f"Example_dk: {derive_login_key_from_user_pass('bluefish')}")
    print(f"Example_dk: {derive_login_key_from_user_pass(os.urandom(64).hex())}")
    print(f"Example_dk: {derive_login_key_from_user_pass(os.urandom(64).hex())}")
    print(f"Example_dk: {derive_login_key_from_user_pass(os.urandom(64).hex())}")
    print(f"Example_dk: {derive_login_key_from_user_pass(os.urandom(64).hex())}")


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
    _dbg_bench_uuid()
    # _dbg_becnh_kdf()
