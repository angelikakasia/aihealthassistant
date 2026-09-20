"""GUI integration checks with temporary credentials; needs Tk/display."""
import tempfile
import tkinter as tk
import unittest
from pathlib import Path
from .security import Security, create_credentials
from .login_ui import LoginWindow


class LoginUITests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        path = Path(self.temp.name)
        create_credentials(path / 'credentials.json', 'caregiver01', '739182')
        self.now = 100
        self.security = Security(path / 'credentials.json', path / 'audit.jsonl',
                                 clock=lambda: self.now)
        self.root = tk.Tk()
        self.root.withdraw()
        self.ui = LoginWindow(self.root, self.security)
        self.addCleanup(self.ui.close)

    def enter(self, pin='739182'):
        self.ui.name.delete(0, 'end')
        self.ui.name.insert(0, 'caregiver01')
        self.ui.pin.insert(0, pin)
        self.ui.login()

    def test_real_login_and_logout(self):
        self.enter()
        self.assertTrue(self.security.is_authenticated())
        self.assertTrue(self.ui.signed_in)
        self.assertEqual(self.ui.pin.get(), '')
        self.ui.logout()
        self.assertFalse(self.security.is_authenticated())
        self.assertFalse(self.ui.signed_in)
        self.assertEqual(self.ui.name.get(), '')

    def test_wrong_pin_cleared(self):
        self.enter('000000')
        self.assertFalse(self.security.is_authenticated())
        self.assertFalse(self.ui.signed_in)
        self.assertEqual(self.ui.pin.get(), '')

    def test_expiry_returns_to_login(self):
        self.enter()
        self.now += 901
        self.root.after_cancel(self.ui.timer)
        self.ui.check_session()
        self.assertFalse(self.ui.signed_in)
        self.assertFalse(self.security.is_authenticated())

    def test_empty_fields_do_not_authenticate(self):
        self.ui.login()
        self.assertFalse(self.security.is_authenticated())
        self.assertIn('Enter your caregiver', self.ui.message.cget('text'))


if __name__ == '__main__':
    unittest.main(verbosity=2)
