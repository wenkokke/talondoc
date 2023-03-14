#!/bin/sh

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
output_dir="${1-$script_dir/docs}"
output_dir="$(realpath $output_dir)"

talondoc autogen \
		--output-dir "$output_dir/knausj_talon" \
		--sphinx-root "$output_dir" \
		--project 'knausj_talon' \
		--package-name user \
		--no-generate-conf \
		--exclude 'conftest.py' \
		--exclude 'test/**' \
		--exclude '**/*.py' \
		"$script_dir/knausj_talon/"

sphinx-build -M "clean" "$output_dir" "$output_dir/_build"

sphinx-build -M "html" "$output_dir" "$output_dir/_build"
