"""Security demonstration with temporary credentials and simulated operations."""
import json
import secrets
import tempfile
from pathlib import Path
from .security import Security, create_credentials


def main():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        pin = ''.join(secrets.choice('0123456789') for _ in range(8))
        create_credentials(root / 'credentials.json', 'caregiver01', pin)
        sec = Security(root / 'credentials.json', root / 'audit.jsonl')
        loaded, sent = [], []

        def fake_loader():
            loaded.append(True)
            return {'type': 'DEMO_UNSAFE_ZONE_ENTRY', 'test_data': True}

        def read():
            try:
                print('Protected read:', sec.read_protected('monitoring_events', fake_loader, for_ai=True))
            except PermissionError:
                print('Protected read: DENY')

        def command(value):
            try:
                sec.execute_command(value, sent.append)
                print(value + ': ALLOW (simulated sender only)')
            except PermissionError:
                print(value + ': DENY')

        print('ANGELIKA SECURITY DEMO — fake data, no LLM, no hardware\n')
        read()
        command('FWD')
        print('Data loads before login:', len(loaded))
        print('Commands sent before login:', len(sent))
        print('Login:', 'SUCCESS' if sec.login('caregiver01', pin) else 'FAILED')
        read()
        command('FWD')
        command('SPIN_FAST')
        sec.logout()
        print('Logged out')
        read()
        command('FWD')
        command('STOP')
        print('\nAudit evidence:')
        for line in sec.audit_path.read_text().splitlines():
            event = json.loads(line)
            print(event['actor'], event['action'], event['resource'], event['result'])
        print('\nTemporary credentials and logs are removed when this demo exits.')


if __name__ == '__main__':
    main()
