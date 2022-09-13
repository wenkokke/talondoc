build:
	poetry build

build-doc:
	@# NOTE: Always clean the environment, because 'analyze_package' does
	@#       not use mtime to check if it should reanalyze a file, and throws
	@#       duplicate object entry errors if it finds duplicates, even if they
	@#       are defined in the same place in the same file.
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
