"""Windows desktop setup and controls. All Tk work stays on the UI thread."""
import os
from pathlib import Path
import queue
import subprocess
import threading
import tkinter as tk
from tkinter import messagebox, ttk
import webbrowser

from .runtime import SetupCancelled
from .services import DASHBOARD_URL, ServiceManager
from .settings import load_settings, save_settings, user_directory


class DesktopApp:
    def __init__(self, root, directory=None):
        self.root = root
        self.directory = Path(directory or user_directory())
        self.manager = ServiceManager(self.directory)
        self.events = queue.Queue()
        self.cancel = threading.Event()
        self.busy = False
        self.running = False
        self.closing = False
        self.inputs = []
        try:
            self.settings = load_settings(self.directory)
        except (OSError, ValueError, TypeError) as error:
            messagebox.showerror('Unable to read settings', str(error), parent=root)
            root.destroy()
            raise
        root.title('ORYTH — Personal Cyber Risk Dashboard')
        root.geometry('680x660')
        root.minsize(620, 630)
        root.configure(bg='#f4f6fa')
        style = ttk.Style(root)
        if 'vista' in style.theme_names():
            style.theme_use('vista')
        style.configure('TFrame', background='#f4f6fa')
        style.configure('TLabel', background='#f4f6fa', font=('Segoe UI', 10))
        style.configure('Title.TLabel', font=('Segoe UI', 23, 'bold'), foreground='#12233f')
        style.configure('Hint.TLabel', font=('Segoe UI', 9), foreground='#52617a')
        frame = ttk.Frame(root, padding=26)
        frame.pack(fill='both', expand=True)
        frame.columnconfigure(0, weight=1)
        ttk.Label(frame, text='ORYTH', style='Title.TLabel').grid(row=0, column=0, sticky='w')
        ttk.Label(frame, text='Your personal cyber risk dashboard', style='Hint.TLabel').grid(row=1, column=0, sticky='w', pady=(0, 20))
        ttk.Label(frame, text='Email breach monitoring', font=('Segoe UI', 11, 'bold')).grid(row=2, column=0, sticky='w')
        ttk.Label(frame, text='Free with XposedOrNot. Enter addresses separated by commas or new lines.', style='Hint.TLabel').grid(row=3, column=0, sticky='w', pady=(3, 6))
        self.emails = tk.Text(frame, height=4, font=('Segoe UI', 10), relief='solid', borderwidth=1, padx=8, pady=6)
        self.emails.insert('1.0', '\n'.join(self.settings['emails']))
        self.emails.grid(row=4, column=0, sticky='ew', pady=(0, 16))
        self.inputs.append(self.emails)
        ttk.Label(frame, text='Network exposure monitoring · optional', font=('Segoe UI', 11, 'bold')).grid(row=5, column=0, sticky='w')
        self.ip = tk.StringVar(value=self.settings['public_ip'])
        self.token = tk.StringVar(value=self.settings['censys_token'])
        self.organization = tk.StringVar(value=self.settings['organization_id'])
        network = ttk.Frame(frame)
        network.grid(row=6, column=0, sticky='ew', pady=(8, 16))
        network.columnconfigure(1, weight=1)
        for row, (label, variable, masked) in enumerate([
                ('Public IP address', self.ip, False), ('Censys token', self.token, True),
                ('Organization ID (optional)', self.organization, False)]):
            ttk.Label(network, text=label).grid(row=row, column=0, sticky='w', padx=(0, 14), pady=4)
            entry = ttk.Entry(network, textvariable=variable, show='•' if masked else '')
            entry.grid(row=row, column=1, sticky='ew', pady=4)
            self.inputs.append(entry)
        ttk.Label(frame, text='Dashboard sign-in', font=('Segoe UI', 11, 'bold')).grid(row=7, column=0, sticky='w')
        credentials = ttk.Frame(frame)
        credentials.grid(row=8, column=0, sticky='ew', pady=(6, 14))
        credentials.columnconfigure(1, weight=1)
        ttk.Label(credentials, text='Username: admin').grid(row=0, column=0, sticky='w', padx=(0, 14))
        self.password = tk.StringVar(value=self.settings['dashboard_password'])
        ttk.Entry(credentials, textvariable=self.password, state='readonly', show='•').grid(row=0, column=1, sticky='ew')
        ttk.Button(credentials, text='Copy password', command=self.copy_password).grid(row=0, column=2, padx=(8, 0))
        buttons = ttk.Frame(frame)
        buttons.grid(row=9, column=0, sticky='ew', pady=8)
        self.start_button = ttk.Button(buttons, text='Start monitoring', command=self.start)
        self.start_button.pack(side='left')
        self.stop_button = ttk.Button(buttons, text='Stop', command=self.stop, state='disabled')
        self.stop_button.pack(side='left', padx=8)
        self.open_button = ttk.Button(buttons, text='Open dashboard', command=lambda: webbrowser.open(DASHBOARD_URL), state='disabled')
        self.open_button.pack(side='left')
        ttk.Button(buttons, text='Open data folder', command=self.open_folder).pack(side='right')
        self.progress = ttk.Progressbar(frame, mode='indeterminate')
        self.progress.grid(row=10, column=0, sticky='ew', pady=(12, 8))
        self.status = tk.StringVar(value='Ready. First start downloads the dashboard components; internet is required.')
        ttk.Label(frame, textvariable=self.status, wraplength=610, style='Hint.TLabel').grid(row=11, column=0, sticky='ew')
        ttk.Label(frame, text='Keep this window open while monitoring. Closing it stops the local services.', wraplength=610, style='Hint.TLabel').grid(row=12, column=0, sticky='ew', pady=(12, 0))
        root.protocol('WM_DELETE_WINDOW', self.close)
        root.after(150, self.process_events)

    def copy_password(self):
        # Persist the generated password so a copied password remains valid after reopening.
        try:
            self.settings = save_settings(self.directory, self.settings)
        except (OSError, ValueError) as error:
            messagebox.showerror('Unable to save settings', str(error), parent=self.root)
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(self.password.get())
        self.status.set('Dashboard password copied. Sign in as admin.')

    def open_folder(self):
        self.directory.mkdir(parents=True, exist_ok=True)
        if os.name == 'nt':
            os.startfile(self.directory)
        else:
            subprocess.Popen(['xdg-open', str(self.directory)])

    def set_inputs(self, enabled):
        for widget in self.inputs:
            widget.configure(state='normal' if enabled else 'disabled')

    def start(self):
        if self.busy or self.running:
            return
        try:
            values = {'emails': self.emails.get('1.0', 'end'), 'public_ip': self.ip.get(),
                      'censys_token': self.token.get(), 'organization_id': self.organization.get(),
                      'dashboard_password': self.password.get()}
            self.settings = save_settings(self.directory, values)
        except (OSError, ValueError) as error:
            messagebox.showerror('Check your settings', str(error), parent=self.root)
            return
        self.busy = True
        self.cancel.clear()
        self.set_inputs(False)
        self.start_button.configure(state='disabled')
        self.stop_button.configure(state='normal')
        self.progress.start(12)
        def worker():
            try:
                self.manager.start(self.settings, progress=lambda text: self.events.put(('status', text)), cancel=self.cancel)
                self.events.put(('started', None))
            except SetupCancelled:
                self.events.put(('stopped', None))
            except Exception as error:
                self.events.put(('error', str(error)))
        threading.Thread(target=worker, daemon=False).start()

    def stop(self):
        self.cancel.set()
        self.stop_button.configure(state='disabled')
        self.open_button.configure(state='disabled')
        self.status.set('Stopping…')
        if self.busy:
            return
        self.busy = True
        def worker():
            self.manager.stop()
            self.events.put(('stopped', None))
        threading.Thread(target=worker, daemon=False).start()

    def close(self):
        self.closing = True
        if not self.busy and not self.running:
            self.root.destroy()
        else:
            self.stop()

    def process_events(self):
        try:
            while True:
                event, text = self.events.get_nowait()
                if event == 'status':
                    self.status.set(text)
                elif event == 'started':
                    self.busy = False
                    self.running = True
                    self.progress.stop()
                    self.open_button.configure(state='normal')
                    if self.closing or self.cancel.is_set():
                        self.stop()
                    else:
                        self.status.set('Monitoring is running. Open the dashboard and sign in as admin.')
                elif event in ('stopped', 'error'):
                    self.busy = False
                    self.running = False
                    self.progress.stop()
                    self.set_inputs(True)
                    self.start_button.configure(state='normal')
                    self.stop_button.configure(state='disabled')
                    self.open_button.configure(state='disabled')
                    self.status.set('Stopped.' if event == 'stopped' else text)
                    if self.closing:
                        self.root.destroy()
                        return
                    if event == 'error':
                        messagebox.showerror('Unable to start ORYTH', text, parent=self.root)
        except queue.Empty:
            pass
        if self.running and not self.busy:
            try:
                self.manager.check_processes()
            except RuntimeError as error:
                self.status.set(str(error))
                self.stop()
        self.root.after(250, self.process_events)


def run(directory=None):
    root = tk.Tk()
    DesktopApp(root, directory)
    root.mainloop()
