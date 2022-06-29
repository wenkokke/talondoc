# from pathlib import Path
# from tree_sitter import Language, Parser

# TALON_LANGUAGE_LIB = "build/talon.so"
# TALON_LANGUAGE_REPO = "vendor/tree-sitter-talon"

# Language.build_library(TALON_LANGUAGE_LIB, [TALON_LANGUAGE_REPO])

# TALON_LANGUAGE = Language(TALON_LANGUAGE_LIB, "talon")

# parser = Parser()
# parser.set_language(TALON_LANGUAGE)

# KNAUSJ_TALON = Path.home().glob("Projects/knausj_talon/**/*.talon")

# for talon_file in KNAUSJ_TALON:
#   print(talon_file)
#   talon_file_bytes = talon_file.read_bytes()
#   tree = parser.parse(talon_file_bytes)
#   print(tree.root_node.sexp())