"""Simple account and family diary windows for the local FROGI app."""
import tkinter as tk
from tkinter import ttk
from datetime import date
from .family_store import FamilyStore

BG = '#FAF8F1'
INK = '#23463D'


class Forms:
    def __init__(self, app):
        self.app = app
        self.windows = []
        self.store = FamilyStore(app.security)

    def clear(self):
        for window in self.windows:
            if window.winfo_exists():
                window.destroy()
        self.windows.clear()

    def window(self, title, size='540x620'):
        win = tk.Toplevel(self.app.root)
        win.title('FROGI | ' + title)
        win.geometry(size)
        win.configure(bg=BG)
        win.transient(self.app.root)
        self.windows.append(win)
        tk.Label(win, text=title, font=('Segoe UI', 22, 'bold'), bg=BG, fg=INK).pack(pady=(20, 10))
        return win

    def label(self, parent, text):
        tk.Label(parent, text=text, bg=BG, fg=INK, wraplength=480,
                 justify='left', font=('Segoe UI', 11)).pack(anchor='w', padx=24, pady=(8, 4))

    def field(self, parent, title, value='', secret=False, multiline=False):
        self.label(parent, title)
        if multiline:
            widget = tk.Text(parent, height=3, wrap='word', font=('Segoe UI', 11))
            widget.insert('1.0', value)
        else:
            widget = ttk.Entry(parent, style='Frogi.TEntry', show='\u2022' if secret else '')
            widget.insert(0, value)
        widget.pack(fill='x', padx=24)
        return widget

    def status(self, parent):
        label = tk.Label(parent, text='', bg=BG, fg='#91404B', wraplength=470, font=('Segoe UI', 11))
        label.pack(fill='x', padx=24, pady=10)
        return label

    def button(self, parent, text, command):
        ttk.Button(parent, text=text, command=command, style='Frogi.TButton').pack(fill='x', padx=24, pady=6)

    def signup(self):
        win = self.window('Join our little pond', '540x640')
        self.label(win, 'Create your own caregiver login. Your baby records belong to this account.')
        name = self.field(win, 'Caregiver login (letters, digits, _ or -)')
        pin = self.field(win, 'Choose a PIN (6–12 digits)', secret=True)
        confirm = self.field(win, 'Enter your PIN again', secret=True)
        status = self.status(win)

        def save():
            first, second = pin.get(), confirm.get()
            pin.delete(0, 'end')
            confirm.delete(0, 'end')
            if first != second:
                status.configure(text='Those PINs don’t match. Please enter them again.')
                return
            try:
                self.app.security.register(name.get().strip(), first)
            except FileExistsError:
                status.configure(text='That login already exists. Please choose another or sign in.')
                return
            except (ValueError, OSError) as exc:
                status.configure(text=str(exc))
                return
            finally:
                first = second = None
            self.app.name.delete(0, 'end')
            self.app.name.insert(0, name.get().strip())
            self.app.message.configure(text='Account created! Enter your PIN and hop in.', fg=INK)
            win.destroy()
            self.app.pin.focus_set()

        self.button(win, 'Create account', save)
        self.button(win, 'Back to login', win.destroy)

    def dashboard(self):
        if not self.app.security.is_authenticated():
            self.app.show_logged_out('Please sign in again.')
            return
        win = self.window('My little ones', '620x680')
        self.label(win, 'Add a baby, then open their illness diary. Entries are written by you; FROGI does not diagnose illnesses.')
        self.label(win, 'Stored on this computer. Local files are not encrypted; use a protected Windows account.')
        tree = ttk.Treeview(win, columns=('name', 'dob'), show='headings', height=9)
        tree.heading('name', text='Baby name')
        tree.heading('dob', text='Date of birth')
        tree.column('name', width=280)
        tree.column('dob', width=150)
        tree.pack(fill='both', expand=True, padx=24, pady=12)
        status = self.status(win)
        rows = {}

        def refresh():
            try:
                records = self.store.babies()
                tree.delete(*tree.get_children())
                rows.clear()
                for row in records:
                    key = str(row['id'])
                    rows[key] = row
                    tree.insert('', 'end', iid=key, values=(row['name'], row['dob']))
                status.configure(text='' if records else 'Your pond is empty. Add your first baby below.')
            except Exception as exc:
                status.configure(text=self.error(exc))

        def selected(action):
            if not tree.selection():
                status.configure(text='Choose a baby from the list first.')
                return
            action(rows[tree.selection()[0]])

        self.button(win, '+ Add baby', lambda: self.baby_form(refresh))
        self.button(win, 'Edit selected baby', lambda: selected(lambda row: self.baby_form(refresh, row)))
        self.button(win, 'Open illness diary', lambda: selected(self.diary))
        tree.bind('<Double-1>', lambda event: selected(self.diary))
        refresh()

    @staticmethod
    def error(exc):
        if isinstance(exc, (PermissionError, ValueError)):
            return str(exc)
        return 'Could not access the local records. Check that the data folder is writable.'

    def baby_form(self, refresh, row=None):
        row = row or {}
        win = self.window('A little introduction', '540x430')
        name = self.field(win, 'Baby name', row.get('name', ''))
        dob = self.field(win, 'Date of birth (YYYY-MM-DD)', row.get('dob', ''))
        status = self.status(win)

        def save():
            try:
                self.store.save_baby(name.get(), dob.get().strip(), row.get('id'))
            except Exception as exc:
                status.configure(text=self.error(exc))
                return
            win.destroy()
            refresh()

        self.button(win, 'Save baby', save)
        self.button(win, 'Cancel', win.destroy)

    def diary(self, baby):
        win = self.window('Illness diary', '680x700')
        self.label(win, baby['name'] + ' • Born ' + baby['dob'])
        tree = ttk.Treeview(win, columns=('date', 'title', 'status'), show='headings', height=7)
        for column, title, width in [('date', 'Started', 100), ('title', 'Illness / concern', 310), ('status', 'Status', 130)]:
            tree.heading(column, text=title)
            tree.column(column, width=width)
        tree.pack(fill='both', expand=True, padx=24, pady=12)
        detail = tk.Text(win, height=7, wrap='word', font=('Segoe UI', 11), state='disabled')
        detail.pack(fill='x', padx=24)
        status = self.status(win)
        rows = {}

        def display(event=None):
            detail.configure(state='normal')
            detail.delete('1.0', 'end')
            if tree.selection():
                row = rows[tree.selection()[0]]
                detail.insert('1.0', 'Started: ' + row['started'] + '\nEnded: ' + (row['ended'] or 'Ongoing') +
                              '\n\nSymptoms: ' + row['symptoms'] + '\n\nNotes: ' + row['notes'])
            detail.configure(state='disabled')

        def refresh():
            try:
                records = self.store.illnesses(baby['id'])
                tree.delete(*tree.get_children())
                rows.clear()
                for row in records:
                    key = str(row['id'])
                    rows[key] = row
                    tree.insert('', 'end', iid=key, values=(row['started'], row['title'], 'Ended' if row['ended'] else 'Ongoing'))
                display()
                status.configure(text='' if records else 'No entries yet. Add a note when you need one.')
            except Exception as exc:
                status.configure(text=self.error(exc))

        def edit():
            if tree.selection():
                self.illness_form(baby, refresh, rows[tree.selection()[0]])
            else:
                status.configure(text='Choose an entry to edit.')

        tree.bind('<<TreeviewSelect>>', display)
        self.button(win, '+ Add illness entry', lambda: self.illness_form(baby, refresh))
        self.button(win, 'Edit selected entry', edit)
        refresh()

    def illness_form(self, baby, refresh, row=None):
        row = row or {}
        win = self.window('A little health note', '560x770')
        title = self.field(win, 'Illness or concern (your own description)', row.get('title', ''))
        started = self.field(win, 'Started (YYYY-MM-DD)', row.get('started', date.today().isoformat()))
        ended = self.field(win, 'Ended (YYYY-MM-DD) — leave blank if ongoing', row.get('ended', ''))
        symptoms = self.field(win, 'Symptoms you noticed', row.get('symptoms', ''), multiline=True)
        notes = self.field(win, 'Notes', row.get('notes', ''), multiline=True)
        status = self.status(win)

        def save():
            try:
                self.store.save_illness(baby['id'], started.get().strip(), ended.get().strip(), title.get(),
                                       symptoms.get('1.0', 'end-1c'), notes.get('1.0', 'end-1c'), row.get('id'))
            except Exception as exc:
                status.configure(text=self.error(exc))
                return
            win.destroy()
            refresh()

        self.button(win, 'Save entry', save)
        self.button(win, 'Cancel', win.destroy)
