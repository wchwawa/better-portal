import base64
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import ANY, MagicMock, patch
import portal_windows as w
import portal_windows_network as n
from test_probe import fixture


class WindowsTests(unittest.TestCase):
    def test_profiles_share_exact_mutation(self):
        with patch.object(w.core, 'network'), patch.object(w.core, 'PATCH_DELTA'), patch.object(w.core, 'CONFIRM_TARGET'), patch.object(w.core, 'PROFILE_LABEL'):
            for profile, number in [('65', b'65000'), ('100', b'1e+05'), ('200', b'2e+05')]:
                w.set_profile(profile)
                data, plain, stream, pos = fixture()
                out, changed = w.core.mutate(data)
                self.assertTrue(changed)
                self.assertEqual(len(out), len(data))
                decoded = bytes(a ^ b for a, b in zip(base64.b64decode(out[pos:pos+800]), stream))
                self.assertEqual(decoded, plain[:334] + number + plain[339:len(decoded)])

    def test_config_rejects_non_peers(self):
        for ip in ('127.0.0.1', '224.0.0.1', '0.0.0.0', '192.0.2.20'):
            with self.assertRaises(ValueError):
                n.validate_config({'interface': 'Wi-Fi', 'ps5_ip': ip, 'portal_ip': '192.0.2.20'})
        self.assertEqual(n.normal_mac('02:AA:00:00:00:01'), '02:aa:00:00:00:01')
        with self.assertRaises(ValueError): n.normal_mac('ff:ff:ff:ff:ff:ff')

    def test_pc_ip_cannot_be_used_as_adapter(self):
        for address in ('192.0.2.30', '2001:db8::30'):
            with self.assertRaisesRegex(ValueError, 'not the PC IP'):
                n.validate_config({'interface': address, 'ps5_ip': '192.0.2.10', 'portal_ip': '192.0.2.20'})

    def test_forwarding_check_is_readonly_and_fails_closed(self):
        with patch.object(n.subprocess, 'run') as run:
            run.return_value.stdout = '{"InterfaceIndex":12,"Forwarding":0}'
            n.forwarding_disabled(12)
            cmd = run.call_args.args[0][-1]
            self.assertIn('Get-NetIPInterface', cmd)
            self.assertNotIn('Set-', cmd)
            run.return_value.stdout = '{"InterfaceIndex":12,"Forwarding":1}'
            with self.assertRaises(RuntimeError): n.forwarding_disabled(12)

    def test_injection_failure_detected(self):
        sock=MagicMock()
        for result in (-1, 0, 1, 4):
            sock.send.return_value=result
            with self.assertRaises(RuntimeError):n.send_raw(sock,b'abc')
        sock.send.return_value=3
        n.send_raw(sock,b'abc')

    def test_restore_uses_original_peer_mac(self):
        state={'config':{},'own_mac':'02:00:00:00:00:01','ps5_mac':'02:00:00:00:00:02','portal_mac':'02:00:00:00:00:03'}
        sent=[]
        with patch.object(n,'configure'),patch.object(n,'open_socket') as op,patch.object(n,'send_raw',side_effect=lambda sock,frame:sent.append(frame)),patch.object(n.time,'sleep'):
            self.assertEqual(n.restore(state),[])
            self.assertEqual(len(sent),12)
            self.assertEqual(sent[0][n.ARP].hwsrc,state['portal_mac'])
            op.return_value.close.assert_called_once()

    def test_restore_close_failure_is_reported(self):
        state={'config':{}}
        with patch.object(n,'configure'),patch.object(n,'open_socket') as op,patch.object(n,'frames',return_value=[]),patch.object(n.time,'sleep'):
            op.return_value.close.side_effect=OSError('close failure')
            self.assertEqual(n.restore(state),['Adapter close: OSError'])

    def test_baseline_requires_acceptance_and_both_directions(self):
        report={'completed':True,'restoration_errors':[],'counts':{'forwarded_in':2,'forwarded_out':2},'ps5_messages':[{'type':'BANG','key_accepted':1,'version_accepted':1},{'type':'STREAMINFO'}]}
        self.assertTrue(w.baseline_ok(report))
        report['counts']['forwarded_out']=0
        self.assertFalse(w.baseline_ok(report))

    def test_target_without_witness_is_not_success(self):
        report={'mode':'200','completed':True,'restoration_errors':[],'high_target_confirmed':True,'egress_witness':{'all_expected_observed':False}}
        self.assertEqual(w.result_code(report),1)
        report['restoration_errors']=['failed']
        self.assertEqual(w.result_code(report),2)

    def test_runtime_send_failure_restores_before_watchdog_stops(self):
        from contextlib import ExitStack
        with tempfile.TemporaryDirectory() as d, ExitStack() as stack:
            stack.enter_context(patch.object(n,'ROOT',Path(d)))
            stack.enter_context(patch.object(n,'require_windows'))
            stack.enter_context(patch.object(n,'configure',return_value={}))
            state={'config':{},'own_mac':'02:00:00:00:00:01'}
            stack.enter_context(patch.object(n,'preflight',return_value=state))
            stack.enter_context(patch.object(n,'MachineLock'))
            stack.enter_context(patch.object(n,'open_socket'))
            stack.enter_context(patch.object(n,'frames',return_value=[b'test']))
            stack.enter_context(patch.object(n,'send_raw',side_effect=RuntimeError('synthetic injection failure')))
            order=[]
            restore=stack.enter_context(patch.object(n,'restore',side_effect=lambda s,**kw:order.append('restore') or []))
            witness=stack.enter_context(patch.object(w,'Witness'))
            witness.return_value.report.return_value={'all_expected_observed':False}
            stack.enter_context(patch.object(w,'set_profile'))
            stack.enter_context(patch.object(w,'print'))
            stack.enter_context(patch.object(w.subprocess,'CREATE_NEW_PROCESS_GROUP',512,create=True))
            stack.enter_context(patch.object(w.subprocess,'DETACHED_PROCESS',8,create=True))
            child=MagicMock();child.poll.return_value=None
            child.terminate.side_effect=lambda:order.append('stop')
            def spawn(args,**kwargs):
                Path(args[-1]).with_suffix('.ready').write_text('ready')
                return child
            stack.enter_context(patch.object(w.subprocess,'Popen',side_effect=spawn))
            self.assertEqual(w.run('65',baseline=True),1)
            restore.assert_called_once_with(state, service=ANY)
            self.assertEqual(order,['restore','stop'])
            report=json.loads(next(Path(d).glob('experiments/*/report.json')).read_text())
            self.assertIn('synthetic injection failure',report['run_error'])
            self.assertFalse(report['completed'])
