"""Offline static/fixture checks. They do NOT claim real Spotube GUI portability."""
import hashlib
import importlib.util
from pathlib import Path
import struct
import tempfile
import unittest
import zipfile

ROOT=Path(__file__).resolve().parent.parent
spec=importlib.util.spec_from_file_location('spotube_build',ROOT/'scripts'/'build.py')
build=importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)

class BuilderTests(unittest.TestCase):
    def test_numeric_semver(self):
        self.assertGreater(build.stable_num('v6.10.1'),build.stable_num('v6.9.99'))
        self.assertIsNone(build.stable_num('v6.0.0-beta.1'))
        self.assertIsNone(build.stable_num('nightly-100'))
        self.assertEqual(build.package_version('v6.0.0'),'6.0.0.0')
    def test_official_source_fixed(self):
        self.assertEqual(build.REPO,'team-spotube/spotube')
        self.assertEqual(build.ASSET,'Spotube-windows-x86_64-setup.exe')
        self.assertEqual(len(build.PINNED_DIGEST['v6.0.0']),64)
    def test_pe_machine_fixture(self):
        with tempfile.TemporaryDirectory() as td:
            f=Path(td)/'dummy.exe'
            blob=bytearray(200)
            blob[:2]=b'MZ';struct.pack_into('<I',blob,0x3C,128)
            blob[128:132]=b'PE\0\0';struct.pack_into('<H',blob,132,0x8664)
            f.write_bytes(blob)
            self.assertEqual(build.pe_machine(f),0x8664)
            blob[128:132]=b'XXXX';f.write_bytes(blob)
            with self.assertRaises(RuntimeError):build.pe_machine(f)
    def test_zip_duplicate_and_traversal_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            f=Path(td)/'bad.zip'
            with zipfile.ZipFile(f,'w') as z:
                z.writestr('SpotubePortable/../escape',b'x')
            with self.assertRaises(RuntimeError): build.verify_zip(f)
    def test_verified_agpl_license_tolerates_utf8_bom_and_whitespace(self):
        # A BOM and blank lines are legal formatting, not evidence of a missing license.
        content = ('GNU AFFERO GENERAL PUBLIC LICENSE\n'
                   ' Version 3, 19 November 2007\n'
                   ' TERMS AND CONDITIONS\n'
                   + ('Full legal license text.\n' * 1200)
                   + ' END OF TERMS AND CONDITIONS\n')
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'LICENSE'
            for raw in (content.encode('utf-8'),
                        b'\xef\xbb\xbf' + content.encode('utf-8'),
                        b'\xef\xbb\xbf\r\n  ' + content.encode('utf-8')):
                path.write_bytes(raw)
                self.assertIn('GNU AFFERO GENERAL PUBLIC LICENSE', build.verify_agpl_license(path))

    def test_license_rejects_wrong_or_truncated_content(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'LICENSE'
            for raw in (b'GNU AFFERO GENERAL PUBLIC LICENSE',
                        (b'MIT License\n' * 5000),
                        (b'GNU GENERAL PUBLIC LICENSE\n' * 5000),
                        (b'\xff' * 20000)):
                path.write_bytes(raw)
                with self.assertRaises(RuntimeError):
                    build.verify_agpl_license(path)

    def test_revision_identity(self):
        self.assertEqual(build.REV, 'b1r2')
        main = (ROOT / '.github' / 'workflows' / 'build-portableapps.yml').read_text(encoding='utf-8')
        self.assertIn('package-revision: b1r2', main)
        repack = (ROOT / '.github' / 'workflows' / 'installer-only.yml').read_text(encoding='utf-8')
        self.assertIn(r'-b1r[12]$', repack)

    def test_official_workflow_contract(self):
        w=(ROOT/'.github'/'workflows'/'build-portableapps.yml').read_text(encoding='utf-8')
        self.assertIn('vhick/Portable-Package-Builder@v1.0.0',w)
        self.assertIn('vhick/portable-release-publisher@v1.1.1',w)
        self.assertIn('engine: custom-nsis',w)
        self.assertIn("dry-run: 'true'",w)
        self.assertIn("dry-run: 'false'",w)
        self.assertIn('continue-on-error: true',w)
        self.assertNotIn('official-tool-url:',w)
    def test_launcher_security_invariants(self):
        t=(ROOT/'launcher'/'SpotubePortable.cpp').read_text(encoding='utf-8')
        self.assertIn('CREATE_SUSPENDED|CREATE_UNICODE_ENVIRONMENT',t)
        self.assertIn('AssignProcessToJobObject',t)
        self.assertIn('safe_tree',t)
        self.assertIn('copy_tree',t)
        self.assertIn('Data',t)
        self.assertNotIn('HKEY_LOCAL_MACHINE',t)
        self.assertNotIn('REG DELETE',t)
        self.assertNotIn('powershell.exe',t.lower())

if __name__=='__main__':unittest.main()
