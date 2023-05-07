#################################################################################
# Common tasks
#################################################################################

.PHONY: test
test:
	tox

.venv/:
	python -m venv .venv

.PHONY: install
install: .venv/
	.venv/bin/pip install .[test]

.PHONY: autogen
autogen: .venv/ | install
	.venv/bin/python -m talondoc autogen \
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
	.venv/bin/python -m mypy talondoc

#################################################################################
# Version management
#################################################################################

.PHONY: bump-patch
bump-patch: require-poetry
	@poetry run bumpver update --patch

.PHONY: bump-minor
bump-minor: require-poetry
	@poetry run bumpver update --minor

.PHONY: bump-major
bump-major: require-poetry
	@poetry run bumpver update --major


#################################################################################
# Dependencies with reasonable error messages
#################################################################################

.PHONY: require-tox
require-tox:
ifeq (,$(wildcard $(shell which tox)))
	@echo "The command you called requires tox"
	@echo "See: https://tox.wiki/en/latest/installation.html"
	@exit 1
endif

.PHONY: require-poetry
require-poetry:
ifeq (,$(wildcard $(shell which poetry)))
	@echo "The command you called requires Poetry"
	@echo "See: https://python-poetry.org/docs/#installation"
	@exit 1
endif
