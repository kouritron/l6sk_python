import os
import unittest

from l6sk.dbl import dbl_util
from l6sk import knobman as km

# ======================================================================================================================
# ======================================================================================================================
# test data ...
_TEST_DATA_KDF_PARAMS = {

    # 3 psets for scrypt
    "scrypt_pset_1": {
        "DBL_KDF_METHOD": 'scrypt',

        # memory usage: 128 * r * N >>>>>>> here we get 128 * 8 * 1024 = 1 MB
        "DBL_SCRYPT_PARAMS_N": 1024,
        "DBL_SCRYPT_PARAMS_R": 8,
        "DBL_KDF_SALT": b'0260e393_litech4t_922fef1f',
    },
    "scrypt_pset_2": {
        "DBL_KDF_METHOD": 'scrypt',

        # memory usage: 128 * r * N >>>>>>> here we get 128 * 8 * 2 * 1024 = 2 MB
        "DBL_SCRYPT_PARAMS_N": 2 * 1024,
        "DBL_SCRYPT_PARAMS_R": 8,
        "DBL_KDF_SALT": b'0260e393_litech4t_922fef1f',
    },
    "scrypt_pset_3": {
        "DBL_KDF_METHOD": 'scrypt',

        # memory usage: 128 * r * N >>>>>>> here we get 128 * 8 * 16 * 1024 = 16 MB
        "DBL_SCRYPT_PARAMS_N": 16 * 1024,
        "DBL_SCRYPT_PARAMS_R": 8,
        "DBL_KDF_SALT": b'0260e393_litech4t_922fef1f',
    },
    # TODO: increase maxmem (which i think defautls to 16 or 32MB and do a larger one)

    # two psets for pbkdf2
    "pbkdf2_pset_1": {
        "DBL_KDF_METHOD": 'pbkdf2_hmac',
        "DBL_PBKDF2_HMAC_ITERATIONS": 40000,
        "DBL_KDF_SALT": b'0260e393_litech4t_922fef1f',
    },
    "pbkdf2_pset_2": {
        "DBL_KDF_METHOD": 'pbkdf2_hmac',
        "DBL_PBKDF2_HMAC_ITERATIONS": 100 * 1000,
        "DBL_KDF_SALT": b'0260e393_litech4t_922fef1f',
    },

    # params for scrypt then pbkdf2
    "scrypt_then_pbkdf2_pset_1": {
        "DBL_KDF_METHOD": 'scrypt_then_pbkdf2_hmac',

        # memory usage: 128 * r * N >>>>>>> here we get 128 * 8 * 8 * 2048 = 16 MB
        "DBL_SCRYPT_PARAMS_N": 8 * 2048,
        "DBL_SCRYPT_PARAMS_R": 8,
        "DBL_PBKDF2_HMAC_ITERATIONS": 8000,
        "DBL_KDF_SALT": b'0260e393_litech4t_922fef1f',
    },
}

_TEST_DATA_KDF = [

    # 3-tuple: <pt, xpected shadow, crypt params by dereferencing from _TEST_DATA_KDF_PARAMS>
    ("hello world", "Doy5qDJuzmxhgI7GqATM1pSE", _TEST_DATA_KDF_PARAMS["scrypt_pset_1"]),
    ("hello world", "_k_T6Bs1-TzBRC5URIdyZSUS", _TEST_DATA_KDF_PARAMS["scrypt_pset_2"]),
    ("hello world", "QmADcx_AwhHrIG_zPc3A950j", _TEST_DATA_KDF_PARAMS["scrypt_pset_3"]),
    ("hello world", "F1F7L-uzKwqqRaOWAl594TRT", _TEST_DATA_KDF_PARAMS["pbkdf2_pset_1"]),
    ("hello world", "5MVo1UEDm7VeJXg6rWir6FP2", _TEST_DATA_KDF_PARAMS["pbkdf2_pset_2"]),
    ("hello world", "UqTM-nrSgexQE04JpPnwQstp", _TEST_DATA_KDF_PARAMS["scrypt_then_pbkdf2_pset_1"]),

    # diff pass
    ("password123", "eZuAXsiig-pV-hOO2eZURa7l", _TEST_DATA_KDF_PARAMS["scrypt_pset_1"]),
    ("password123", "chHf8o-KZZl4Umm4Y6BYsASj", _TEST_DATA_KDF_PARAMS["scrypt_pset_2"]),
    ("password123", "emekoZBCHny09PU4ngG_3UQc", _TEST_DATA_KDF_PARAMS["scrypt_pset_3"]),
    ("password123", "vTIObepvBHjekUFAcoCZvcQP", _TEST_DATA_KDF_PARAMS["pbkdf2_pset_1"]),
    ("password123", "q7XUsOwi-LIru-NIXvegAnrA", _TEST_DATA_KDF_PARAMS["pbkdf2_pset_2"]),
    ("password123", "RoqaWAKIRq0dI-Cpkuo2vOZ3", _TEST_DATA_KDF_PARAMS["scrypt_then_pbkdf2_pset_1"]),

    # diff pass
    ("bluefish", "Wap7NTu9MvjpdWvAtaeu98Z3", _TEST_DATA_KDF_PARAMS["scrypt_pset_1"]),
    ("bluefish", "Ff6hq6oSP_-mdXBP5xf8u5dx", _TEST_DATA_KDF_PARAMS["scrypt_pset_2"]),
    ("bluefish", "DWXl6E4zzm31bmteYVrH4rqt", _TEST_DATA_KDF_PARAMS["scrypt_pset_3"]),
    ("bluefish", "X1Es0TaELoeqvqoNUIV3Ga9P", _TEST_DATA_KDF_PARAMS["pbkdf2_pset_1"]),
    ("bluefish", "yoOXoWCmnuMLCJDUrnDPuBVI", _TEST_DATA_KDF_PARAMS["pbkdf2_pset_2"]),
    ("bluefish", "VlF3RXBCCGz57c7Svv-N-3Sm", _TEST_DATA_KDF_PARAMS["scrypt_then_pbkdf2_pset_1"]),
]


# ======================================================================================================================
# ======================================================================================================================
class TestDBLUtil(unittest.TestCase):

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
    def test_empty_dispatch(self):

        for test_record in _TEST_DATA_KDF:

            # 3-tuple: <pass plaintext, xpected shadow, crypt knobs for knob man>
            pt, xpct_shadow, kdf_knobs = test_record
            km.update_knobs(kdf_knobs)

            # get actual dk.
            actual_shadow = dbl_util.derive_login_key_from_user_pass(pt)
            self.assertEqual(actual_shadow, xpct_shadow)

            print(f"passed test case. pt: {pt}  --  actual shadow: {actual_shadow}  --  xpct shadow: {xpct_shadow}")


# ======================================================================================================================
# ======================================================================================================================
if __name__ == '__main__':
    unittest.main()
