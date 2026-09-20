"""Manual medication/allergy records and local appointment reminders."""
import json
from datetime import datetime, timedelta
from .family_store import FamilyStore

# key, visible label, required, maximum length
FIELDS = {
    'medication': [('name', 'Medication name', True, 120),
                   ('dose', 'Dose / instructions (as prescribed)', False, 300),
                   ('schedule', 'Schedule (your notes)', False, 300),
                   ('prescriber', 'Prescriber', False, 120),
                   ('notes', 'Notes', False, 2000)],
    'allergy': [('name', 'Allergen / substance', True, 120),
                ('reaction', 'Reaction observed', False, 1000),
                ('instructions', 'Clinician instructions', False, 2000),
                ('notes', 'Notes', False, 2000)],
    'appointment': [('name', 'Appointment / reason', True, 120),
                    ('when', 'Date and time (YYYY-MM-DD HH:MM, local time)', True, 16),
                    ('provider', 'Clinician / clinic', False, 200),
                    ('location', 'Location', False, 300),
                    ('notes', 'Notes', False, 2000)]}
STATUSES = {'medication': ('Active', 'Stopped'), 'allergy': ('Reported', 'Confirmed', 'Resolved'),
            'appointment': ('Scheduled', 'Completed', 'Cancelled')}
REMINDERS = {'No reminder': -1, 'At appointment time': 0, '15 minutes before': 15,
             '1 hour before': 60, '1 day before': 1440}


class HealthStore(FamilyStore):
    @staticmethod
    def table(db):
        db.execute('''CREATE TABLE IF NOT EXISTS health_items (
            id INTEGER PRIMARY KEY, baby_id INTEGER NOT NULL REFERENCES babies(id),
            kind TEXT NOT NULL, payload TEXT NOT NULL, acknowledged INTEGER NOT NULL DEFAULT 0)''')

    @staticmethod
    def time(value):
        try:
            result = datetime.strptime(value, '%Y-%m-%d %H:%M')
            if result.strftime('%Y-%m-%d %H:%M') != value:
                raise ValueError
            return result
        except (ValueError, TypeError):
            raise ValueError('Enter the appointment date/time as YYYY-MM-DD HH:MM (24-hour local time).')

    def _owned(self, db, baby_id, owner):
        if not db.execute('SELECT id FROM babies WHERE id=? AND owner=?', (baby_id, owner)).fetchone():
            raise PermissionError('Record unavailable.')

    def records(self, baby_id, kind):
        if kind not in FIELDS:
            raise ValueError('Unknown record type.')
        with self.security._lock:
            owner = self._actor('HEALTH_READ')
            with self._connect() as db:
                self.table(db)
                self._owned(db, baby_id, owner)
                records = [dict(id=r['id'], **json.loads(r['payload'])) for r in db.execute(
                    'SELECT id,payload FROM health_items WHERE baby_id=? AND kind=?', (baby_id, kind))]
                return sorted(records, key=lambda r: r.get('when', r['name']))

    def save(self, baby_id, kind, values, record_id=None):
        if kind not in FIELDS:
            raise ValueError('Unknown record type.')
        with self.security._lock:
            owner = self._actor('HEALTH_WRITE')
            clean = {key: self._text(values.get(key, ''), label, maximum, required)
                     for key, label, required, maximum in FIELDS[kind]}
            if values.get('status') not in STATUSES[kind]:
                raise ValueError('Choose a valid status.')
            clean['status'] = values['status']
            if kind == 'appointment':
                self.time(clean['when'])
                lead = values.get('reminder_minutes', 60)
                if type(lead) is not int or lead not in REMINDERS.values():
                    raise ValueError('Choose a reminder time.')
                clean['reminder_minutes'] = lead
            with self._connect() as db:
                self.table(db)
                self._owned(db, baby_id, owner)
                payload = json.dumps(clean)
                if record_id is None:
                    return db.execute('INSERT INTO health_items(baby_id,kind,payload) VALUES(?,?,?)',
                                      (baby_id, kind, payload)).lastrowid
                old = db.execute('SELECT payload,acknowledged FROM health_items WHERE id=? AND baby_id=? AND kind=?',
                                 (record_id, baby_id, kind)).fetchone()
                if not old:
                    raise PermissionError('Record unavailable.')
                previous = json.loads(old['payload'])
                reset = any(previous.get(k) != clean.get(k) for k in ('when', 'status', 'reminder_minutes'))
                db.execute('UPDATE health_items SET payload=?,acknowledged=? WHERE id=?',
                           (payload, 0 if reset else old['acknowledged'], record_id))
                return record_id

    def due(self, now=None):
        now = now or datetime.now()
        with self.security._lock:
            owner = self._actor('REMINDER_CHECK')
            with self._connect() as db:
                self.table(db)
                due = []
                for row in db.execute('''SELECT h.id,h.payload,b.name baby_name FROM health_items h
                    JOIN babies b ON b.id=h.baby_id WHERE b.owner=? AND h.kind='appointment' AND h.acknowledged=0''', (owner,)):
                    data = json.loads(row['payload'])
                    lead = data['reminder_minutes']
                    if data['status'] == 'Scheduled' and lead >= 0 and now >= self.time(data['when']) - timedelta(minutes=lead):
                        due.append(dict(id=row['id'], baby_name=row['baby_name'], **data))
                return sorted(due, key=lambda r: r['when'])

    def acknowledge(self, record_id):
        with self.security._lock:
            owner = self._actor('REMINDER_ACK')
            with self._connect() as db:
                self.table(db)
                result = db.execute('''UPDATE health_items SET acknowledged=1 WHERE id=? AND kind='appointment'
                    AND baby_id IN (SELECT id FROM babies WHERE owner=?)''', (record_id, owner))
                if not result.rowcount:
                    raise PermissionError('Record unavailable.')
