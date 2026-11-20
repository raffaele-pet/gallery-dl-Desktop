import tempfile
import unittest
from pathlib import Path
from tkinter import ttk
from unittest.mock import patch

import app


class InterfaceTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        with patch('app.STATE_FILE', Path(temporary.name) / 'preferences.json'):
            self.window = app.App()
        self.addCleanup(self.close_window)
        self.window.update()

    def close_window(self):
        self.window.progress.stop()
        for timer in self.window.tk.call('after', 'info'):
            self.window.tk.call('after', 'cancel', timer)
        self.window.destroy()

    def test_details_scrollbar_is_themed_and_only_visible_on_overflow(self):
        self.assertFalse(self.window.log_frame.winfo_ismapped())
        self.window.details_button.invoke()
        self.window.update()
        self.assertFalse(self.window.log_scrollbar.winfo_ismapped())
        for number in range(40):
            self.window.append(f'File {number}')
        self.window.update()
        self.assertTrue(self.window.log_scrollbar.winfo_ismapped())
        self.assertEqual(ttk.Style(self.window).lookup('Details.Vertical.TScrollbar', 'troughcolor'), app.PANEL)
        self.window.clear_details()
        self.window.update()
        self.assertFalse(self.window.log_scrollbar.winfo_ismapped())

    def test_status_and_bar_follow_transfer_until_the_job_finishes(self):
        self.window.set_busy(True)
        self.window.events.put({'type': 'progress', 'label': 'Downloading video', 'percent': 43.5, 'speed': '80 KiB/s'})
        self.window.poll()
        self.assertEqual(self.window.status.get(), 'Downloading video 43%')
        self.assertEqual(self.window.progress_value.get(), 43.5)
        self.assertEqual(self.window.detail.get(), '80 KiB/s')
        self.window.events.put({'type': 'file', 'name': 'clip.mp4', 'existing': False})
        self.window.events.put({'type': 'done', 'text': 'Completed', 'incomplete': False})
        self.window.events.put({'type': 'exit', 'code': 0, 'update': False})
        self.window.poll()
        self.assertEqual(self.window.progress_value.get(), 100)
        self.assertEqual(self.window.detail.get(), '1 saved')
        self.assertFalse(self.window.busy)
