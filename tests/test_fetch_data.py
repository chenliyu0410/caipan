import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('fetch_data', Path(__file__).parents[1] / 'scripts/fetch_data.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class FetchTests(unittest.TestCase):
    def test_timeout_retries_and_returns_failure(self):
        with patch.object(m.urllib.request, 'urlopen', side_effect=TimeoutError('timeout')) as request, patch.object(m.time, 'sleep'):
            self.assertIsNone(m.fetch_moa_date('115.10.26'))
            self.assertEqual(request.call_count, 3)

    def test_failed_fetch_preserves_prices_and_publishes_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            history = Path(directory) / 'history.json'
            latest = Path(directory) / 'latest.json'
            original = {'dates': ['115.10.22'], 'records': {'109_C01': {'115.10.22': {'c': 28, 'h': 30, 'l': 26, 'v': 100}}}}
            history.write_text(json.dumps(original), encoding='utf-8')
            with patch.object(m, 'HISTORY_FILE', str(history)), patch.object(m, 'LATEST_FILE', str(latest)), patch.object(m, 'fetch_moa_date', return_value=None):
                report = m.update_history_data(days_back=0)
                self.assertEqual(len(report['failed_dates']), 1)
                self.assertEqual(report['successful_dates'], [])
                output = m.build_latest_dataset({'state': 'failed', **report})
                self.assertEqual(output['trade_date'], '115.10.22')
                self.assertEqual(output['fetch_status']['state'], 'failed')
                self.assertEqual(json.loads(history.read_text(encoding='utf-8')), original)

    def test_valid_empty_response_is_not_connection_failure(self):
        with patch.object(m, 'load_history', return_value={'dates': [], 'records': {}}), patch.object(m, 'save_history'), patch.object(m, 'fetch_moa_date', return_value=[]):
            report = m.update_history_data(days_back=0)
            self.assertEqual(report['failed_dates'], [])
            self.assertEqual(len(report['successful_dates']), 1)

if __name__ == '__main__':
    unittest.main()
