#!/bin/

# POSIX compliant method for 'pipefail':
fail=$(mktemp)

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
output_dir="$script_dir/docs"

[ ! -s "$fail" ] && \
  python \
  -X utf8 \
  -m talondoc autogen \
  --output-dir "$output_dir/knausj_talon" \
  --sphinx-root "$output_dir" \
  --project 'knausj_talon' \
  --package-name user \
  --no-generate-conf \
  --exclude 'conftest.py' \
  --exclude 'test/**' \
  "$script_dir/knausj_talon/" \
  || echo > "$fail"

[ ! -s "$fail" ] && \
  sphinx-build \
  -M "clean" \
  "$output_dir" \
  "$output_dir/_build" \
  || echo > "$fail"

[ ! -s "$fail" ] && \
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
