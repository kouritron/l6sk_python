
import os
import unittest

# ======================================================================================================================
# ======================================================================================================================
class TestSQLiteDAO(unittest.TestCase):

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
    # ==================================================================================================================
    def test_1(self):

        self.assertEqual(2, 1 + 1)



if __name__ == '__main__':
    unittest.main()
