"""Local, single-caregiver student prototype. No AI or hardware dependencies."""
import hashlib
import hmac
import json
import re
import secrets
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

ITERATIONS = 600_000
BASE = Path(__file__).resolve().parent
RESOURCES = frozenset({'monitoring_events', 'safety_alerts', 'event_history'})
COMMANDS = frozenset({'FWD', 'BACK', 'LEFT', 'RIGHT', 'STOP'})


def create_credentials(path, auth_id, pin):
    """Exclusively create a credential file; never silently overwrite it."""
    if not isinstance(auth_id, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', auth_id):
        raise ValueError('Authentication ID must use 1-64 letters, digits, _ or -.')
    if not isinstance(pin, str) or not re.fullmatch(r'[0-9]{6,12}', pin):
        raise ValueError('Use a test PIN of 6-12 digits.')
    salt = secrets.token_bytes(32)
    digest = hashlib.pbkdf2_hmac('sha256', pin.encode(), salt, ITERATIONS)
    record = {'version': 1, 'auth_id': auth_id, 'algorithm': 'pbkdf2_sha256',
              'iterations': ITERATIONS, 'salt': salt.hex(), 'hash': digest.hex()}
    with Path(path).open('x', encoding='utf-8') as stream:
        json.dump(record, stream, indent=2)
        stream.write('\n')


class Security:
    """One trusted local application session, not a multi-user web session store.

    Trusted application code owns this object. Never expose login state, callbacks,
    audit_event, or filesystem access as arbitrary LLM tools.
    """
    def __init__(self, credentials_path=BASE / 'credentials.json',
                 audit_path=BASE / 'audit_log.jsonl', *, session_seconds=900,
                 max_failures=5, lockout_seconds=30, clock=time.monotonic):
        if session_seconds <= 0 or max_failures < 1 or lockout_seconds <= 0:
            raise ValueError('Security timing and attempt limits must be positive.')
        self.credentials_path = Path(credentials_path)
        self.audit_path = Path(audit_path)
        self.session_seconds = session_seconds
        self.max_failures = max_failures
        self.lockout_seconds = lockout_seconds
        self._clock = clock
        self._actor = None
        self._expires = 0
        self._failures = 0
        self._blocked_until = 0
        self._lock = threading.RLock()

    def _active(self):
        if self._actor is not None and self._clock() >= self._expires:
            self._actor = None
            self._expires = 0
        return self._actor is not None

    def audit_event(self, action, resource, result):
        """Trusted code only. Do not pass PINs, prompts, tokens or child data here."""
        with self._lock:
            self._active()
            if not all(isinstance(x, str) and len(x) <= 64
                       for x in (action, resource, result)):
                raise ValueError('Audit fields must be short strings.')
            event = {'timestamp': datetime.now(timezone.utc).isoformat(),
                     'actor': self._actor or 'anonymous', 'action': action,
                     'resource': resource, 'result': result}
            with self.audit_path.open('a', encoding='utf-8') as stream:
                stream.write(json.dumps(event) + '\n')

    def _record(self, action, resource, result):
        try:
            self.audit_event(action, resource, result)
            return True
        except (OSError, ValueError):
            return False

    def _verify(self, auth_id, pin):
        # Bound input and stored parameters before running the expensive KDF.
        if not isinstance(auth_id, str) or not isinstance(pin, str):
            return False
        if len(auth_id) > 64 or not re.fullmatch(r'[0-9]{6,12}', pin):
            return False
        try:
            if self.credentials_path.stat().st_size > 4096:
                return False
            data = json.loads(self.credentials_path.read_text(encoding='utf-8'))
            if not isinstance(data, dict):
                return False
            if data['version'] != 1 or data['algorithm'] != 'pbkdf2_sha256':
                return False
            iterations = data['iterations']
            if type(iterations) is not int or not ITERATIONS <= iterations <= 2_000_000:
                return False
            stored_id = data['auth_id']
            if not isinstance(stored_id, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', stored_id):
                return False
            salt = bytes.fromhex(data['salt'])
            expected = bytes.fromhex(data['hash'])
            if len(salt) != 32 or len(expected) != 32:
                return False
            actual = hashlib.pbkdf2_hmac('sha256', pin.encode(), salt, iterations)
            id_matches = hmac.compare_digest(auth_id.encode(), stored_id.encode())
            hash_matches = hmac.compare_digest(actual, expected)
            return id_matches and hash_matches
        except (OSError, ValueError, KeyError, TypeError):
            return False

    def login(self, auth_id, pin):
        with self._lock:
            # A failed re-login cannot retain an earlier authenticated session.
            self._actor = None
            self._expires = 0
            if self._clock() < self._blocked_until:
                self._record('LOGIN', 'session', 'FAILED')
                return False
            if not self._verify(auth_id, pin):
                self._failures += 1
                if self._failures >= self.max_failures:
                    self._blocked_until = self._clock() + self.lockout_seconds
                    self._failures = 0
                self._record('LOGIN', 'session', 'FAILED')
                return False
            self._actor = auth_id
            self._expires = self._clock() + self.session_seconds
            if not self._record('LOGIN', 'session', 'SUCCESS'):
                self._actor = None
                self._expires = 0
                return False
            self._failures = 0
            return True

    def logout(self):
        with self._lock:
            try:
                return self._record('LOGOUT', 'session', 'SUCCESS')
            finally:
                self._actor = None
                self._expires = 0

    def is_authenticated(self):
        with self._lock:
            return self._active()

    def can_read(self, resource, *, for_ai=False):
        with self._lock:
            known = isinstance(resource, str) and resource in RESOURCES
            allowed = known and self._active()
            logged = self._record('AI_READ' if for_ai else 'READ',
                                  resource if known else 'unknown',
                                  'ALLOW' if allowed else 'DENY')
            return bool(allowed and logged)

    def can_command(self, command):
        with self._lock:
            known = isinstance(command, str) and command in COMMANDS
            stop = known and command == 'STOP'
            allowed = known and (stop or self._active())
            logged = self._record('ROBOT_COMMAND', command if known else 'unknown',
                                  'ALLOW' if allowed else 'DENY')
            # STOP permission survives login and audit failures. Actual stopping
            # must be implemented by the team's robot interface and controller.
            return bool(stop or (allowed and logged))

    def read_protected(self, resource, loader, *, for_ai=False):
        """Invoke a trusted data loader only after authorization succeeds."""
        with self._lock:
            if not self.can_read(resource, for_ai=for_ai):
                raise PermissionError('Access denied.')
            return loader()

    def execute_command(self, command, sender):
        """Invoke a trusted sender only after command authorization succeeds."""
        with self._lock:
            if not self.can_command(command):
                raise PermissionError('Command denied.')
            return sender(command)


_default = Security()
login = _default.login
logout = _default.logout
is_authenticated = _default.is_authenticated
can_read = _default.can_read
can_command = _default.can_command
audit_event = _default.audit_event
read_protected = _default.read_protected
execute_command = _default.execute_command
