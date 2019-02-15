from PyQt5.QtCore import Qt
from PyQt5.QtGui import QCursor
from PyQt5.QtWidgets import QApplication
import functools

def processing_cursor(cursor=QCursor(Qt.WaitCursor)):
    def processing_cursor_decorator(func):
        @functools.wraps(func)
        def func_wrapper(*args, **kwargs):
            show_processing_cursor(cursor=cursor)

            try:
               return func(*args, **kwargs)
            except Exception:
                hide_processing_cursor()
                raise
            finally:
                hide_processing_cursor()

        return func_wrapper
    return processing_cursor_decorator

def show_processing_cursor(cursor=QCursor(Qt.WaitCursor)):
    QApplication.setOverrideCursor(cursor)
    QApplication.processEvents()

def hide_processing_cursor():
    QApplication.restoreOverrideCursor()
    QApplication.processEvents()