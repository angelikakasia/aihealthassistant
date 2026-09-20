"""Caregiver-entered records and signed-in appointment reminders."""
import tkinter as tk
from tkinter import ttk
from datetime import datetime
import time
from .health_store import HealthStore, FIELDS, STATUSES, REMINDERS

TITLES = {'medication': 'Medications', 'allergy': 'Allergies', 'appointment': 'Appointments'}


class HealthUI:
    def __init__(self, forms):
        self.forms = forms
        self.store = HealthStore(forms.app.security)

    def open(self, baby):
        f = self.forms
        win = f.window(baby['name'] + ' · Care notebook', '760x730')
        f.label(win, 'Keep your little one’s records together. Medication details are your entries; doses are not calculated.')
        f.button(win, 'Open illness diary', lambda: f.diary(baby))
        notebook = ttk.Notebook(win)
        notebook.pack(fill='both', expand=True, padx=24, pady=(10, 20))
        for kind, title in TITLES.items():
            page = tk.Frame(notebook, bg='#FAF8F1')
            notebook.add(page, text='  ' + title + '  ')
            self.page(page, baby, kind)

    def page(self, page, baby, kind):
        f = self.forms
        if kind == 'appointment':
            f.label(page, 'Schedule uses this computer’s local time. Reminders appear only while FROGI is open and you are signed in. Missed reminders appear next time you sign in.')
        tree = ttk.Treeview(page, columns=('name', 'extra', 'status'), show='headings', height=6)
        for key, title, width in [('name', 'Name / reason', 230),
                                  ('extra', 'Date & time' if kind == 'appointment' else 'Details', 210),
                                  ('status', 'Status', 110)]:
            tree.heading(key, text=title)
            tree.column(key, width=width)
        tree.pack(fill='both', expand=True, padx=16, pady=10)
        scrollbar = ttk.Scrollbar(page, orient='vertical', command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side='right', fill='y')
        detail = tk.Text(page, height=5, wrap='word', font=('Segoe UI', 11), state='disabled')
        detail.pack(fill='x', padx=16)
        status = f.status(page)
        rows = {}

        def display(event=None):
            detail.configure(state='normal')
            detail.delete('1.0', 'end')
            if tree.selection() and tree.selection()[0] in rows:
                row = rows[tree.selection()[0]]
                text = '\n'.join(label + ': ' + (row[key] or '—') for key, label, _, _ in FIELDS[kind])
                if kind == 'appointment':
                    text += '\nReminder: ' + next(label for label, minutes in REMINDERS.items() if minutes == row['reminder_minutes'])
                detail.insert('1.0', text)
            detail.configure(state='disabled')

        def refresh():
            if not page.winfo_exists():
                return
            try:
                records = self.store.records(baby['id'], kind)
                tree.delete(*tree.get_children())
                rows.clear()
                for row in records:
                    key = str(row['id'])
                    rows[key] = row
                    tree.insert('', 'end', iid=key, values=(row['name'], row.get('when', row.get('dose', row.get('reaction', ''))), row['status']))
                display()
                status.configure(text='' if records else 'Nothing here yet. Add your first record below.')
            except Exception as exc:
                status.configure(text=f.error(exc))

        def edit():
            if tree.selection():
                self.editor(baby, kind, refresh, rows[tree.selection()[0]])
            else:
                status.configure(text='Choose a record first.')

        tree.bind('<<TreeviewSelect>>', display)
        f.button(page, '+ Add ' + {'medication': 'medication', 'allergy': 'allergy', 'appointment': 'appointment'}[kind],
                 lambda: self.editor(baby, kind, refresh))
        f.button(page, 'Edit selected record', edit)
        refresh()

    def editor(self, baby, kind, refresh, row=None):
        row = row or {}
        f = self.forms
        win = f.window(('Edit ' if row else 'Add ') + kind, '600x760')
        # Scrollable forms keep fields and actions reachable on smaller screens.
        canvas = tk.Canvas(win, bg='#FAF8F1', highlightthickness=0)
        scroll = ttk.Scrollbar(win, orient='vertical', command=canvas.yview)
        scroll.pack(side='right', fill='y')
        canvas.pack(fill='both', expand=True)
        canvas.configure(yscrollcommand=scroll.set)
        body = tk.Frame(canvas, bg='#FAF8F1')
        item = canvas.create_window((0, 0), window=body, anchor='nw')
        body.bind('<Configure>', lambda event: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.bind('<Configure>', lambda event: canvas.itemconfigure(item, width=event.width))
        fields = {}
        for key, label, _, maximum in FIELDS[kind]:
            value = row.get(key, '')
            fields[key] = f.field(body, label, value, multiline=maximum > 500)
        f.label(body, 'Status')
        state = ttk.Combobox(body, values=STATUSES[kind], state='readonly')
        state.set(row.get('status', STATUSES[kind][0]))
        state.pack(fill='x', padx=24)
        reminder = None
        if kind == 'appointment':
            f.label(body, 'Remind me')
            reminder = ttk.Combobox(body, values=list(REMINDERS), state='readonly')
            reminder.set(next(label for label, minutes in REMINDERS.items() if minutes == row.get('reminder_minutes', 60)))
            reminder.pack(fill='x', padx=24)
        status = f.status(body)

        def save():
            values = {key: widget.get('1.0', 'end-1c') if isinstance(widget, tk.Text) else widget.get()
                      for key, widget in fields.items()}
            values['status'] = state.get()
            if reminder is not None:
                values['reminder_minutes'] = REMINDERS[reminder.get()]
            try:
                self.store.save(baby['id'], kind, values, row.get('id'))
            except Exception as exc:
                status.configure(text=f.error(exc))
                return
            win.destroy()
            refresh()
            f.next_reminder_check = 0

        f.button(body, 'Save ' + kind, save)
        f.button(body, 'Cancel', win.destroy)

    def reminders(self):
        f = self.forms
        if f.reminder_window is not None and f.reminder_window.winfo_exists():
            return
        try:
            due = self.store.due()
        except Exception:
            f.app.message.configure(text='Appointment reminders could not be checked. Please check your schedule.', fg='#91404B')
            return
        if not due:
            return
        win = f.window('A little appointment reminder', '610x550')
        f.reminder_window = win
        text = tk.Text(win, wrap='word', font=('Segoe UI', 12), height=12)
        text.pack(fill='both', expand=True, padx=24, pady=10)
        for row in due:
            late = self.store.time(row['when']) < datetime.now()
            text.insert('end', f"{row['baby_name']} · {row['name']}\n{row['when']}" +
                        (' · Past appointment / missed reminder' if late else '') +
                        f"\n{row['provider']}\n{row['location']}\n\n")
        text.configure(state='disabled')
        status = f.status(win)

        def acknowledge():
            try:
                for row in due:
                    self.store.acknowledge(row['id'])
            except Exception as exc:
                status.configure(text=f.error(exc))
                return
            win.destroy()

        f.button(win, 'Got it · Dismiss these reminders', acknowledge)
        def snooze():
            f.next_reminder_check = time.monotonic() + 300
            win.destroy()

        f.button(win, 'Remind me again in 5 minutes', snooze)
        win.protocol('WM_DELETE_WINDOW', snooze)
        # Closing without acknowledgement is a five-minute snooze in this run.
        win.lift()
        win.bell()
