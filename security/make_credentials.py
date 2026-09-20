"""Run from the project root: python -m security.make_credentials"""
from getpass import getpass
from .security import BASE, create_credentials


def main():
    auth_id = input('Test caregiver ID [caregiver01]: ').strip() or 'caregiver01'
    pin = getpass('Enter a fake test PIN (6-12 digits): ')
    confirm = getpass('Confirm test PIN: ')
    if pin != confirm:
        print('PINs do not match. Nothing saved.')
        return 1
    try:
        create_credentials(BASE / 'credentials.json', auth_id, pin)
    except (ValueError, OSError) as exc:
        print(f'Credentials were not created: {exc}')
        return 1
    print('Created local security/credentials.json. Keep it out of GitHub.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
