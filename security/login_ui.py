"""FROGI caregiver login window. Run: py -3 -m security.login_ui"""
import tkinter as tk
from tkinter import ttk
from .family_store import FamilySecurity
from .family_ui import Forms
from .widgets import RoundedButton

CREAM = '#FAF8F1'
INK = '#23463D'
GREEN = '#32765A'
MINT = '#E5F0DF'
PINK = '#F5D5DF'


class LoginWindow:
    """One real local security session, owned by this window."""
    def __init__(self, root, security=None):
        self.root = root
        self.security = security if security is not None else FamilySecurity()
        self.forms = Forms(self)
        self.signed_in = False
        self.timer = None
        self.root.title('FROGI | Caregiver login')
        self.root.geometry('510x790')
        self.root.minsize(470, 760)
        self.root.configure(bg=CREAM)
        self.root.protocol('WM_DELETE_WINDOW', self.close)
        style = ttk.Style(root)
        style.theme_use('clam')
        style.configure('Frogi.TEntry', font=('Segoe UI', 13), padding=10,
                        fieldbackground='white', foreground=INK)
        style.configure('Frogi.TButton', font=('Segoe UI', 12, 'bold'),
                        background=GREEN, foreground='white', padding=12,
                        borderwidth=0)
        style.map('Frogi.TButton', background=[('active', '#255B45'),
                                               ('disabled', '#718878')])
        outer = tk.Frame(root, bg=CREAM)
        outer.pack(expand=True, fill='both', padx=36, pady=20)
        self.label(outer, 'F R O G I', 12, bold=True).pack(pady=(0, 4))
        self.label(outer, 'Extra eyes for mini you.', 11).pack()
        self.draw_frog(outer)
        self.heading = self.label(outer, 'Hello, caregiver!', 25, bold=True)
        self.heading.pack(pady=(4, 5))
        self.subtitle = self.label(outer, 'A little hello. A secure sign-in.', 11)
        self.subtitle.pack(pady=(0, 18))

        self.form = tk.Frame(outer, bg=CREAM)
        self.form.pack(fill='x')
        self.label(self.form, 'Caregiver name', 11, bold=True).pack(anchor='w')
        self.name = ttk.Entry(self.form, style='Frogi.TEntry')
        self.name.pack(fill='x', pady=(5, 14))
        self.label(self.form, 'Your PIN', 11, bold=True).pack(anchor='w')
        self.pin = ttk.Entry(self.form, show='\u2022', style='Frogi.TEntry')
        self.pin.pack(fill='x', pady=(5, 6))
        self.label(self.form, 'Your PIN stays hidden while you type.', 10).pack(anchor='w')
        self.login_button = RoundedButton(self.form, text='Hop in',
                                       command=self.login)
        self.login_button.pack(fill='x', pady=(18, 0))
        RoundedButton(self.form, text='Sign up · Create account', command=self.forms.signup).pack(fill='x', pady=(8, 0))
        self.name.bind('<Return>', lambda event: self.pin.focus_set())
        self.pin.bind('<Return>', lambda event: self.login())

        self.welcome = tk.Frame(outer, bg=MINT, padx=20, pady=20)
        self.label(self.welcome, 'You are signed in', 17, bold=True, bg=MINT).pack()
        self.label(self.welcome, 'Your caregiver session is open.\nIt closes automatically after 15 minutes.',
                   11, bg=MINT).pack(pady=(10, 16))
        self.logout_button = RoundedButton(self.welcome, text='Log out',
                                        command=self.logout)
        self.logout_button.pack(fill='x')
        RoundedButton(self.welcome, text='My babies & care notebook',
                   command=self.forms.dashboard).pack(fill='x', pady=(10, 0))

        self.message = self.label(outer, '', 11)
        self.message.configure(wraplength=390)
        self.message.pack(fill='x', pady=(16, 4))
        self.footer = self.label(outer, 'Caregiver access only\nMonitoring and robot controls are not connected here.', 10)
        self.footer.configure(wraplength=400)
        self.footer.pack(side='bottom', pady=(10, 0))
        if not self.security.credentials_path.is_file():
            self.message.configure(text='New here? Choose Sign up to create your account.',
                                   fg='#91404B')
        self.name.focus_set()
        self.timer = self.root.after(1000, self.check_session)

    def label(self, parent, text, size, *, bold=False, bg=CREAM):
        return tk.Label(parent, text=text, bg=bg, fg=INK,
                        font=('Segoe UI', size, 'bold' if bold else 'normal'),
                        justify='center')

    def draw_frog(self, parent):
        canvas = tk.Canvas(parent, width=240, height=142, bg=CREAM, highlightthickness=0)
        canvas.pack(pady=(8, 0))
        canvas.create_oval(26, 119, 214, 140, fill=MINT, outline='')
        canvas.create_oval(37, 35, 203, 133, fill='#A6C992', outline=INK, width=2)
        for x in (76, 164):
            canvas.create_oval(x-28, 14, x+28, 74, fill='#A6C992', outline=INK, width=2)
            canvas.create_oval(x-18, 24, x+18, 62, fill='white', outline='')
            canvas.create_oval(x-7, 34, x+7, 52, fill=INK, outline='')
            canvas.create_oval(x-3, 35, x+1, 40, fill='white', outline='')
        canvas.create_oval(56, 78, 86, 94, fill=PINK, outline='')
        canvas.create_oval(154, 78, 184, 94, fill=PINK, outline='')
        canvas.create_arc(92, 68, 148, 106, start=195, extent=150, style='arc', outline=INK, width=3)

    def login(self):
        if self.signed_in:
            return
        auth_id = self.name.get().strip()
        pin = self.pin.get()
        self.pin.delete(0, 'end')
        if not auth_id or not pin:
            self.message.configure(text='Enter your caregiver name and PIN.', fg='#91404B')
            self.pin.focus_set()
            return
        self.login_button.configure(state='disabled')
        self.message.configure(text='Checking your login…', fg=INK)
        self.root.update_idletasks()
        try:
            allowed = self.security.login(auth_id, pin)
        finally:
            pin = None
            self.login_button.configure(state='normal')
        if allowed:
            self.forms.clear()
            self.signed_in = True
            self.name.delete(0, 'end')
            self.heading.configure(text='Welcome back!')
            self.subtitle.configure(text='A happy little hop. You’re in.')
            self.form.pack_forget()
            self.welcome.pack(fill='x', before=self.message)
            self.message.configure(text='Login successful.', fg=GREEN)
            self.logout_button.focus_set()
        else:
            self.message.configure(text='We couldn’t sign you in. Check your name and PIN.\n'
                                   'After repeated attempts, wait 30 seconds and try again.', fg='#91404B')
            self.pin.focus_set()

    def show_logged_out(self, message):
        self.forms.clear()
        self.signed_in = False
        self.name.delete(0, 'end')
        self.pin.delete(0, 'end')
        self.welcome.pack_forget()
        self.form.pack(fill='x', before=self.message)
        self.heading.configure(text='Hello, caregiver!')
        self.subtitle.configure(text='A little hello. A secure sign-in.')
        self.message.configure(text=message, fg=INK)
        self.name.focus_set()

    def logout(self):
        logged = self.security.logout()
        self.show_logged_out('All signed out. See you soon!' if logged else
                             'You are signed out. The audit log could not be saved.')

    def check_session(self):
        if self.signed_in and not self.security.is_authenticated():
            self.show_logged_out('Your session has ended. Please sign in again.')
        if self.signed_in:
            self.forms.check_reminders()
        self.timer = self.root.after(1000, self.check_session)

    def close(self):
        self.forms.clear()
        if self.timer is not None:
            self.root.after_cancel(self.timer)
        if self.signed_in:
            self.security.logout()
        self.root.destroy()


def main():
    root = tk.Tk()
    LoginWindow(root)
    root.mainloop()


if __name__ == '__main__':
    main()
