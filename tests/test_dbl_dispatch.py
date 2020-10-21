import os
import unittest

from l6sk.dbl.dbl_dispatch import DBL_REQ, DBL_REQUEST_DISPATCH, DBL_REQ_PRIORITY
from l6sk.dbl.dbl_api import DBL_API

# ======================================================================================================================
# ======================================================================================================================
# test data ...


# ======================================================================================================================
# ======================================================================================================================
class TestDBLDispatch(unittest.TestCase):

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

        dispatch = DBL_REQUEST_DISPATCH()

        for _ in range(10):
            res = dispatch.get_next_req()
            self.assertIsNone(res)

    def test_lots_of_put(self):

        dispatch = DBL_REQUEST_DISPATCH()

        for i in range(1000):
            next_rq = DBL_REQ(op=DBL_API.DESCRIBE_USER, data=f"{i}", priority=DBL_REQ_PRIORITY.LOW)
            dispatch.put_req(next_rq)

    def test_basic_put_and_get_back(self):

        dispatch = DBL_REQUEST_DISPATCH()

        sentinel = "123"
        test_req = DBL_REQ(op=DBL_API.DESCRIBE_USER, data=sentinel, priority=DBL_REQ_PRIORITY.HIGH)

        dispatch.put_req(test_req)

        actual_res = dispatch.get_next_req()
        print(f"Sentinel is: {sentinel} \nActual req: {actual_res}")

        self.assertEqual(actual_res.data, sentinel)

        actual_res = dispatch.get_next_req()
        print(f"Now expecting None -- Got back: {actual_res}")

        self.assertIsNone(actual_res)


# ======================================================================================================================
# ======================================================================================================================
if __name__ == '__main__':
    unittest.main()
