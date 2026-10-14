import contextlib
import io
import json
from pathlib import Path
import queue
import tempfile
import unittest
from unittest.mock import MagicMock, patch
from scapy.all import ARP, Ether, IP, UDP, Raw
import portal_auto as a
import portal_auto_platform as n
import portal_active_probe as p
from test_probe import fixture


class AutoTests(unittest.TestCase):
    def test_new_mac_auto_sessions_stop_before_administrator_access(self):
        for command in ('configure', 'baseline', 'run', 'verify-baseline'):
            with self.subTest(command=command), \
                 patch.object(a.sys, 'platform', 'darwin'), \
                 patch.object(a.sys, 'argv', ['portal_auto.py', command]), \
                 patch.object(n, 'require_admin') as require_admin, \
                 contextlib.redirect_stderr(io.StringIO()) as stderr, \
                 self.assertRaises(SystemExit) as stopped:
                a.main()
            self.assertEqual(stopped.exception.code, 2)
            self.assertIn('new sessions are disabled', stderr.getvalue())
            require_admin.assert_not_called()

    def setUp(self):
        self.old_network = p.network
        p.network = n
        self.s = {'config': {'interface': 'en0', 'ps5_ip': n.PS5, 'portal_ip': n.PORTAL},
                  'own_mac': '02:00:00:00:00:01', 'ps5_mac': '02:00:00:00:00:02', 'portal_mac': '02:00:00:00:00:03'}
        self.c = {'network': self.s['config'], 'profile': '65', 'ps5_mac': self.s['ps5_mac'], 'portal_mac': self.s['portal_mac']}
    def tearDown(self):
        p.network = self.old_network
    def frame(self, payload=b'feedback', **kw):
        return bytes(Ether(src=kw.get('mac',self.s['portal_mac']), dst=self.s['own_mac']) /
                     IP(src=kw.get('src',n.PORTAL), dst=kw.get('dst',n.PS5)) / UDP(dport=9296) / Raw(payload))
    def test_only_enrolled_outbound(self):
        for kw in ({'mac': self.s['ps5_mac'], 'src': n.PS5, 'dst': n.PORTAL},
                   {'mac': '02:00:00:00:00:77'}, {'src': '192.0.2.77'}, {'dst': '192.0.2.77'}):
            self.assertIsNone(a.outbound(self.frame(**kw),self.s))
    def test_unchanged_feedback_no_loop(self):
        before=self.frame(); after,*_=a.outbound(before,self.s)
        self.assertEqual(before[14:],after[14:])
        self.assertIsNone(a.outbound(after,self.s))
    def test_every_profile_and_baseline(self):
        data,*_=fixture()
        for delta in a.PROFILES.values():
            with patch.object(p,'PATCH_DELTA',delta):
                before=self.frame(data)
                after,_,_,changed=a.outbound(before,self.s)
                self.assertTrue(changed);self.assertEqual(len(before),len(after))
                after,_,_,changed=a.outbound(before,self.s,False)
                self.assertFalse(changed);self.assertEqual(before[14:],after[14:])
    def test_arp_does_not_redirect_video(self):
        for repair in (False,True):
            f=a.portal_arp(self.s,repair)
            self.assertEqual(f[ARP].pdst,n.PORTAL)
            self.assertEqual(f[ARP].psrc,n.PS5)
            self.assertEqual(f[ARP].hwsrc,self.s['ps5_mac' if repair else 'own_mac'])
    def test_restoration_failure(self):
        with patch.object(n,'configure'),patch.object(n,'open_socket',side_effect=OSError('down')):
            self.assertEqual(a.restore_peer(self.s),['down'])
    def test_restoration_repeated(self):
        with patch.object(n,'configure'),patch.object(n,'open_socket') as sock,patch.object(n,'send') as send,patch.object(a.time,'sleep'):
            self.assertEqual(a.restore_peer(self.s),[])
            self.assertEqual(send.call_count,5);sock.return_value.close.assert_called_once()
    def test_baseline_binds_config_and_code(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            self.assertFalse(a.baseline_valid(self.c,root))
            a.atomic_json(root/'auto-baseline.json',{'fingerprint':a.fingerprint(self.c),'forwarded_out':3,'restored':True})
            self.assertTrue(a.baseline_valid(self.c,root))
            self.c['profile']='200'
            self.assertFalse(a.baseline_valid(self.c,root))
    def test_bad_enrollment_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'c.json'
            for value in ('ff:ff:ff:ff:ff:ff',self.c['ps5_mac']):
                self.c['portal_mac']=value
                a.atomic_json(path,self.c)
                with self.assertRaises(ValueError):a.config(path)
    def guard(self, event, errors):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); a.atomic_json(root/'restore-state.json',self.s)
            (root/'recovery-required').touch()
            q=MagicMock()
            if isinstance(event,Exception):q.get.side_effect=event
            else:q.get.return_value=event
            with patch.object(n,'Lock') as lock, patch.object(n,'Parent') as owner,patch.object(n,'configure'),patch.object(n,'open_socket'),patch.object(a.signal,'signal'),patch.object(a.threading,'Thread'),patch.object(a.queue,'Queue',return_value=q),patch.object(a,'restore_peer',return_value=errors) as restore:
                timeline=[]
                owner.return_value.stop.side_effect=lambda:timeline.append('stop')
                restore.side_effect=lambda s:timeline.append('repair') or errors
                result=a.guardian(root,123)
                return result,timeline,(root/'recovery-required').exists(),lock.return_value.close.call_args
    def test_guard_eof_repairs(self):
        result,timeline,marker,closed=self.guard(False,[])
        self.assertEqual((result,timeline,marker),(0,['repair'],False))
        self.assertTrue(closed.kwargs['repaired'])
    def test_guard_timeout_stops_before_repair(self):
        result,timeline,marker,_=self.guard(queue.Empty(),[])
        self.assertEqual((result,timeline,marker),(0,['stop','repair'],False))
    def test_failed_recovery_blocks_restart(self):
        result,_,marker,closed=self.guard(False,['down'])
        self.assertEqual(result,1);self.assertTrue(marker);self.assertFalse(closed.kwargs['repaired'])
    def test_no_relay_without_baseline_or_after_failed_recovery(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            with patch.object(n,'state_for') as prepare:
                with self.assertRaises(RuntimeError):a.run(self.c,root)
                (root/'recovery-required').touch()
                with self.assertRaises(RuntimeError):a.run(self.c,root,active=False)
                prepare.assert_not_called()


class LinuxRouteTests(unittest.TestCase):
    def test_gateway_rejected_without_mutation(self):
        with patch.object(n.sys,'platform','linux'),patch.object(n.Path,'read_text',return_value='0'),patch.object(n.subprocess,'check_output',return_value='[{"dev":"eth0","gateway":"192.0.2.1"}]'),patch.object(n,'IFACE','eth0'):
            with self.assertRaises(RuntimeError):n.health()
    def test_direct_route_allowed(self):
        with patch.object(n.sys,'platform','linux'),patch.object(n.Path,'read_text',return_value='0'),patch.object(n.subprocess,'check_output',return_value='[{"dev":"eth0","prefsrc":"192.0.2.30"}]'),patch.object(n,'IFACE','eth0'):
            n.health()
    def test_forwarding_enabled_rejected(self):
        with patch.object(n.sys,'platform','linux'),patch.object(n.Path,'read_text',return_value='1'):
            with self.assertRaises(RuntimeError):n.health()


class AdapterSelectionTests(unittest.TestCase):
    def adapters(self):
        return {1: MagicMock(mac='02:00:00:00:00:01', ip='192.0.2.30', network_name='npcap-one'),
                2: MagicMock(mac='02:00:00:00:00:02', ip='192.0.2.31', network_name='npcap-two')}
    def test_menu_number_stores_device_id(self):
        with patch.object(n.conf, 'ifaces', self.adapters()), patch('builtins.input', return_value='2'), patch('builtins.print'):
            self.assertEqual(a.choose_windows_interface(), 'npcap-two')
    def test_pc_ip_and_invalid_numbers_rejected(self):
        with patch.object(n.conf, 'ifaces', self.adapters()), patch('builtins.print'):
            for entry in ('192.0.2.30', 'npcap-one', '0', '3'):
                with patch('builtins.input', return_value=entry), self.assertRaises(ValueError):
                    a.choose_windows_interface()
    def test_no_adapter_fails_before_prompt(self):
        with patch.object(n.conf, 'ifaces', {}), patch('builtins.input') as prompt:
            with self.assertRaises(RuntimeError): a.choose_windows_interface()
            prompt.assert_not_called()
