"""Check dependency faults without installing packages or touching the network."""
from importlib import metadata
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools import windows_runtime as runtime


class WindowsRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.requirements = Path(self.temp.name) / 'requirements.txt'
        self.requirements.write_text("scapy==2.6.1\nwindows-curses==2.4.2; sys_platform == 'win32'\n")

    def test_ready_requires_matching_distributions_and_loadable_native_modules(self):
        with patch.object(runtime.metadata, 'version', side_effect=['2.6.1', '2.4.2']), \
                patch.object(runtime.importlib, 'import_module') as load:
            runtime.check_dependencies(self.requirements)
        self.assertEqual([call.args[0] for call in load.call_args_list], ['curses', 'scapy.all'])

    def test_missing_changed_and_broken_packages_do_not_report_ready(self):
        for error in (metadata.PackageNotFoundError('scapy'), RuntimeError('broken native module')):
            with self.subTest(error=error), \
                    patch.object(runtime.metadata, 'version', side_effect=['2.6.1', '2.4.2']), \
                    patch.object(runtime.importlib, 'import_module', side_effect=error):
                with self.assertRaises(type(error)):
                    runtime.check_dependencies(self.requirements)
        with patch.object(runtime.metadata, 'version', return_value='2.5.0'):
            with self.assertRaisesRegex(RuntimeError, 'needs updating'):
                runtime.check_dependencies(self.requirements)
        with patch.object(runtime.metadata, 'version', side_effect=metadata.PackageNotFoundError('scapy')):
            with self.assertRaises(metadata.PackageNotFoundError):
                runtime.check_dependencies(self.requirements)

    def test_new_requirement_syntax_is_not_silently_ignored(self):
        self.requirements.write_text('unknown-package>=1\n')
        with self.assertRaisesRegex(RuntimeError, 'Unsupported dependency'):
            runtime.check_dependencies(self.requirements)

    def test_unsupported_interpreters_are_rejected_before_installation(self):
        for host, version, architecture in [('darwin', (3, 14), 'macosx'),
                                             ('win32', (3, 9), 'win-amd64'),
                                             ('win32', (3, 15), 'win-amd64'),
                                             ('win32', (3, 14), 'win-arm64'),
                                             ('win32', (3, 14), 'win32')]:
            with self.subTest(host=host, version=version, architecture=architecture), \
                    patch.object(runtime.sys, 'platform', host), \
                    patch.object(runtime.sys, 'version_info', version), \
                    patch.object(runtime.sysconfig, 'get_platform', return_value=architecture):
                with self.assertRaises(RuntimeError):
                    runtime.check_python()
        with patch.object(runtime.sys, 'platform', 'win32'), \
                patch.object(runtime.sys, 'version_info', (3, 14)), \
                patch.object(runtime.sysconfig, 'get_platform', return_value='win-amd64'):
            runtime.check_python()


if __name__ == '__main__':
    unittest.main()
