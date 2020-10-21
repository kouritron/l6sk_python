# test_dbl_api.py
# TODO implement this, every implementation of dbl should pass this test.
# these tests can bypass the dispatch manager. include test cases, for DBI API operations as if the req just came
# of the dispatch queue and rdy to be processed.
# or maybe not. This would turn it into a dao test. put that in its own file.


import os
import unittest

# ======================================================================================================================
class TestSample(unittest.TestCase):

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
    def test_1(self):
        """ Sample test 1. """

        self.assertEqual(2, 1 + 1)

    def test_2(self):
        """ Sample test 2. """

        self.assertGreater(2, 1)

    def test_3(self):
        """ Sample test 3. """

        self.assertTrue("hi" + "truthy")


if __name__ == '__main__':
    unittest.main()
