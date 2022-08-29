# Minimal complete definition:
#
# edit.copy()
#   Copy selection to clipboard
# edit.cut()
#   Cut selection to clipboard
# edit.delete()
#   Delete selection
# edit.delete_line()
#   Delete line under cursor
# edit.delete_paragraph()
#   Delete paragraph under cursor
# edit.delete_sentence()
#   Delete sentence under cursor
# edit.delete_word()
#   Delete word under cursor
# edit.down()
#   Move cursor down one row
# edit.extend_again()
#   Extend selection again in the same way
# edit.extend_column(n: int)
#   Extend selection to column <n>
# edit.extend_down()
#   Extend selection down one row
# edit.extend_file_end()
#   Extend selection to end of file
# edit.extend_file_start()
#   Extend selection to start of file
# edit.extend_left()
#   Extend selection left one column
# edit.extend_line(n: int)
#   Extend selection to include line <n>
# edit.extend_line_down()
#   Extend selection down one full line
# edit.extend_line_end()
#   Extend selection to end of line
# edit.extend_line_start()
#   Extend selection to start of line
# edit.extend_line_up()
#   Extend selection up one full line
# edit.extend_page_down()
#   Extend selection down one page
# edit.extend_page_up()
#   Extend selection up one page
# edit.extend_paragraph_end()
#   Extend selection to the end of the current paragraph
# edit.extend_paragraph_next()
#   Extend selection to the start of the next paragraph
# edit.extend_paragraph_previous()
#   Extend selection to the start of the previous paragraph
# edit.extend_paragraph_start()
#   Extend selection to the start of the current paragraph
# edit.extend_right()
#   Extend selection right one column
# edit.extend_sentence_end()
#   Extend selection to the end of the current sentence
# edit.extend_sentence_next()
#   Extend selection to the start of the next sentence
# edit.extend_sentence_previous()
#   Extend selection to the start of the previous sentence
# edit.extend_sentence_start()
#   Extend selection to the start of the current sentence
# edit.extend_up()
#   Extend selection up one row
# edit.extend_word_left()
#   Extend selection left one word
# edit.extend_word_right()
#   Extend selection right one word
# edit.file_end()
#   Move cursor to end of file (start of line)
# edit.file_start()
#   Move cursor to start of file
# edit.find(text: str = None)
#   Open Find dialog, optionally searching for text
# edit.find_next()
#   Select next Find result
# edit.find_previous()
#   Select previous Find result
# edit.indent_less()
#   Remove a tab stop of indentation
# edit.indent_more()
#   Add a tab stop of indentation
# edit.left()
#   Move cursor left one column
# edit.line_clone()
#   Create a new line identical to the current line
# edit.line_down()
#   Move cursor to start of line below
# edit.line_end()
#   Move cursor to end of line
# edit.line_insert_down()
#   Insert line below cursor
# edit.line_insert_up()
#   Insert line above cursor
# edit.line_start()
#   Move cursor to start of line
# edit.line_swap_down()
#   Swap the current line with the line below
# edit.line_swap_up()
#   Swap the current line with the line above
# edit.line_up()
#   Move cursor to start of line above
# edit.move_again()
#   Move cursor again in the same way
# edit.page_down()
#   Move cursor down one page
# edit.page_up()
#   Move cursor up one page
# edit.paragraph_end()
#   Move cursor to the end of the current paragraph
# edit.paragraph_next()
#   Move cursor to the start of the next paragraph
# edit.paragraph_previous()
#   Move cursor to the start of the previous paragraph
# edit.paragraph_start()
#   Move cursor to the start of the current paragraph
# edit.paste()
#   Paste clipboard at cursor
# edit.paste_match_style()
#   Paste clipboard without style information
# edit.print()
#   Open print dialog
# edit.redo()
#   Redo
# edit.right()
#   Move cursor right one column
# edit.save()
#   Save current document
# edit.save_all()
#   Save all open documents
# edit.select_all()
#   Select all text in the current document
# edit.select_line(n: int = None)
#   Select entire line <n>, or current line
# edit.select_lines(a: int, b: int)
#   Select entire lines from <a> to <b>
# edit.select_none()
#   Clear current selection
# edit.select_paragraph()
#   Select the entire nearest paragraph
# edit.select_sentence()
#   Select the entire nearest sentence
# edit.select_word()
#   Select word under cursor
# edit.selected_text() -> str
#   Get currently selected text
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
# edit.undo()
#   Undo
# edit.up()
#   Move cursor up one row
# edit.word_left()
#   Move cursor left one word
# edit.word_right()
#   Move cursor right one word
