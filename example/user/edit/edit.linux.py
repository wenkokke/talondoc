from talon import Context, actions  # type: ignore

ctx = Context()
ctx.matches = r"""
os: linux
"""


@ctx.action_class("edit")
class EditActions:
    @staticmethod
    def copy():
        actions.key("ctrl-c")

    @staticmethod
    def cut():
        actions.key("ctrl-x")

    @staticmethod
    def delete():
        actions.key("backspace")

    @staticmethod
    def delete_line():
        actions.edit.select_line()
        actions.edit.delete()

    @staticmethod
    def delete_word():
        actions.edit.select_word()
        actions.edit.delete()

    @staticmethod
    def down():
        actions.key("down")

    @staticmethod
    def extend_down():
        actions.key("shift-down")

    @staticmethod
    def extend_file_end():
        actions.key("shift-ctrl-end")

    @staticmethod
    def extend_file_start():
        actions.key("shift-ctrl-home")

    @staticmethod
    def extend_left():
        actions.key("shift-left")

    @staticmethod
    def extend_line_down():
        actions.key("shift-down")

    @staticmethod
    def extend_line_end():
        actions.key("shift-end")

    @staticmethod
    def extend_line_start():
        actions.key("shift-home")

    @staticmethod
    def extend_line_up():
        actions.key("shift-up")

    @staticmethod
    def extend_page_down():
        actions.key("shift-pagedown")

    @staticmethod
    def extend_page_up():
        actions.key("shift-pageup")

    @staticmethod
    def extend_right():
        actions.key("shift-right")

    @staticmethod
    def extend_up():
        actions.key("shift-up")

    @staticmethod
    def extend_word_left():
        actions.key("ctrl-shift-left")

    @staticmethod
    def extend_word_right():
        actions.key("ctrl-shift-right")

    @staticmethod
    def file_end():
        actions.key("ctrl-end")

    @staticmethod
    def file_start():
        actions.key("ctrl-home")

    @staticmethod
    def find(text: str = None):
        actions.key("ctrl-f")
        actions.actions.insert(text)

    @staticmethod
    def find_next():
        actions.key("f3")

    @staticmethod
    def indent_less():
        actions.key("home delete")

    @staticmethod
    def indent_more():
        actions.key("home tab")

    @staticmethod
    def left():
        actions.key("left")

    @staticmethod
    def line_down():
        actions.key("down home")

    @staticmethod
    def line_end():
        actions.key("end")

    @staticmethod
    def line_insert_up():
        actions.key("home enter up")

    @staticmethod
    def line_start():
        actions.key("home")

    @staticmethod
    def line_up():
        actions.key("up home")

    @staticmethod
    def page_down():
        actions.key("pagedown")

    @staticmethod
    def page_up():
        actions.key("pageup")

    @staticmethod
    def paste():
        actions.key("ctrl-v")

    @staticmethod
    def print():
        actions.key("ctrl-p")

    @staticmethod
    def redo():
        actions.key("ctrl-y")

    @staticmethod
    def right():
        actions.key("right")

    @staticmethod
    def save():
        actions.key("ctrl-s")

    @staticmethod
    def save_all():
        actions.key("ctrl-shift-s")

    @staticmethod
    def select_all():
        actions.key("ctrl-a")

    @staticmethod
    def select_line(n: int = None):
        actions.key("end shift-home")

    @staticmethod
    def select_none():
        actions.key("right")

    @staticmethod
    def select_word():
        actions.edit.right()
        actions.edit.word_left()
        actions.edit.extend_word_right()

    @staticmethod
    def undo():
        actions.key("ctrl-z")

    @staticmethod
    def up():
        actions.key("up")

    @staticmethod
    def word_left():
        actions.key("ctrl-left")

    @staticmethod
    def word_right():
        actions.key("ctrl-right")

    @staticmethod
    def zoom_in():
        actions.key("ctrl-+")

    @staticmethod
    def zoom_out():
        actions.key("ctrl--")

    @staticmethod
    def zoom_reset():
        actions.key("ctrl-0")
