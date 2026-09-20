"""Owner isolation, validation and persistent reminder behavior."""
import tempfile
import unittest
from pathlib import Path
from datetime import datetime
from .family_store import FamilySecurity
from .health_store import HealthStore


class HealthTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        path = Path(self.temp.name)
        self.clock = 0
        self.sec = FamilySecurity(path / 'credentials.json', path / 'audit.jsonl', clock=lambda: self.clock)
        self.sec.register('one', '12345678')
        self.sec.register('two', '87654321')
        self.sec.login('one', '12345678')
        self.store = HealthStore(self.sec)
        self.baby = self.store.save_baby('Fictional Baby', '2024-01-01')

    def appointment(self, **changes):
        values = dict(name='Test visit', when='2027-01-10 14:00', status='Scheduled', reminder_minutes=60)
        values.update(changes)
        return values

    def test_medications_and_allergies_persist_and_edit(self):
        for kind, status in [('medication', 'Active'), ('allergy', 'Reported')]:
            rid = self.store.save(self.baby, kind, dict(name='Test record', status=status))
            self.store.save(self.baby, kind, dict(name='Edited record', status=status), rid)
            records = HealthStore(self.sec).records(self.baby, kind)
            self.assertEqual(records[0]['name'], 'Edited record')
            self.assertEqual(len(records), 1)

    def test_due_boundary_and_acknowledgement_persists(self):
        rid = self.store.save(self.baby, 'appointment', self.appointment())
        self.assertEqual(self.store.due(datetime(2027, 1, 10, 12, 59)), [])
        self.assertEqual(len(self.store.due(datetime(2027, 1, 10, 13))), 1)
        self.store.acknowledge(rid)
        self.assertEqual(HealthStore(self.sec).due(datetime(2027, 1, 10, 14)), [])

    def test_missed_reminders_available_after_restart(self):
        self.store.save(self.baby, 'appointment', self.appointment())
        self.assertEqual(len(HealthStore(self.sec).due(datetime(2027, 1, 12))), 1)

    def test_cancelled_completed_and_disabled_do_not_remind(self):
        for values in [self.appointment(status='Cancelled'), self.appointment(status='Completed'),
                       self.appointment(reminder_minutes=-1)]:
            self.store.save(self.baby, 'appointment', values)
        self.assertEqual(self.store.due(datetime(2027, 1, 12)), [])

    def test_rescheduling_rearms_reminder(self):
        rid = self.store.save(self.baby, 'appointment', self.appointment())
        self.store.acknowledge(rid)
        self.store.save(self.baby, 'appointment', self.appointment(when='2027-01-11 14:00'), rid)
        self.assertEqual(self.store.due(datetime(2027, 1, 10, 14)), [])
        self.assertEqual(len(self.store.due(datetime(2027, 1, 11, 13))), 1)

    def test_other_owner_is_denied(self):
        rid = self.store.save(self.baby, 'appointment', self.appointment())
        self.sec.login('two', '87654321')
        self.assertEqual(self.store.due(datetime(2027, 1, 12)), [])
        for action in [lambda: self.store.records(self.baby, 'appointment'),
                       lambda: self.store.save(self.baby, 'appointment', self.appointment(), rid),
                       lambda: self.store.acknowledge(rid)]:
            with self.assertRaises(PermissionError):
                action()

    def test_logged_out_and_expired_access(self):
        self.sec.logout()
        with self.assertRaises(PermissionError):
            self.store.due()
        self.sec.login('one', '12345678')
        self.clock = 901
        with self.assertRaises(PermissionError):
            self.store.records(self.baby, 'medication')

    def test_invalid_input(self):
        for change in [dict(when='2027-02-30 12:00'), dict(when='2027-01-10 25:00'),
                       dict(reminder_minutes=12), dict(status='Unknown'), dict(name='')]:
            with self.assertRaises(ValueError):
                self.store.save(self.baby, 'appointment', self.appointment(**change))

    def test_schedule_is_chronological(self):
        self.store.save(self.baby, 'appointment', self.appointment(when='2027-05-01 09:00'))
        self.store.save(self.baby, 'appointment', self.appointment(when='2027-02-01 09:00'))
        self.assertEqual(self.store.records(self.baby, 'appointment')[0]['when'], '2027-02-01 09:00')

    def test_audit_failure_denies_and_no_health_details_in_log(self):
        self.store.save(self.baby, 'allergy', dict(name='Private substance', reaction='Private reaction', status='Reported'))
        self.assertNotIn('Private substance', self.sec.audit_path.read_text())
        self.assertNotIn('Private reaction', self.sec.audit_path.read_text())
        self.sec.audit_path = Path(self.temp.name)
        with self.assertRaises(PermissionError):
            self.store.due()


if __name__ == '__main__':
    unittest.main(verbosity=2)
