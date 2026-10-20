"""Non-privileged, no side effects readiness-report tests."""
from pathlib import Path
from unittest.mock import patch
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts/qa'))
import principal_readiness as readiness

class ReadinessTests(unittest.TestCase):
    def test_non_linux_is_unsupported(self):
        with patch.object(readiness.sys,'platform','win32'):
            self.assertEqual(readiness.inspect()['status'],'UNSUPPORTED')

    def test_linux_reports_no_positive_uid_claim(self):
        with (patch.object(readiness.sys,'platform','linux'),
              patch.object(readiness.os,'getuid',create=True,return_value=1000),
              patch.object(readiness.os,'geteuid',create=True,return_value=1000),
              patch.object(readiness.os,'getgid',create=True,return_value=1000),
              patch.object(readiness.os,'getegid',create=True,return_value=1000),
              patch.object(readiness.os,'getgroups',create=True,return_value=[1000]),
              patch.object(readiness.os,'readlink',return_value='user:[4026531837]'),
              patch.object(readiness.shutil,'which',return_value='/usr/bin/test')):
            result=readiness.inspect()
        self.assertEqual(result['status'],'NOT_READY')
        self.assertFalse(result['separateBrokerUidVerified'])
        self.assertFalse(result['brokerStorageIsolated'])
        self.assertTrue(result['supplementalGroupsPresent'])

if __name__=='__main__':
    unittest.main()
