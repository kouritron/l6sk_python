# import os
import unittest
import time

from l6sk import crypt_util

# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================
# ============================================================================== Test DATA, params, expected results ...
# NOTE: scrypt memory usage: 128 * r * N
# n:1024 and r:8 results ------>>>>> 128 * 8 * 1024 = 1 MB

# list of dicts. each dict is one test group
_TD_AUTH_KDF_XPECTED_DATA = [

    # test group: 1 MB scrypt, pbkdf ignored
    {
        "kwargs": {
            "salt": b'fafd52b82186a75e0869bf33',
            "scrypt_n": 1024,
            "scrypt_r": 8,
            "pbkdf2_iters": 8000,
            "dklen": 18,
            "kdf_method": 'scrypt',
        },
        # 2-tuple: <pt, xpected shadow>
        "xpected_records": [
            ("hello world", "xy79Xe3SNM1pL3Xz43Ffne6V"),
            ("password123", "rtrKaixgsZub3cuRq6PDF4yt"),
            ("greywolf", "HAyAXBHnB_6qv8srgYArZMnZ"),
        ]
    },

    # test group: 16 MB scrypt, pbkdf ignored
    {
        "kwargs": {
            "salt": b'fafd52b82186a75e0869bf33',
            "scrypt_n": 16 * 1024,
            "scrypt_r": 8,
            "pbkdf2_iters": 8000,
            "dklen": 18,
            "kdf_method": 'scrypt',
        },
        # 2-tuple: <pt, xpected shadow>
        "xpected_records": [
            ("hello world", "VF7fvKPvTLQw08sQVTa8A_l8"),
            ("password123", "LIeK2TpP5QaaTLYlnFUofd-v"),
            ("greywolf", "vHN3r2UcDsr8NUPV2BEcmBoW"),
        ]
    },

    # test group: heavy pbkdf, scrypt ignored (and set low)
    {
        "kwargs": {
            "salt": b'fafd52b82186a75e0869bf33',
            "scrypt_n": 1024,
            "scrypt_r": 8,
            "pbkdf2_iters": 1000 * 1000,
            "dklen": 18,
            "kdf_method": 'pbkdf2_hmac',
        },
        # 2-tuple: <pt, xpected shadow>
        "xpected_records": [
            ("hello world", "slHCzxdH86DUntgOCkDilSEj"),
            ("password123", "9j-wmilrp65-VNOgCYViyw4e"),
            ("greywolf", "rZNyQ6ybz3q0bgF9I4BMFucI"),
        ]
    },

    # test group: lite pbkdf, scrypt ignored (and set hi)
    {
        "kwargs": {
            "salt": b'fafd52b82186a75e0869bf33',
            "scrypt_n": 16 * 1024,
            "scrypt_r": 8,
            "pbkdf2_iters": 4 * 1000,
            "dklen": 18,
            "kdf_method": 'pbkdf2_hmac',
        },
        # 2-tuple: <pt, xpected shadow>
        "xpected_records": [
            ("hello world", "XwJqGSSj-E5IS2M_P6R67wAI"),
            ("password123", "F8qe1EMuccIP8wU1xbcoRc5N"),
            ("greywolf", "hb9mECV-BLt5FzAufgAip98e"),
        ]
    },

    # test group: scrypt_then_pbkdf2_hmac
    # 16mb + 40k iterations, about 60 ms per dk (on 4 ghz zen+)
    {
        "kwargs": {
            "salt": b'16a90eed44842585e4900931',
            "scrypt_n": 16 * 1024,
            "scrypt_r": 8,
            "pbkdf2_iters": 40 * 1000,
            "dklen": 18,
            "kdf_method": 'scrypt_then_pbkdf2_hmac',
        },
        # 2-tuple: <pt, xpected shadow>
        "xpected_records": [
            ("hello world", "IxsSdMsvmkAqW94ncW4QVf62"),
            ("password123", "TribxtmGykrTWUvgLQ_0hYdI"),
            ("redwolf", "r_RrPHNLcLOXbuyIOyjXa-aD"),
        ]
    },
]

# ======================================================================================================================
# ======================================================================================================================
class TestAuthKDF(unittest.TestCase):

    # runs once per test class
    @classmethod
    def setUpClass(cls):

        super().setUpClass()
        print("---------------------- setUpClass() called")
        # print(os.environ['PATH'])

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()

        print("---------------------- tearDownClass() called")

    # runs once per test case
    def setUp(self):
        pass

    def tearDown(self):
        pass

    # ==================================================================================================================
    def test_auth_kdf(self):

        print(f"Testing Auth kdf class ... \n")

        # _TD_AUTH_KDF_XPECTED_DATA: list of dicts. each dict is one test group
        for test_group in _TD_AUTH_KDF_XPECTED_DATA:

            start_time = time.perf_counter()

            print('Running new test group ...')
            auth_kdf = crypt_util.AuthKDF(**test_group['kwargs'])

            for xpected_record in test_group['xpected_records']:
                # 2-tuple: <pt, xpected shadow>
                pt, xpct_shadow = xpected_record

                # get the actual dk.
                actual_shadow = auth_kdf.get_pw_shadow_b64(pt)
                self.assertEqual(actual_shadow, xpct_shadow)

                print(f"passed test. pt: {pt}  --  actual shadow: {actual_shadow}  --  xpct shadow: {xpct_shadow}")

            deltaT = time.perf_counter() - start_time
            print(f"test group done. deltaT: {deltaT*1000:.2f} milli seconds \n")


# ======================================================================================================================
# ======================================================================================================================
if __name__ == '__main__':
    unittest.main()
