#!/bin/sh

# POSIX compliant method for 'pipefail':
fail=$(mktemp)

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
output_dir="$script_dir/docs"

[ ! -s "$fail" ] && \
  PYTHONUTF8=1 \
  talondoc autogen \
  --output-dir "$output_dir/knausj_talon" \
  --sphinx-root "$output_dir" \
  --project 'knausj_talon' \
  --package-name "user" \
  --no-generate-conf \
  --exclude "conftest.py" \
  --exclude "test/stubs/talon/__init__.py" \
  --exclude "test/stubs/talon/grammar.py" \
  --exclude "test/stubs/talon/experimental/textarea.py" \
  --exclude "test/repo_root_init.py" \
  --exclude "test/test_code_modified_function.py" \
  --exclude "test/test_create_spoken_forms.py" \
  --exclude "test/test_dictation.py" \
  --exclude "test/test_formatters.py" \
  --exclude "plugin/draft_editor/draft_editor.py" \
  --exclude "plugin/talon_draft_window/__init__.py" \
  --exclude "plugin/talon_draft_window/draft_talon_helpers.py" \
  --exclude "plugin/talon_draft_window/draft_ui.py" \
  --exclude "plugin/talon_draft_window/test_draft_ui.py" \
  "$script_dir/knausj_talon/" \
  || echo > "$fail"

[ ! -s "$fail" ] && \
  PYTHONUTF8=1 \
  sphinx-build \
  -M "clean" \
  "$output_dir" \
  "$output_dir/_build" \
  || echo > "$fail"

[ ! -s "$fail" ] && \
  PYTHONUTF8=1 \
  sphinx-build \
  -M "html" \
  "$output_dir" \
  "$output_dir/_build" \
  || echo > "$fail"

if [ -s "$fail" ]; then
    rm "$fail"
    echo "Could not build example documentation for knausj_talon" >&2
    exit 1
else
    rm "$fail"
    exit 0
fi
