"""Real storage and authorization tests, using temporary fictional records."""
import tempfile
import unittest
from pathlib import Path
from .family_store import FamilySecurity, FamilyStore
from .security import create_credentials


class FamilyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.now = 0
        self.sec = FamilySecurity(self.root / 'credentials.json', self.root / 'audit.jsonl', clock=lambda: self.now)
        self.store = FamilyStore(self.sec)
        self.sec.register('first', '12345678')
        self.sec.register('second', '87654321')
        self.assertTrue(self.sec.login('first', '12345678'))

    def test_persistence_and_editing(self):
        baby = self.store.save_baby('Test Baby', '2024-01-01')
        entry = self.store.save_illness(baby, '2024-02-01', '', 'Caregiver note', 'Cough', 'Test only')
        self.store.save_illness(baby, '2024-02-01', '2024-02-03', 'Updated note', 'Cough', 'Ended', entry)
        again = FamilyStore(self.sec)
        self.assertEqual(again.babies()[0]['name'], 'Test Baby')
        self.assertEqual(again.illnesses(baby)[0]['ended'], '2024-02-03')
        self.store.save_baby('New name', '2024-01-01', baby)
        self.assertEqual(again.babies()[0]['name'], 'New name')

    def test_other_caregiver_cannot_access(self):
        baby = self.store.save_baby('Private Baby', '2024-01-01')
        entry = self.store.save_illness(baby, '2024-02-01', '', 'Private note', '', '')
        self.sec.logout()
        self.assertTrue(self.sec.login('second', '87654321'))
        self.assertEqual(self.store.babies(), [])
        for action in (lambda: self.store.illnesses(baby),
                       lambda: self.store.save_baby('Changed', '2024-01-01', baby),
                       lambda: self.store.save_illness(baby, '2024-02-01', '', 'Changed', '', '', entry)):
            with self.assertRaises(PermissionError):
                action()

    def test_logout_and_expiry(self):
        self.sec.logout()
        with self.assertRaises(PermissionError):
            self.store.babies()
        with self.assertRaises(PermissionError):
            self.store.save_baby('Test', '2024-01-01')
        self.sec.login('first', '12345678')
        self.now = 901
        with self.assertRaises(PermissionError):
            self.store.babies()

    def test_date_validation(self):
        for value in ('wrong', '2024-02-30', '2999-01-01'):
            with self.assertRaises(ValueError):
                self.store.save_baby('Test', value)
        baby = self.store.save_baby('Test', '2024-01-01')
        for start, end in [('2023-01-01', ''), ('2024-02-01', '2024-01-01')]:
            with self.assertRaises(ValueError):
                self.store.save_illness(baby, start, end, 'Note', '', '')

    def test_existing_login_preserved_and_duplicates_denied(self):
        create_credentials(self.sec.credentials_path, 'Angelika', '11223344')
        self.assertTrue(self.sec.login('Angelika', '11223344'))
        with self.assertRaises(FileExistsError):
            self.sec.register('Angelika', '88776655')
        with self.assertRaises(FileExistsError):
            self.sec.register('first', '88776655')
        self.assertFalse(self.sec.login('first', '88776655'))

    def test_missing_audit_denies_records(self):
        self.sec.audit_path = self.root
        with self.assertRaises(PermissionError):
            self.store.save_baby('Test', '2024-01-01')
        self.assertFalse(self.store.path.exists())

    def test_private_content_not_logged(self):
        baby = self.store.save_baby('Private Baby', '2024-01-01')
        self.store.save_illness(baby, '2024-02-01', '', 'Private illness', 'Private symptom', 'Private note')
        log = self.sec.audit_path.read_text()
        for value in ('Private Baby', 'Private illness', 'Private symptom', '12345678'):
            self.assertNotIn(value, log)


if __name__ == '__main__':
    unittest.main(verbosity=2)
