import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('fetch_data', Path(__file__).parents[1] / 'scripts/fetch_data.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

NO_PROXY = {'MOA_PROXY_BASE': '', 'MOA_PROXY_TOKEN': '', 'MOA_ALLOW_DIRECT': '1'}
VIA_PROXY = {'MOA_PROXY_BASE': 'https://proxy.example/?url={url}', 'MOA_PROXY_TOKEN': '', 'MOA_ALLOW_DIRECT': '1'}


class FakeResponse:
    """模擬 urlopen 的回應物件（context manager + read）"""

    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self):
        return self.payload


class FetchTests(unittest.TestCase):
    def setUp(self):
        # 路由記憶是模組層級狀態，每個測試都要從乾淨的狀態開始
        m.reset_route_cache()

    def test_timeout_retries_and_returns_failure(self):
        with patch.dict(m.os.environ, NO_PROXY), patch.object(m.urllib.request, 'urlopen', side_effect=TimeoutError('timeout')) as request, patch.object(m.time, 'sleep'):
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

    def test_routes_default_to_direct_only(self):
        with patch.dict(m.os.environ, NO_PROXY):
            routes = m.build_routes('115.10.27')
        self.assertEqual([label for label, _ in routes], ['直連'])
        self.assertTrue(routes[0][1].startswith('https://data.moa.gov.tw/'))

    def test_proxy_is_tried_before_direct(self):
        with patch.dict(m.os.environ, VIA_PROXY):
            routes = m.build_routes('115.10.27')
        self.assertEqual([label for label, _ in routes], ['代理', '直連'])
        self.assertTrue(routes[0][1].startswith('https://proxy.example/?url=https%3A%2F%2Fdata.moa.gov.tw'))

    def test_proxy_without_placeholder_appends_encoded_target(self):
        with patch.dict(m.os.environ, dict(VIA_PROXY, MOA_PROXY_BASE='https://proxy.example/get/')):
            routes = m.build_routes('115.10.27')
        self.assertTrue(routes[0][1].startswith('https://proxy.example/get/https%3A%2F%2Fdata.moa.gov.tw'))

    def test_direct_can_be_disabled(self):
        with patch.dict(m.os.environ, dict(VIA_PROXY, MOA_ALLOW_DIRECT='0')):
            routes = m.build_routes('115.10.27')
        self.assertEqual([label for label, _ in routes], ['代理'])

    def test_falls_back_to_direct_when_proxy_is_dead(self):
        def fake_urlopen(req, **kwargs):
            if 'proxy.example' in req.full_url:
                raise TimeoutError('timeout')
            return FakeResponse(json.dumps([{'作物名稱': '高麗菜'}]).encode('utf-8'))

        with patch.dict(m.os.environ, VIA_PROXY), patch.object(m.urllib.request, 'urlopen', side_effect=fake_urlopen), patch.object(m.time, 'sleep'):
            items = m.fetch_moa_date('115.10.27')
        self.assertEqual(items, [{'作物名稱': '高麗菜'}])

    def test_working_route_is_reused_for_later_dates(self):
        calls = []

        def fake_urlopen(req, **kwargs):
            calls.append(req.full_url)
            if 'proxy.example' in req.full_url:
                raise TimeoutError('timeout')
            return FakeResponse(b'[]')

        with patch.dict(m.os.environ, VIA_PROXY), patch.object(m.urllib.request, 'urlopen', side_effect=fake_urlopen), patch.object(m.time, 'sleep'):
            m.fetch_moa_date('115.10.27')
            calls.clear()
            m.fetch_moa_date('115.10.26')
        # 第一個日期已確認直連可用，第二個日期不該再浪費時間重試死掉的代理
        self.assertEqual(len(calls), 1)
        self.assertIn('data.moa.gov.tw', calls[0])

    def test_token_goes_in_header_not_url(self):
        captured = {}

        def fake_urlopen(req, **kwargs):
            captured['headers'] = dict(req.headers)
            captured['url'] = req.full_url
            return FakeResponse(b'[]')

        with patch.dict(m.os.environ, dict(VIA_PROXY, MOA_PROXY_TOKEN='s3cret')), patch.object(m.urllib.request, 'urlopen', side_effect=fake_urlopen):
            m.fetch_moa_date('115.10.27')
        self.assertEqual(captured['headers'].get('X-caipan-token'), 's3cret')
        self.assertNotIn('s3cret', captured['url'])

    def test_report_records_which_route_worked(self):
        with patch.object(m, 'load_history', return_value={'dates': [], 'records': {}}), patch.object(m, 'save_history'), patch.dict(m.os.environ, NO_PROXY), patch.object(m.urllib.request, 'urlopen', return_value=FakeResponse(b'[]')):
            report = m.update_history_data(days_back=0)
        self.assertEqual(report['route'], '直連')


if __name__ == '__main__':
    unittest.main()
