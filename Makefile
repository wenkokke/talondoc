build:
	poetry build

build-doc:
	poetry install -E docs
	@# NOTE:
	@#   Some entries store AST nodes, which do not currently support
	@#   unpickling. They pickle via __reduce__, and don't automatically
	@#   unpickle. Once that is fixed, we no longer need to discard the
	@#   cache on every run.
	poetry run sphinx-build -M "clean" "example/docs" "example/docs/_build"
	poetry run talondoc autogen \
		--output-dir example/docs/knausj_talon \
		--project 'knausj_talon' \
		--package-name user \
		--no-generate-conf \
		--exclude '*.py' \
		--exclude 'modes/wake_up_wav2letter.talon' \
		example/knausj_talon/
	poetry run sphinx-build -M "html" "example/docs" "example/docs/_build"

serve:
	@(cd docs/_build/html && npx browser-sync -ss)

clean:
	@git clean -dfqX

bump-patch:
	@poetry run bumpver update --patch

bump-minor:
	@poetry run bumpver update --minor

bump-major:
	@poetry run bumpver update --major

.PHONY: build build-doc serve clean test bump-patch bump-minor bump-major
