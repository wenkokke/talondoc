#!/bin/sh

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
output_dir="$script_dir/docs"

[ ! -s "$fail" ] && \
  PYTHONUTF8=1 \
  talondoc \
  autogen \
  --output-dir "$output_dir/knausj_talon" \
  --sphinx-root "$output_dir" \
  --project 'knausj_talon' \
  --package-name "user" \
  --package-dir "$script_dir/knausj_talon/" \
  --format "${TALONDOC_FORMAT:-rst}" \
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
  || echo > "$fail"
