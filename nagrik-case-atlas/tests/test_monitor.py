import os, unittest
os.environ.setdefault('DATABASE_URL','sqlite:////tmp/constituency_explorer_test_monitor.db')
from backend.app.monitor import host_allowed

class MonitorHostAllowlistTests(unittest.TestCase):
    def test_official_ecourts_domain_allowed(self):
        self.assertTrue(host_allowed('services.ecourts.gov.in'))
    def test_http_is_rejected_by_url_checker(self):
        from backend.app.monitor import check_url
        with self.assertRaises(ValueError): check_url('http://services.ecourts.gov.in/path')
    def test_arbitrary_domain_not_allowed(self):
        self.assertFalse(host_allowed('example.com'))

if __name__=='__main__': unittest.main()
