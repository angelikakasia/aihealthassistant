"""Local caregiver accounts and owner-scoped baby/illness records."""
import hashlib
import json
import re
import sqlite3
from contextlib import contextmanager
from datetime import date
from pathlib import Path
from .security import Security, create_credentials


class FamilySecurity(Security):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.accounts = self.credentials_path.parent / 'accounts'

    def _account_path(self, auth_id):
        return self.accounts / (hashlib.sha256(auth_id.encode()).hexdigest() + '.json')

    def register(self, auth_id, pin):
        if not isinstance(auth_id, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', auth_id):
            raise ValueError('Use 1–64 letters, digits, underscores or hyphens for your login.')
        with self._lock:
            if self.credentials_path.exists():
                # Preserve the original single-account file without migrating it.
                try:
                    old = json.loads(self.credentials_path.read_text(encoding='utf-8'))
                    if old['auth_id'] == auth_id:
                        raise FileExistsError('This login already exists. Please sign in.')
                except (KeyError, json.JSONDecodeError):
                    raise ValueError('Existing credentials need repair before creating accounts.')
            self.accounts.mkdir(exist_ok=True)
            create_credentials(self._account_path(auth_id), auth_id, pin)
            self._record('SIGNUP', 'account', 'SUCCESS')

    def _verify(self, auth_id, pin):
        if not isinstance(auth_id, str) or len(auth_id) > 64:
            return False
        original = self.credentials_path
        account = self._account_path(auth_id)
        try:
            if account.is_file():
                self.credentials_path = account
            return super()._verify(auth_id, pin)
        finally:
            self.credentials_path = original


class FamilyStore:
    """Authorization checked on every operation, including writes."""
    def __init__(self, security, path=None):
        self.security = security
        self.path = Path(path) if path else security.credentials_path.parent / 'family.sqlite3'

    @contextmanager
    def _connect(self):
        db = sqlite3.connect(self.path)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA foreign_keys = ON')
        db.executescript('''
            CREATE TABLE IF NOT EXISTS babies (
                id INTEGER PRIMARY KEY, owner TEXT NOT NULL,
                name TEXT NOT NULL, dob TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS illnesses (
                id INTEGER PRIMARY KEY, baby_id INTEGER NOT NULL REFERENCES babies(id),
                started TEXT NOT NULL, ended TEXT NOT NULL DEFAULT '',
                title TEXT NOT NULL, symptoms TEXT NOT NULL, notes TEXT NOT NULL);
        ''')
        try:
            with db:
                yield db
        finally:
            db.close()

    def _actor(self, action):
        if not self.security.is_authenticated():
            self.security._record(action, 'family_records', 'DENY')
            raise PermissionError('Your session ended. Please sign in again.')
        if not self.security._record(action, 'family_records', 'ALLOW'):
            raise PermissionError('The audit log is unavailable. Records were not accessed.')
        return self.security._actor

    @staticmethod
    def _date(value, label):
        try:
            if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
                raise ValueError
            parsed = date.fromisoformat(value)
            if parsed > date.today():
                raise ValueError
            return parsed
        except (TypeError, ValueError):
            raise ValueError(f'{label} must be a real date, YYYY-MM-DD, no later than today.')

    @staticmethod
    def _text(value, label, maximum, required=True):
        value = value.strip()
        if (required and not value) or len(value) > maximum:
            raise ValueError(f'{label}: enter {"1" if required else "0"}–{maximum} characters.')
        return value

    def babies(self):
        with self.security._lock:
            owner = self._actor('FAMILY_READ')
            with self._connect() as db:
                return [dict(r) for r in db.execute(
                    'SELECT id,name,dob FROM babies WHERE owner=? ORDER BY name,id', (owner,))]

    def save_baby(self, name, dob, baby_id=None):
        with self.security._lock:
            owner = self._actor('FAMILY_WRITE')
            name = self._text(name, 'Baby name', 80)
            self._date(dob, 'Date of birth')
            with self._connect() as db:
                if baby_id is None:
                    return db.execute('INSERT INTO babies(owner,name,dob) VALUES(?,?,?)',
                                      (owner, name, dob)).lastrowid
                if not db.execute('SELECT id FROM babies WHERE id=? AND owner=?', (baby_id, owner)).fetchone():
                    raise PermissionError('Record unavailable.')
                if db.execute('SELECT id FROM illnesses WHERE baby_id=? AND started<?', (baby_id, dob)).fetchone():
                    raise ValueError('Birth date cannot be after an existing illness entry.')
                db.execute('UPDATE babies SET name=?,dob=? WHERE id=? AND owner=?', (name, dob, baby_id, owner))
                return baby_id

    def illnesses(self, baby_id):
        with self.security._lock:
            owner = self._actor('FAMILY_READ')
            with self._connect() as db:
                if not db.execute('SELECT id FROM babies WHERE id=? AND owner=?', (baby_id, owner)).fetchone():
                    raise PermissionError('Record unavailable.')
                return [dict(r) for r in db.execute(
                    'SELECT * FROM illnesses WHERE baby_id=? ORDER BY started DESC,id DESC', (baby_id,))]

    def save_illness(self, baby_id, started, ended, title, symptoms, notes, entry_id=None):
        with self.security._lock:
            owner = self._actor('FAMILY_WRITE')
            start = self._date(started, 'Start date')
            if ended and self._date(ended, 'End date') < start:
                raise ValueError('End date cannot be before start date.')
            title = self._text(title, 'Illness or concern', 120)
            symptoms = self._text(symptoms, 'Symptoms', 2000, False)
            notes = self._text(notes, 'Notes', 4000, False)
            with self._connect() as db:
                baby = db.execute('SELECT dob FROM babies WHERE id=? AND owner=?', (baby_id, owner)).fetchone()
                if not baby:
                    raise PermissionError('Record unavailable.')
                if started < baby['dob']:
                    raise ValueError('Start date cannot be before the baby’s birth date.')
                values = (started, ended, title, symptoms, notes)
                if entry_id is None:
                    return db.execute('INSERT INTO illnesses(started,ended,title,symptoms,notes,baby_id) VALUES(?,?,?,?,?,?)',
                                      (*values, baby_id)).lastrowid
                cursor = db.execute('UPDATE illnesses SET started=?,ended=?,title=?,symptoms=?,notes=? WHERE id=? AND baby_id=?',
                                    (*values, entry_id, baby_id))
                if not cursor.rowcount:
                    raise PermissionError('Record unavailable.')
                return entry_id
