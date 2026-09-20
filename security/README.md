# Angelika: security and privacy

This folder implements Angelika's standalone component. It contains no computer
vision, LLM integration, serial implementation, or Arduino/hardware code.
Only Python's standard library is required (Python 3.10 or newer).

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
