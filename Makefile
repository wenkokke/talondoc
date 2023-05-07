#################################################################################
# Tests
#################################################################################

.PHONY: test
test: mypy
	tox

#################################################################################
# Build Docs
#################################################################################

.PHONY: autogen
autogen: .venv/
	@.venv/bin/pip install -q .[docs] 2>/dev/null
	@.venv/bin/python -m talondoc autogen \
		--output-dir "example/docs/knausj_talon" \
		--package-name "user" \
		--sphinx-root "example/docs" \
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
		"example/knausj_talon/"

.PHONY: mypy
mypy: .venv/
	@.venv/bin/pip install -q .[mypy]
	@.venv/bin/python -m mypy talondoc

.venv/:
	python -m venv .venv

#################################################################################
# Version management
#################################################################################

.PHONY: bump-patch
bump-patch: require-poetry
	@pipx run bumpver update --patch

.PHONY: bump-minor
bump-minor: require-poetry
	@pipx run bumpver update --minor

.PHONY: bump-major
bump-major: require-poetry
	@pipx run bumpver update --major
