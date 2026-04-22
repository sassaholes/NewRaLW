import unittest

from tracker import detect_platform


class TrackerSmokeTests(unittest.TestCase):
    def test_detect_x(self):
        self.assertEqual(detect_platform("https://x.com/some/post"), "x")
        self.assertEqual(detect_platform("https://twitter.com/some/post"), "x")


if __name__ == "__main__":
    unittest.main()
