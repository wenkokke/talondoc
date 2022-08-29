from talon import Context, actions, clip # type: ignore

ctx = Context()
ctx.matches = r"""
os: mac
"""


@ctx.action_class("edit")
class EditActions:
    @staticmethod
    def copy():
        actions.key("cmd-c")

    @staticmethod
    def cut():
        actions.key("cmd-x")

    @staticmethod
    def delete():
        actions.key("backspace")

    @staticmethod
    def delete_line():
        actions.edit.select_line()
        actions.edit.delete()

    # edit.delete_paragraph()
    #   Delete paragraph under cursor

    # edit.delete_sentence()
    #   Delete sentence under cursor

    @staticmethod
    def delete_word():
        actions.edit.select_word()
        actions.edit.delete()

    @staticmethod
    def down():
        actions.key("down")

    # edit.extend_again()
    #   Extend selection again in the same way

    # edit.extend_column(n: int)
    #   Extend selection to column <n>

    @staticmethod
    def extend_down():
        actions.key("shift-down")

    @staticmethod
    def extend_file_end():
        actions.key("cmd-shift-down")

    @staticmethod
    def extend_file_start():
        actions.key("cmd-shift-up")

    @staticmethod
    def extend_left():
        actions.key("shift-left")

    # edit.extend_line(n: int)
    #   Extend selection to include line <n>

    @staticmethod
    def extend_line_down():
        actions.key("shift-down")

    @staticmethod
    def extend_line_end():
        actions.key("cmd-shift-right")

    @staticmethod
    def extend_line_start():
        actions.key("cmd-shift-left")

    @staticmethod
    def extend_line_up():
        actions.key("shift-up")

    @staticmethod
    def extend_page_down():
        actions.key("cmd-shift-pagedown")

    @staticmethod
    def extend_page_up():
        actions.key("cmd-shift-pageup")

    # edit.extend_paragraph_end()
    #   Extend selection to the end of the current paragraph

    # edit.extend_paragraph_next()
    #   Extend selection to the start of the next paragraph

    # edit.extend_paragraph_previous()
    #   Extend selection to the start of the previous paragraph

    # edit.extend_paragraph_start()
    #   Extend selection to the start of the current paragraph

    @staticmethod
    def extend_right():
        actions.key("shift-right")

    # edit.extend_sentence_end()
    #   Extend selection to the end of the current sentence

    # edit.extend_sentence_next()
    #   Extend selection to the start of the next sentence

    # edit.extend_sentence_previous()
    #   Extend selection to the start of the previous sentence

    # edit.extend_sentence_start()
    #   Extend selection to the start of the current sentence

    @staticmethod
    def extend_up():
        actions.key("shift-up")

    @staticmethod
    def extend_word_left():
        actions.key("shift-alt-left")

    @staticmethod
    def extend_word_right():
        actions.key("shift-alt-right")

    @staticmethod
    def file_end():
        actions.key("cmd-down cmd-left")

    @staticmethod
    def file_start():
        actions.key("cmd-up cmd-left")

    @staticmethod
    def find(text: str = None):
        actions.key("cmd-f")
        if text:
            actions.insert(text)

    @staticmethod
    def find_next():
        actions.key("cmd-g")

    @staticmethod
    def find_previous():
        actions.key("cmd-shift-g")

    @staticmethod
    def indent_less():
        actions.key("cmd-left delete")

    @staticmethod
    def indent_more():
        actions.key("cmd-left tab")

    # edit.jump_column(n: int)
    #   Move cursor to column <n>

    # edit.jump_line(n: int)
    #   Move cursor to line <n>

    @staticmethod
    def jump_line(n: int):
        # This action does nothing, but is used in select_line
        pass

    @staticmethod
    def left():
        actions.key("left")

    # edit.line_clone()
    #   Create a new line identical to the current line

    @staticmethod
    def line_down():
        actions.key("down home")

    @staticmethod
    def line_end():
        actions.key("cmd-right")

    @staticmethod
    def line_insert_down():
        actions.edit.line_end()
        actions.key("enter")

    @staticmethod
    def line_insert_up():
        actions.edit.line_start()
        actions.key("enter up")

    @staticmethod
    def line_start():
        actions.key("cmd-left")

    # edit.line_swap_down()
    #   Swap the current line with the line below

    # edit.line_swap_up()
    #   Swap the current line with the line above

    @staticmethod
    def line_up():
        actions.key("up cmd-left")

    # edit.move_again()
    #   Move cursor again in the same way

    @staticmethod
    def page_down():
        actions.key("pagedown")

    @staticmethod
    def page_up():
        actions.key("pageup")

    # edit.paragraph_end()
    #   Move cursor to the end of the current paragraph

    # edit.paragraph_next()
    #   Move cursor to the start of the next paragraph

    # edit.paragraph_previous()
    #   Move cursor to the start of the previous paragraph

    # edit.paragraph_start()
    #   Move cursor to the start of the current paragraph

    @staticmethod
    def paste():
        actions.key("cmd-v")

    @staticmethod
    def paste_match_style():
        actions.key("cmd-alt-shift-v")

    @staticmethod
    def print():
        actions.key("cmd-p")

    @staticmethod
    def redo():
        actions.key("cmd-shift-z")

    @staticmethod
    def right():
        actions.key("right")

    @staticmethod
    def save():
        actions.key("cmd-s")

    @staticmethod
    def save_all():
        actions.key("cmd-shift-s")

    @staticmethod
    def select_all():
        actions.key("cmd-a")

    @staticmethod
    def select_line(n: int = None):
        # If jump_line is not implemented, this action simply selects the current line.
        if n:
            actions.edit.jump_line(n)
        actions.key("cmd-right cmd-shift-left")

    @staticmethod
    def select_lines(a: int, b: int):
        # If b is smaller, swap a and b:
        if b < a:
            a, b = b, a
        # If jump_line is not implemented, this action simply selects
        # a number of lines equal to the difference between <a> and <b>.
        actions.edit.jump_line(a)
        actions.edit.line_start()
        for _ in range(0, b - a):
            actions.edit.extend_line_down()
        actions.edit.extend_line_end()

    @staticmethod
    def select_none():
        actions.key("escape")

    # edit.select_paragraph()
    #   Select the entire nearest paragraph

    # edit.select_sentence()
    #   Select the entire nearest sentence

    @staticmethod
    def select_word():
        actions.edit.right()
        actions.edit.word_left()
        actions.edit.extend_word_right()

    @staticmethod
    def selected_text() -> str:
        with clip.capture() as s:
            actions.edit.copy()
        try:
            return s.get()
        except clip.NoChange:
            return ""

    # edit.selection_clone()
    #   Insert a copy of the current selection

    # edit.sentence_end()
    #   Move cursor to the end of the current sentence

    # edit.sentence_next()
    #   Move cursor to the start of the next sentence

    # edit.sentence_previous()
    #   Move cursor to the start of the previous sentence

    # edit.sentence_start()
    #   Move cursor to the start of the current sentence

    @staticmethod
    def undo():
        actions.key("cmd-z")

    @staticmethod
    def up():
        actions.key("up")

    @staticmethod
    def word_left():
        actions.key("alt-left")

    @staticmethod
    def word_right():
        actions.key("alt-right")

    @staticmethod
    def zoom_in():
        actions.key("cmd-=")

    @staticmethod
    def zoom_out():
        actions.key("cmd--")

    @staticmethod
    def zoom_reset():
        actions.key("cmd-0")
