"""Angelika's standalone security component."""
from .security import (Security, login, logout, is_authenticated, can_read,
                       can_command, audit_event, read_protected, execute_command)
