# Angelika: security and privacy

This folder implements Angelika's standalone component. It contains no computer
vision, LLM integration, serial implementation, or Arduino/hardware code.
Only Python's standard library is required (Python 3.10 or newer).

## Open the caregiver login window

Double-click **Open FROGI.bat** in the repository folder, or run:

```powershell
cd "C:\Users\angel\Documents\Codex\2026-09-20\x20-re\work\aihealthassistant"
py -3 -m security.login_ui
```

Enter your actual caregiver ID (for example, `Angelika`) and the PIN you created,
then select **Hop in**. The window verifies `security/credentials.json` using the
existing security backend. **Log out** clears the session. Closing the window
also logs out; after 15 minutes it automatically returns to the login form.
The PIN field is hidden and cleared after each submitted attempt.

This is a caregiver-facing login window with a friendly frog illustration.
It displays real authentication status; it does not display monitoring data or
operate hardware. Its session belongs to this application process and does not
sign a separate AI application into the account. Integration remains pending.
Create credentials once with `py -3 -m security.make_credentials` if needed.
The window requires Python's standard Tkinter/Tcl/Tk component (included with
normal python.org Windows installations). No pip packages are required.

To run the four additional window integration checks on a computer with Tk:

```powershell
py -3 -m security.login_ui_tests
```

## What each file does

Paths below are relative to the repository root.

| File | Responsibility and use |
| --- | --- |
| `security/security.py` | Implements real credential verification, login/logout, session expiry, failed-login cooldown, data-access checks, command authorization, and audit logging. Provides wrappers that authorize before calling a data loader or command sender. |
| `security/login_ui.py` | Frog-themed desktop login/logout window connected to actual saved credentials and an in-memory security session. |
| `security/login_ui_tests.py` | Four GUI integration tests for real credential verification, logout, rejected PINs, empty input, and session expiry using temporary accounts. |
| `Open FROGI.bat` | Windows double-click launcher that opens the login window from the correct repository directory. |
| `security/make_credentials.py` | Prompts for a caregiver ID and PIN, generates a random salt, hashes the PIN, and creates the local credential file. It never saves the original PIN and refuses to overwrite existing credentials. |
| `security/security_tests.py` | Runs 18 automated security tests using isolated temporary credentials and mock operations. Checks authentication, permissions, logout, expiry, cooldown, audit behavior, STOP, and credential protection. |
| `security/demo.py` | Demonstrates security decisions using temporary credentials, a fake monitoring event, and a simulated command sender. It does not connect to a camera, LLM, or robot. |
| `security/__init__.py` | Exposes the security interface so the application can use imports such as `from security import login`. |
| `security/README.md` | Explains this component, setup, useful commands, security design, and integration responsibilities. |
| `.gitignore` | Excludes generated credentials, audit logs, `.env`, Python cache files, and the local virtual environment from ordinary Git additions. |
| `security/credentials.json` — local only | Stores one caregiver's authentication ID, algorithm, iteration count, salt, and PIN hash. This is the current file-based credential store, not a database server. |
| `security/audit_log.jsonl` — local only | Records real security decisions, one JSON event per line. Created when security actions are recorded. Contains no PINs or monitoring-event content. |

The login backend is real. Fake data is used only in the isolated tests and demo.
The current setup script says "test" because this is a student prototype; the
credentials it creates are actually verified by `login()`. There is currently no
account-management interface or multi-account database. A graphical login/logout
window is available through `security.login_ui`.

## How the PIN is hashed and salted

1. `make_credentials.py` collects the PIN with `getpass`, so characters are not
   displayed in the terminal. It checks that the PIN contains 6–12 digits and
   that the confirmation matches.
2. `create_credentials()` in `security.py` generates a fresh 32-byte random salt
   using `secrets.token_bytes(32)`.
3. It computes the hash with
   `hashlib.pbkdf2_hmac('sha256', pin.encode(), salt, 600_000)`.
   PBKDF2 repeats computational work to make each guessing attempt more expensive.
4. It stores the salt and 32-byte hash as hexadecimal strings, together with
   `auth_id`, `version`, `algorithm`, and `iterations`, in `credentials.json`.
   It does not store the plaintext PIN.
5. At login, it loads the saved salt and iteration count and hashes the entered
   PIN using those same parameters. It compares the result with the stored hash
   using `hmac.compare_digest`. A new salt is not generated during verification.

The salt is not a password and does not need to be secret. Different random salts
make the same PIN produce different hashes. Hashing is one-way, not reversible
encryption: opening the credential file will show the ID, salt, and hash, but
cannot show the original PIN. Keep the complete credential file private because
someone with its hash can attempt offline guesses.

## Useful Windows PowerShell commands

Always start in the repository folder. Running these Python commands from
`C:\Windows\system32` produces `No module named 'security'`.
For Angelika's current local checkout:

```powershell
cd "C:\Users\angel\Documents\Codex\2026-09-20\x20-re\work\aihealthassistant"
```

On another computer, replace that path with your own repository folder.

### Create credentials once

```powershell
py -3 -m security.make_credentials
```

Choose a caregiver ID and PIN privately. IDs are case-sensitive: `Angelika` and
`angelika` are different. If credentials already exist, use them to log in; the
setup command deliberately refuses to replace them. No PIN recovery or reset
interface is implemented yet.

### Check a real login

```powershell
py -3 -c "from security import login; from getpass import getpass; print('LOGIN SUCCESSFUL' if login(input('Login: '), getpass('PIN: ')) else 'LOGIN FAILED')"
```

This verifies the entered ID and PIN against your actual local credential file
and records the result. The PIN is hidden while you type. This command exits
after the check, so its session ends immediately; it does not sign you into
GitHub or authenticate a separate running application.

### Keep a session open and check permissions

Start Python interactively:

```powershell
py -3
```

Then enter these lines at the Python `>>>` prompt, one at a time. The login
line prompts for your actual credentials; do not put your PIN into code.

```python
from security import login, logout, is_authenticated, can_read, can_command
from getpass import getpass
login(input('Login: '), getpass('PIN: '))
is_authenticated()
can_read('monitoring_events')
can_read('safety_alerts')
can_read('event_history', for_ai=True)
can_command('FWD')
can_command('SPIN_FAST')
logout()
is_authenticated()
can_read('monitoring_events')
can_command('FWD')
can_command('STOP')
exit()
```

After a successful login, approved reads and `FWD` return `True` until logout or
expiry. `SPIN_FAST` returns `False`. After logout, authentication, protected reads,
and `FWD` return `False`; `STOP` remains allowed. These command checks authorize
only: they do not move or stop physical hardware. Session state and the login
cooldown belong to this Python process and do not persist after it exits.

### Inspect your local credential store

```powershell
notepad .\security\credentials.json
```

Use this to see the saved login ID, salt, hash, and iteration count. The PIN is
not present. Inspect without changing the values, and do not publish the file.

### Inspect login and authorization history

```powershell
notepad .\security\audit_log.jsonl
Get-Content .\security\audit_log.jsonl -Tail 10
```

The log exists after a security action has been recorded. Events contain
`timestamp`, `actor`, `action`, `resource`, and `result`. A successful login uses
the authenticated caregiver ID; failed logins use `anonymous`.

### Run automated checks and the isolated demo

```powershell
py -3 -m security.security_tests
py -3 -m security.demo
```

Expected test result: `18 PASS | 0 FAIL`. These commands use temporary files and
do not replace your own credentials or log you into a separate application.

### Check GitHub upload protection

```powershell
git branch --show-current
git status --short
git check-ignore security/credentials.json security/audit_log.jsonl
git ls-files -- security/credentials.json security/audit_log.jsonl
```

Your development branch should be `angelika-security`. `git check-ignore` should
print both local file paths; `git ls-files` should print nothing for them. Code,
tests, and documentation belong in GitHub; generated credentials and runtime logs
stay local. If Git reports dubious ownership for the Codex-created checkout,
use a one-command exception scoped to this exact folder, for example:

```powershell
git -c safe.directory=C:/Users/angel/Documents/Codex/2026-09-20/x20-re/work/aihealthassistant -C "C:\Users\angel\Documents\Codex\2026-09-20\x20-re\work\aihealthassistant" status --short
```

Use that same prefix with `push origin angelika-security` instead of
`status --short` when uploading an already-created commit from this checkout.

## Run from the repository root

```powershell
python -m security.security_tests
python -m security.demo
python -m security.make_credentials
```

On Windows, `py -3` can replace `python` when Python is installed through the
Python launcher. Tests and the demonstration use temporary fake credentials and
remove their files when finished. The demo does not require credential setup.
The credential setup command prompts privately for a 6–12 digit test PIN and
writes `security/credentials.json`. It refuses to overwrite an existing file.
Do not commit that generated file or `security/audit_log.jsonl`.

## Implemented controls

- PBKDF2-HMAC-SHA256, 600,000 iterations, and a random 32-byte salt.
- Constant-time hash comparison; no plaintext PIN storage.
- Login, logout, and one in-memory application session with a 15-minute absolute expiry.
- Five failed attempts trigger a 30-second in-process cooldown.
- The same Boolean failure response for wrong PINs and unknown users.
- Exact allowlists for resources and movement commands; unknown values are denied.
- Append-only application audit writes with UTC timestamp, actor, action, resource, result.
- Authorization wrappers that check permissions before calling a data loader or sender.
- Failed audit writes deny login, protected reads, and movement authorization.
- STOP remains authorized without login, including when the audit file is unavailable.

Protected resources: `monitoring_events`, `safety_alerts`, `event_history`.
Commands: `FWD`, `BACK`, `LEFT`, `RIGHT`, `STOP`.
Optional knowledge/configuration resources are not enabled.

## Interface for team integration

```python
from security import (
    login, logout, is_authenticated, can_read, can_command,
    read_protected, execute_command,
)

# Collect credentials through trusted application input, never through the LLM.
# login(auth_id, pin) -> bool
# logout() -> bool indicating whether its audit write succeeded; always clears login
# is_authenticated() -> bool
# can_read(resource, for_ai=False) -> bool
# can_command(command) -> bool
```

Prefer the following wrappers at the actual point of retrieval or sending.
The functions `load_actual_events`, `call_llm`, and `send_actual_command` below
are integration placeholders for the team's existing implementations, not part
of Angelika's deliverable.

```python
try:
    context = read_protected(
        "monitoring_events", load_actual_events, for_ai=True
    )
except PermissionError:
    response = "Access denied."
else:
    response = call_llm(context)

try:
    execute_command("FWD", send_actual_command)
except PermissionError:
    response = "Command denied."
```

The caller must pass a callable loader, not data already retrieved. The wrapper
never calls that loader on denial. Treat every private data source and actual
command sender as protected, regardless of question wording or AI output.
The LLM cannot set session state, supply credentials, select arbitrary callbacks,
or directly call loaders, filesystem operations, raw serial tools, or audit APIs.
Audit events record authorization decisions, not proof of successful retrieval
or physical execution. Callback failures propagate to the trusted application.

The module-level interface shares ONE local session. Applications requiring
multiple concurrent caregivers must implement per-user session binding before
using this in a web service. A `Security` instance permits isolated testing.

Logout and expiry block future access. The integrating application must also
clear private cached responses and LLM conversation context when a caregiver
logs out or a session expires. This module cannot erase data already released
to another component. Cloud-provider data handling remains an integration decision.

Immediate automatic safety alerts are independent of caregiver access to their
history. Do not route automatic LEDs/buzzers through the caregiver movement
allowlist. The hardware stop and obstacle override remain Jeremiah's work.
STOP authorization here is not proof of a functioning emergency-stop mechanism.

## Tests and demonstration

`security_tests.py` includes the ten requested security scenarios plus eight
additional cases for invalid inputs, session expiry, cooldown, credential errors,
audit failures, STOP, and salt generation. It returns a nonzero exit status on
failure. The AI boundary test uses mock callbacks; it does not evaluate an actual
language model, paraphrase classifier, hallucination behavior, or robot.

`demo.py` demonstrates denied read/movement, successful login, approved read and
simulated movement, unknown-command denial, logout protection, STOP, and audit
evidence. It uses a random temporary test PIN without displaying it.

## Remaining team integration checks

Angelika supplies and tests these security functions. Aneela connects every
private retrieval and caregiver movement action to them. Together, verify that
denied requests never reach actual LLM context or serial transmission, including
alternate wording and prompt-injection attempts. Check private context cleanup
after logout and expiry. Jeremiah demonstrates actual stopping and obstacle
override, including when the LLM is unavailable. These end-to-end checks cannot
be claimed complete from this standalone test suite.

## Prototype limits

Hashing is not encryption of monitoring data. A short PIN can be guessed offline
if its hash is stolen. Use test credentials only and protect the local OS account.
Git ignore rules prevent accidental additions, not filesystem access. This module
does not enforce OS permissions, encrypt files, or prevent another local process
from reading or changing them. The audit file is not tamper-evident. The cooldown
and session reset when the program restarts. Failed logins are logged as anonymous
to avoid recording untrusted identifiers. This is an educational local prototype,
not a production identity service or medical safety system.

Before committing, run `git status --short` and verify generated credentials and
runtime logs are absent. Use `git check-ignore security/credentials.json
security/audit_log.jsonl` to check the ignore rules. Already tracked secrets require
separate removal; adding ignore rules does not untrack them.
