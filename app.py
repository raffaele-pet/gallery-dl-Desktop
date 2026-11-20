"""Paste a link, choose a folder, download."""
from __future__ import annotations

import ctypes
import json
import os
from pathlib import Path
import queue
import subprocess
import sys
import threading
import tkinter as tk
import webbrowser
from tkinter import filedialog, messagebox, ttk
from app_update import is_packaged_installation
from engine import folder_name_from_url, normalize_urls

APP_DIR = Path(__file__).resolve().parent
STATE_FILE = APP_DIR / '.gallery-dl-gui.json'
ICON_PNG = APP_DIR / 'assets/gallery-dl-icon.png'
ICON_ICO = APP_DIR / 'assets/gallery-dl-icon.ico'
BG, PANEL, BORDER = '#151326', '#201d35', '#443b60'
TEXT, MUTED, GREEN, FOCUS = '#f6f2ff', '#bbb3d1', '#b2f962', '#ab97e7'


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('gallery-dl Desktop')
        try:
            if sys.platform == 'win32':
                self.iconbitmap(str(ICON_ICO))
            else:
                self.iconphoto(True, tk.PhotoImage(file=str(ICON_PNG)))
        except tk.TclError:
            pass
        self.configure(bg=BG)
        self.events = queue.Queue()
        self.process = None
        self.busy = self.cancelled = False
        self.saved = self.existing = 0
        self.update_restart_required = False
        self.update_verified = False
        self.updating = False
        destination = str(Path('Downloads') / 'gallery-dl')
        prefs = {}
        try:
            prefs = json.loads(STATE_FILE.read_text(encoding='utf-8'))
            destination = prefs.get('destination') or destination
            previous_default = str(Path.home() / 'Downloads' / 'gallery-dl')
            if os.path.normcase(destination) == os.path.normcase(previous_default):
                destination = str(Path('Downloads') / 'gallery-dl')
        except (OSError, ValueError):
            pass
        self.destination = tk.StringVar(value=destination)
        self.download_images = tk.BooleanVar(value=prefs.get('images', True) is not False)
        self.download_videos = tk.BooleanVar(value=bool(prefs.get('videos', False)))
        self.separate_media = tk.BooleanVar(value=prefs.get('separate_media', True) is not False)
        self.collection = tk.StringVar()
        self._automatic_collection = ''
        self._setting_collection = False
        self.status = tk.StringVar(value='Ready')
        self.detail = tk.StringVar()
        self.progress_value = tk.DoubleVar()
        self.details_visible = False
        self.managed_install = is_packaged_installation()
        self._configure_style()
        self._build_ui()
        self.protocol('WM_DELETE_WINDOW', self.close)
        self.bind('<Control-Return>', lambda _: self.start())
        self.after(100, self.poll)

    def _configure_style(self):
        style = ttk.Style(self)
        style.theme_use('clam')
        style.configure('.', background=BG, foreground=TEXT, font=('Segoe UI', 10))
        style.configure('Heading.TLabel', font=('Segoe UI Semibold', 17))
        style.configure('Section.TLabel', font=('Segoe UI Semibold', 10))
        style.configure('Muted.TLabel', foreground=MUTED)
        style.configure('Rule.TFrame', background=BORDER)
        style.configure('TEntry', padding=(8, 6), fieldbackground=PANEL, insertcolor=TEXT,
                        bordercolor=BORDER, lightcolor=PANEL, darkcolor=PANEL)
        style.map('TEntry', bordercolor=[('focus', FOCUS)],
                  fieldbackground=[('disabled', BG)], foreground=[('disabled', MUTED)])
        for name in ('TButton', 'TMenubutton', 'Primary.TButton'):
            primary = name == 'Primary.TButton'
            normal = GREEN if primary else BG
            hover = '#cbff9c' if primary else '#302a47'
            style.configure(name, padding=(11, 6), background=normal,
                            foreground='#17280d' if primary else TEXT,
                            bordercolor=GREEN if primary else BORDER,
                            lightcolor=normal, darkcolor=normal, focuscolor=FOCUS)
            style.map(name, background=[('disabled', PANEL), ('active', hover), ('pressed', hover)],
                      foreground=[('disabled', MUTED)],
                      bordercolor=[('focus', FOCUS), ('disabled', BORDER)])
        style.configure('Primary.TButton', padding=(16, 7), font=('Segoe UI Semibold', 10))
        style.configure('TMenubutton', arrowcolor=MUTED)
        for name in ('TCheckbutton', 'TRadiobutton'):
            style.configure(name, indicatorbackground=PANEL, indicatorforeground='#1b2b10',
                            bordercolor=BORDER, focuscolor=FOCUS)
            style.map(name, indicatorbackground=[('selected', GREEN)], foreground=[('disabled', MUTED)],
                      background=[('active', BG)])
        style.configure('Horizontal.TProgressbar', background=GREEN, troughcolor=PANEL,
                        bordercolor=BORDER, lightcolor=GREEN, darkcolor=GREEN)
        style.configure('Details.Vertical.TScrollbar', background='#554979', troughcolor=PANEL,
                        bordercolor=PANEL, lightcolor='#554979', darkcolor='#554979',
                        arrowcolor='#e8dfff', arrowsize=12)
        style.map('Details.Vertical.TScrollbar', background=[('active', '#74649b')])

    def _build_ui(self):
        body = ttk.Frame(self, padding=(24, 16, 24, 16))
        body.pack(fill='both', expand=True)
        body.columnconfigure(0, weight=1)
        body.rowconfigure(10, weight=1)

        header = ttk.Frame(body)
        header.grid(row=0, column=0, sticky='ew', pady=(0, 12))
        ttk.Label(header, text='Download media', style='Heading.TLabel').pack(side='left')
        tools = ttk.Menubutton(header, text='Tools', width=7, takefocus=True)
        tools.pack(side='right')
        self.tools_menu = tk.Menu(tools, tearoff=False, background=PANEL, foreground=TEXT,
                                  activebackground='#38304f', activeforeground=TEXT)
        if self.managed_install:
            self.tools_menu.add_command(label='Check for app updates…', command=self.open_releases)
        self.tools_menu.add_command(label='Update download engines' if self.managed_install else 'Update app and engines',
                                    command=self.update_engine)
        tools.configure(menu=self.tools_menu)
        ttk.Frame(body, style='Rule.TFrame', height=1).grid(row=1, column=0, sticky='ew', pady=(0, 12))

        source = ttk.Frame(body)
        source.grid(row=2, column=0, sticky='ew', pady=(0, 13))
        source.columnconfigure(0, weight=1)
        ttk.Label(source, text='Source URLs', style='Section.TLabel').grid(row=0, column=0, sticky='w', pady=(0, 5))
        self.urls = tk.Text(source, height=3, width=1, wrap='word', bg=PANEL, fg=TEXT, insertbackground=TEXT,
                            selectbackground='#66548f', selectforeground=TEXT, relief='flat', borderwidth=0,
                            highlightthickness=1, highlightbackground=BORDER, highlightcolor=FOCUS,
                            padx=8, pady=6, font=('Segoe UI', 10), undo=True)
        self.urls.grid(row=1, column=0, sticky='ew')
        self.urls.bind('<<Modified>>', self.url_changed)
        self.urls.bind('<Tab>', self._leave_urls)
        self.urls.bind('<Shift-Tab>', self._leave_urls)
        self.urls.edit_modified(False)
        self.paste = ttk.Button(source, text='Paste', command=self.paste_urls)
        self.paste.grid(row=1, column=1, sticky='n', padx=(8, 0))
        ttk.Label(source, text='Paste links to pages, posts, images or galleries.',
                  style='Muted.TLabel').grid(row=2, column=0, sticky='w', pady=(5, 0))

        options = ttk.Frame(body)
        options.grid(row=3, column=0, sticky='ew', pady=(0, 14))
        options.columnconfigure(0, weight=1)
        options.columnconfigure(1, weight=1)
        media = ttk.Frame(options)
        media.grid(row=0, column=0, sticky='w')
        ttk.Label(media, text='Media', style='Section.TLabel').grid(row=0, column=0, sticky='w', pady=(0, 3))
        self.images_check = ttk.Checkbutton(media, text='Images', variable=self.download_images)
        self.images_check.grid(row=1, column=0, sticky='w')
        self.videos_check = ttk.Checkbutton(media, text='Videos', variable=self.download_videos)
        self.videos_check.grid(row=1, column=1, sticky='w', padx=(12, 0))
        layout = ttk.Frame(options)
        layout.grid(row=0, column=1, sticky='w', padx=(12, 0))
        ttk.Label(layout, text='Folder layout', style='Section.TLabel').grid(row=0, column=0, sticky='w', pady=(0, 3))
        self.separate_radio = ttk.Radiobutton(layout, text='Separate folders', variable=self.separate_media, value=True)
        self.separate_radio.grid(row=1, column=0, sticky='w')
        self.together_radio = ttk.Radiobutton(layout, text='One folder', variable=self.separate_media, value=False)
        self.together_radio.grid(row=1, column=1, sticky='w', padx=(12, 0))

        destination = ttk.Frame(body)
        destination.grid(row=4, column=0, sticky='ew')
        destination.columnconfigure(0, weight=1)
        ttk.Label(destination, text='Save to', style='Section.TLabel').grid(row=0, column=0, sticky='w', pady=(0, 5))
        self.folder_entry = ttk.Entry(destination, textvariable=self.destination, font=('Segoe UI', 10))
        self.folder_entry.grid(row=1, column=0, sticky='ew')
        self.browse = ttk.Button(destination, text='Browse…', command=self.choose_folder)
        self.browse.grid(row=1, column=1, sticky='ns', padx=(8, 0))
        ttk.Button(destination, text='Open folder', command=self.open_folder).grid(
            row=1, column=2, sticky='ns', padx=(8, 0))
        ttk.Label(destination, text='Collection name', style='Section.TLabel').grid(row=2, column=0, sticky='w', pady=(9, 5))
        self.collection_entry = ttk.Entry(destination, textvariable=self.collection, font=('Segoe UI', 10))
        self.collection_entry.grid(row=3, column=0, columnspan=3, sticky='ew')
        self.collection.trace_add('write', self.collection_changed)

        ttk.Frame(body, style='Rule.TFrame', height=1).grid(row=5, column=0, sticky='ew', pady=(15, 10))
        progress = ttk.Frame(body)
        progress.grid(row=6, column=0, sticky='ew', pady=(0, 10))
        progress.columnconfigure(0, weight=1)
        progress.rowconfigure(0, minsize=40)
        ttk.Label(progress, textvariable=self.status, style='Section.TLabel', wraplength=420).grid(
            row=0, column=0, sticky='w')
        ttk.Label(progress, textvariable=self.detail, style='Muted.TLabel').grid(row=0, column=1, sticky='e')
        self.progress = ttk.Progressbar(progress, variable=self.progress_value, mode='determinate', maximum=100)
        self.progress.grid(row=1, column=0, columnspan=2, sticky='ew', pady=(6, 0))

        actions = ttk.Frame(body)
        actions.grid(row=7, column=0, sticky='ew')
        actions.columnconfigure(1, weight=1)
        self.details_button = ttk.Button(actions, text='Show details', command=lambda: self.show_details(not self.details_visible))
        self.details_button.grid(row=0, column=0)
        self.stop = ttk.Button(actions, text='Cancel', command=self.cancel)
        self.stop.grid(row=0, column=2, padx=(0, 8))
        self.stop.grid_remove()
        self.download = ttk.Button(actions, text='Download', command=self.start, style='Primary.TButton', width=13)
        self.download.grid(row=0, column=3)

        self.log_frame = ttk.Frame(body)
        self.log_frame.grid(row=10, column=0, sticky='nsew', pady=(12, 0))
        self.log_frame.columnconfigure(0, weight=1)
        self.log_frame.rowconfigure(0, weight=1)
        self.log = tk.Text(self.log_frame, height=5, width=1, wrap='word', bg=PANEL, fg=MUTED,
                           selectbackground='#66548f', selectforeground=TEXT, relief='flat', borderwidth=0,
                           highlightthickness=1, highlightbackground=BORDER, highlightcolor=FOCUS,
                           padx=8, pady=6, font=('Segoe UI', 10), state='disabled')
        self.log.grid(row=0, column=0, sticky='nsew')
        self.log_scrollbar = ttk.Scrollbar(self.log_frame, command=self.log.yview, style='Details.Vertical.TScrollbar')
        self.log_scrollbar.grid(row=0, column=1, sticky='ns')
        self.log_scrollbar.grid_remove()
        self.log.configure(yscrollcommand=self._update_log_scrollbar)
        self.log_frame.grid_remove()

        self.update_idletasks()
        self.compact_height = body.winfo_reqheight()
        self.minimum_width = max(580, body.winfo_reqwidth())
        self.minsize(self.minimum_width, self.compact_height)
        self.geometry(f'{max(self.minimum_width, 730)}x{self.compact_height}')
        self._style_title_bar()
        self.urls.focus_set()

    def _style_title_bar(self):
        if sys.platform != 'win32':
            return
        get_ancestor = ctypes.windll.user32.GetAncestor
        get_ancestor.argtypes = (ctypes.c_void_p, ctypes.c_uint)
        get_ancestor.restype = ctypes.c_void_p
        window = get_ancestor(self.winfo_id(), 2)
        set_attribute = ctypes.windll.dwmapi.DwmSetWindowAttribute
        set_attribute.argtypes = (ctypes.c_void_p, ctypes.c_uint, ctypes.c_void_p, ctypes.c_uint)
        dark = ctypes.c_int(1)
        if set_attribute(window, 20, ctypes.byref(dark), ctypes.sizeof(dark)) != 0:
            set_attribute(window, 19, ctypes.byref(dark), ctypes.sizeof(dark))
        for attribute, color in ((34, BORDER), (35, BG), (36, TEXT)):
            value = ctypes.c_uint(int.from_bytes(bytes.fromhex(color[1:]), 'little'))
            set_attribute(window, attribute, ctypes.byref(value), ctypes.sizeof(value))

    def _update_log_scrollbar(self, first, last):
        self.log_scrollbar.set(first, last)
        if float(first) <= 0 and float(last) >= 1:
            self.log_scrollbar.grid_remove()
        else:
            self.log_scrollbar.grid()

    def show_details(self, visible=True):
        if visible == self.details_visible:
            return
        self.details_visible = visible
        self.details_button.configure(text='Hide details' if visible else 'Show details')
        if visible:
            self.log_frame.grid()
        else:
            self.log_frame.grid_remove()
        height = self.compact_height + (134 if visible else 0)
        self.minsize(self.minimum_width, height)
        if self.state() == 'normal':
            size = max(height, self.winfo_height()) if visible else max(height, self.winfo_height() - 134)
            self.geometry(f'{self.winfo_width()}x{size}')

    def _leave_urls(self, event):
        widget = event.widget.tk_focusPrev() if event.state & 1 else event.widget.tk_focusNext()
        widget.focus_set()
        return 'break'

    def paste_urls(self):
        self.urls.focus_set()
        self.urls.event_generate('<<Paste>>')

    def open_releases(self):
        webbrowser.open('https://github.com/raffaele-pet/gallery-dl-Desktop/releases/latest')

    def choose_folder(self):
        folder = filedialog.askdirectory(initialdir=self.resolve_destination())
        if folder:
            self.destination.set(folder)

    def resolve_destination(self):
        value = os.path.expandvars(self.destination.get().strip())
        path = Path(value).expanduser()
        return (Path.home() / path if not path.is_absolute() else path).resolve()

    def collection_changed(self, *_):
        if not self._setting_collection and self.collection.get() != self._automatic_collection:
            self._automatic_collection = ''

    def url_changed(self, _event=None):
        if not self.urls.edit_modified():
            return
        self.urls.edit_modified(False)
        try:
            suggested = folder_name_from_url(normalize_urls(self.urls.get('1.0', 'end'))[0])
        except ValueError:
            return
        if not self.collection.get() or self.collection.get() == self._automatic_collection:
            self._setting_collection = True
            self.collection.set(suggested)
            self._automatic_collection = suggested
            self._setting_collection = False

    def target_folder(self):
        name = self.collection.get().strip()
        if not name:
            raise ValueError('Enter a folder name.')
        if name in ('.', '..') or any(char in name for char in '<>:"/\\|?*') or name.rstrip(' .') != name:
            raise ValueError('Use a single folder name without /, \\ or special characters.')
        if name.split('.')[0].upper() in {'CON', 'PRN', 'AUX', 'NUL', *(f'COM{i}' for i in range(1, 10)), *(f'LPT{i}' for i in range(1, 10))}:
            raise ValueError('This folder name is reserved by Windows.')
        return self.resolve_destination() / name

    def open_folder(self):
        try:
            folder = self.target_folder() if self.collection.get().strip() else self.resolve_destination()
            folder.mkdir(parents=True, exist_ok=True)
            os.startfile(folder)
        except (ValueError, OSError) as exc:
            messagebox.showerror('Folder unavailable', str(exc))

    def append(self, text):
        if not text.strip():
            return
        follow = self.log.yview()[1] >= 1
        self.log.configure(state='normal')
        self.log.insert('end', text + '\n')
        if follow:
            self.log.see('end')
        self.log.configure(state='disabled')

    def clear_details(self):
        self.log.configure(state='normal')
        self.log.delete('1.0', 'end')
        self.log.configure(state='disabled')

    def show_progress(self, percent=None):
        mode = str(self.progress.cget('mode'))
        if percent is None:
            if mode != 'indeterminate':
                self.progress_value.set(0)
                self.progress.configure(mode='indeterminate')
                self.progress.start(15)
        else:
            if mode != 'determinate':
                self.progress.stop()
                self.progress.configure(mode='determinate')
            self.progress_value.set(percent)

    def set_busy(self, value, updating=False):
        self.busy = value
        self.updating = updating
        state = 'disabled' if value else 'normal'
        for control in (self.download, self.paste, self.browse, self.folder_entry,
                        self.collection_entry, self.urls, self.images_check, self.videos_check,
                        self.separate_radio, self.together_radio):
            control.configure(state=state)
        self.tools_menu.entryconfigure('end', state=state)
        if value and not updating:
            self.stop.configure(state='normal')
            self.stop.grid()
        else:
            self.stop.grid_remove()

    def start(self):
        if self.busy:
            return
        try:
            urls = normalize_urls(self.urls.get('1.0', 'end'))
            if not self.destination.get().strip():
                raise ValueError('Choose a destination folder.')
            if not self.download_images.get() and not self.download_videos.get():
                raise ValueError('Select Images, Videos, or both.')
            destination = self.target_folder()
            destination.mkdir(parents=True, exist_ok=True)
        except (ValueError, OSError) as exc:
            messagebox.showerror('Check the URL or folder', str(exc))
            return
        try:
            STATE_FILE.write_text(json.dumps({
                'destination': self.destination.get().strip(),
                'images': self.download_images.get(),
                'videos': self.download_videos.get(),
                'separate_media': self.separate_media.get(),
            }), encoding='utf-8')
        except OSError:
            pass
        self.saved = self.existing = 0
        self.cancelled = False
        self.clear_details()
        self.detail.set('')
        self.set_busy(True)
        self.show_progress()
        self.status.set('Looking for media…')
        self.launch([str(APP_DIR / 'engine.py')], {
            'urls': urls,
            'destination': str(destination),
            'images': self.download_images.get(),
            'videos': self.download_videos.get(),
            'separate_media': self.separate_media.get(),
        })

    def launch(self, args, payload=None):
        # Spawn before enabling event processing: Cancel cannot race creation.
        try:
            self.process = subprocess.Popen([str(APP_DIR / '.venv/Scripts/python.exe'), '-u', *args],
                cwd=APP_DIR, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                encoding='utf-8', errors='replace', env={**os.environ, 'PYTHONIOENCODING': 'utf-8'},
                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            if payload is not None:
                self.process.stdin.write(json.dumps(payload) + '\n')
                self.process.stdin.flush()
            self.process.stdin.close()
        except OSError as exc:
            self.append(str(exc))
            self.status.set('Could not start. Run the installer again.')
            self.show_progress(0)
            self.show_details()
            self.set_busy(False)
            return
        proc = self.process
        def read():
            for line in proc.stdout:
                try:
                    event = json.loads(line)
                    if not isinstance(event, dict):
                        raise ValueError()
                except ValueError:
                    event = {'type': 'log', 'text': line.rstrip()}
                self.events.put(event)
            self.events.put({'type': 'exit', 'code': proc.wait(), 'update': payload is None})
        threading.Thread(target=read, daemon=True).start()

    def poll(self):
        while not self.events.empty():
            event = self.events.get_nowait()
            kind = event.get('type')
            if self.cancelled and kind in ('status', 'source', 'progress', 'error', 'done'):
                continue
            if kind == 'log':
                self.append(event.get('text', ''))
            elif kind == 'source':
                self.show_progress()
                self.status.set(f"Reading {event['text']}…")
                self.detail.set(f"Link {event['index']} of {event['count']}" if event['count'] > 1 else '')
            elif kind == 'status':
                self.show_progress()
                self.status.set(event.get('text', ''))
                self.detail.set('')
            elif kind == 'progress':
                percent = event['percent']
                self.show_progress(percent)
                label = event['label']
                self.status.set(label + (f' {int(percent)}%' if percent is not None else '…'))
                self.detail.set(event.get('speed', ''))
            elif kind == 'error':
                self.status.set('Could not download this item')
                self.append(event.get('text', ''))
            elif kind == 'file':
                self.existing += bool(event.get('existing'))
                self.saved += not event.get('existing', False)
                if not self.cancelled:
                    self.status.set('Checking for more media…')
                    self.detail.set(self.file_summary())
                    self.show_progress()
                if not event.get('existing'):
                    self.append('Saved: ' + event['name'])
            elif kind == 'done':
                if event.get('incomplete'):
                    self.status.set('Download incomplete')
                    self.append(event['text'])
                    self.show_details()
                    self.show_progress(0)
                else:
                    self.status.set('Download complete')
                    self.show_progress(100)
                self.detail.set(self.file_summary())
            elif kind == 'update_result':
                self.update_verified = True
                self.update_restart_required = bool(event.get('restart_required'))
            elif kind == 'exit':
                self.process = None
                self.set_busy(False)
                if self.cancelled:
                    self.status.set('Download canceled')
                    self.detail.set(self.file_summary())
                    self.show_progress(0)
                elif event.get('update'):
                    self.show_progress(0)
                    text = 'Update verified.'
                    if self.update_restart_required:
                        text += ' Reopen the app to load the updated interface.'
                    self.status.set(text if event['code'] == 0 and self.update_verified
                                    else 'Update failed or could not be verified. See the details.')
                    if event['code'] or not self.update_verified:
                        self.show_details()
                elif event['code'] != 0:
                    self.status.set('Download incomplete' if self.saved or self.existing else 'Download failed')
                    self.detail.set(self.file_summary())
                    self.show_details()
                    self.show_progress(0)
        self.after(100, self.poll)

    def file_summary(self):
        counts = [f'{self.saved} saved'] if self.saved else []
        if self.existing:
            counts.append(f'{self.existing} already present')
        return ' · '.join(counts)

    def cancel(self):
        if self.process and self.process.poll() is None:
            self.cancelled = True
            self.stop.configure(state='disabled')
            self.status.set('Canceling…')
            subprocess.Popen(['taskkill', '/PID', str(self.process.pid), '/T', '/F'],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))

    def update_engine(self):
        if not self.busy:
            self.cancelled = False
            self.update_restart_required = False
            self.update_verified = False
            self.set_busy(True, updating=True)
            self.clear_details()
            self.detail.set('')
            self.show_progress()
            self.status.set('Checking download engine updates…' if self.managed_install
                            else 'Checking app and engine updates…')
            self.launch([str(APP_DIR / 'maintenance.py'), *(['--dependencies-only'] if self.managed_install else [])])

    def close(self):
        if self.updating:
            return
        if self.busy and not messagebox.askyesno('Close?', 'Cancel the current operation and close?'):
            return
        self.cancel()
        self.destroy()


if __name__ == '__main__':
    if sys.platform == 'win32':
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass
    App().mainloop()
