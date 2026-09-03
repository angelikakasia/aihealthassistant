FROGI: AI Health and Safety Assistant

FROGI is a six-week student prototype of an AI-assisted health and safety companion for caregivers during supervised infant and toddler play.

The project combines computer vision, conversational AI, security controls, and a mobile frog-shaped robot. FROGI is designed to monitor a controlled play area, detect predefined safety events, notify a caregiver, and support simple natural-language interaction.

> **Important:** FROGI is an educational prototype. It does not replace active caregiver supervision, professional medical monitoring, or emergency services.

## Project Goals

FROGI demonstrates how three systems can work together:

1. **AI monitoring and assistance** uses a fixed camera to detect a person or compatible test target in a controlled demonstration area, monitors basic position, identifies entry into predefined unsafe zones, and supports caregiver questions.
2. **Security and privacy** protects monitoring information and sensitive actions through authentication, authorization, and audit logging.
3. **The physical robot** provides LED and audible alerts, basic commanded movement, distance sensing, and automatic obstacle stopping.

## Planned MVP Features

- Person or test-target detection using computer vision in a controlled demonstration area
- Basic target-position and predefined unsafe-zone monitoring
- Predefined unsafe-zone detection
- Caregiver safety alerts
- Natural-language questions and commands
- Retrieval from an approved knowledge collection
- Caregiver authentication and session management
- Access control for protected monitoring information
- Authorization for AI actions and robot commands
- Security audit logging
- Basic robot movement
- Distance-based obstacle detection and automatic stopping
- Green, yellow, and red LED status indicators
- Audible alerts

If time permits, the team may explore prolonged-crying detection after the core system is reliable.

The MVP does not require the physical robot to independently find, recognize, track, or follow a child. Computer vision observes the controlled demonstration area, while the robot performs alerts, authorized basic movements, and local obstacle stopping.

## System Overview

```text
Camera
  -> computer vision
  -> movement and unsafe-zone monitoring
  -> safety event and alert logic
  -> LED and buzzer commands

Caregiver request
  -> authentication and authorization
  -> approved monitoring data or knowledge
  -> conversational AI response

Robot command
  -> authorization
  -> serial communication
  -> physical controller
  -> obstacle-safety override
```

Immediate safety alerts and the robot's local obstacle-stop behavior do not depend on conversational AI. Protected monitoring information must pass a security check before it is provided to the AI assistant.

## Repository Structure

```text
FROGI/
|-- ai-assistant/    # Computer vision, monitoring, AI, and robot communication
|-- security/        # Authentication, authorization, and audit logging
|-- robot/           # Robot controller, sensors, movement, LEDs, and buzzer
|-- knowledge/       # Approved information for retrieval by the AI assistant
|-- docs/            # Architecture and project documentation
|-- .gitignore
|-- requirements.txt
`-- README.md
```

### `ai-assistant/`

Planned modules include fixed-camera input, person or compatible test-target detection, basic position monitoring, unsafe-zone detection, alerts, monitoring events, conversational AI, and serial communication with the robot.

### `security/`

Contains caregiver authentication, hashed test credentials, session handling, access control, robot-command authorization, audit logging, and automated security tests.

### `robot/`

Contains the Arduino-compatible controller and hardware pin map for motors, distance sensing, LED eyes, buzzer behavior, serial commands, and the physical safety stop.

### `knowledge/`

Contains approved project, operating, demonstration, and child-safety reference material. Sources should record their origin, sensitivity, and authentication requirements.

## Team

| Team member | Primary responsibility | Development branch |
| --- | --- | --- |
| Angelika | AI security and privacy | `angelika-security` |
| Aneela | AI child monitoring and assistant | `aneela-ai` |
| Jeremiah | Hardware and physical FROGI | `jeremiah-robot` |

The `main` branch contains stable, integrated work. Features are developed and tested on the individual branches before integration.

## Development Plan

- **Weeks 1–2:** Build the individual AI, security, and robot components.
- **Week 3:** Connect monitoring, security, conversational AI, and robot communication.
- **Week 4:** Integrate the complete MVP and test end-to-end scenarios.
- **Week 5:** Fix integration issues and improve reliability and safety.
- **Week 6:** Freeze features, complete testing, and prepare the final demonstration.

## Prototype Demonstrations

The final MVP is intended to demonstrate:

1. Detection and basic position monitoring of a person or compatible test target within a controlled demonstration area.
2. An unsafe-zone event that triggers an LED, buzzer, and recorded alert.
3. Denial of protected information to an unauthenticated user and access for an authenticated caregiver.
4. Robot movement followed by an automatic stop when an obstacle is detected.
5. A caregiver asking FROGI about approved status or event information.

## Security and Privacy

Development and demonstrations use fake or test data only. Do not commit:

- Passwords, PINs, API keys, tokens, or other secrets
- Real child, caregiver, medical, or monitoring information
- Camera recordings containing private information
- Runtime credentials, monitoring events, or audit logs
- Large local AI model files

The following files remain local and should be excluded through `.gitignore`:

```text
.env
security/credentials.json
security/credentials.json.bak
security/audit_log.jsonl
ai-assistant/monitoring_events.json
*.key
*.gguf
*.safetensors
```

## Development Setup

Clone the repository and switch to your assigned branch:

```bash
git clone <repository-url>
cd FROGI
git switch <branch-name>
```

Create a Python virtual environment and install the project dependencies:

```bash
python -m venv .venv
```

On Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Hardware setup and startup instructions will be documented as the integrated prototype is completed.

## Current Status

FROGI is under active development as a six-week minimum viable prototype. Features described here are planned MVP capabilities unless marked as completed in the project documentation.
