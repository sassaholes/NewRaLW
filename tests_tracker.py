import unittest

from tracker import parse_ddg_results, unwrap_ddg_redirect


class TrackerParsingTests(unittest.TestCase):
    def test_unwrap_ddg_redirect_extracts_uddg(self) -> None:
        wrapped = "https://duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.com%2Fwatch%3Fv%3D1"
        self.assertEqual(unwrap_ddg_redirect(wrapped), "https://example.com/watch?v=1")

    def test_parse_ddg_results_with_classic_markup(self) -> None:
        html = '''
        <a class="result__a" href="https://duckduckgo.com/l/?uddg=https%3A%2F%2Fyoutube.com%2Fwatch%3Fv%3Dabc">Adele - Hello</a>
        <div class="result__snippet">Popular upload</div>
        '''
        rows = parse_ddg_results(html, "Adele Hello")
        self.assertEqual(len(rows), 1)
        self.assertIn("youtube.com/watch?v=abc", rows[0].url)

    def test_parse_ddg_results_with_testid_markup(self) -> None:
        html = '''
        <article>
          <h2><a data-testid="result-title-a" href="https://example.com/path">Example title</a></h2>
          <div data-result-snippet="1">Sample snippet text</div>
        </article>
        '''
        rows = parse_ddg_results(html, "Adele Hello")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].url, "https://example.com/path")
        self.assertEqual(rows[0].title, "Example title")
        self.assertIn("Sample snippet", rows[0].snippet)


if __name__ == "__main__":
    unittest.main()
