# Find

scout this:
  edit.find(edit.selected_text())

scout next:
  edit.find_next()

scout previous:
  edit.find_previous()


# Save

file save:
	edit.save()

file save all:
	edit.save_all()


# Undo/Redo

nope:
	edit.undo()

redo:
	edit.redo()

# Navigation

goal:
  edit.left()

gore:
  edit.right()

goop:
  edit.up()

gown:
  edit.down()

moon:
  edit.word_left()

step:
  edit.word_right()

head:
  edit.line_start()

tail:
  edit.line_end()

scroll up:
  edit.page_up()

scroll down:
  edit.page_down()

header:
  edit.file_start()

tailor:
  edit.file_end()


# Insert

slurp:
  edit.line_insert_up()

slap:
	edit.line_insert_down()

clone line:
  edit.line_clone()


# Intent

(indent | [in] dent):
  edit.indent_more()

out dent:
  edit.indent_less()


# Swap

drag down:
  edit.line_swap_down()

drag up:
  edit.line_swap_up()


# Select

cork:
  edit.select_none()

grab up:
  edit.extend_up()

grab down:
  edit.extend_down()

grab left:
  edit.extend_left()

grab right:
  edit.extend_right()

(take|grab) word:
  edit.select_word()

grab (moon|word left):
  edit.extend_word_left()

grab (step|word right):
  edit.extend_word_right()

(take|grab) line:
  edit.select_line()

grab head:
  edit.extend_line_start()

grab tail:
  edit.extend_line_end()

(take|grab) file:
  edit.select_all()

grab header:
  edit.extend_file_start()

grab tailor:
  edit.extend_file_end()


# Delete

gobble:
    edit.extend_word_right()
    edit.extend_word_left()
    insert(" ")

wipe [goal]:
	  edit.delete()

wipe gore:
    edit.right()
    edit.delete()

clear word:
    edit.select_word()
    edit.delete()

clear (moon|word left):
    edit.extend_word_left()
    edit.delete()

clear (step|word right):
    edit.extend_word_right()
    edit.delete()

clear line:
    edit.select_line()
    edit.delete()

clear head:
    edit.extend_line_start()
    edit.delete()

clear tail:
    edit.extend_line_end()
    edit.delete()

clear file:
    edit.select_all()
    edit.delete()

clear header:
    edit.extend_file_start()
    edit.delete()

clear tailor:
    edit.extend_file_end()
    edit.delete()


# Copy

copy (it | that):
	edit.copy()

copy word:
    edit.select_word()
    edit.copy()

copy (moon|word left):
    edit.extend_word_left()
    edit.copy()

copy (step|word right):
    edit.extend_word_right()
    edit.copy()

copy line:
    edit.select_line()
    edit.copy()

copy head:
    edit.extend_line_start()
    edit.copy()

copy tail:
    edit.extend_line_end()
    edit.copy()

copy file:
    edit.select_all()
    edit.copy()

copy header:
    edit.extend_file_start()
    edit.copy()

copy tailor:
    edit.extend_file_end()
    edit.copy()


# Cut

cut (it | that):
	edit.cut()

cut word:
    edit.select_word()
    edit.cut()

cut (moon|word left):
    edit.extend_word_left()
    edit.cut()

cut (step|word right):
    edit.extend_word_right()
    edit.cut()

cut line:
    edit.select_line()
    edit.cut()

cut head:
    edit.extend_line_start()
    edit.cut()

cut tail:
    edit.extend_line_end()
    edit.cut()

cut file:
    edit.select_all()
    edit.cut()

cut header:
    edit.extend_file_start()
    edit.cut()

cut tailor:
    edit.extend_file_end()
    edit.cut()


# Paste

paste (it | that):
	edit.paste()

paste match:
    edit.paste_match_style()
