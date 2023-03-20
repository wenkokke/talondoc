#################################################################################
# Common tasks
#################################################################################

.PHONY: default
default: test

.PHONY: docs
docs: require-poetry type-check
	@poetry install --all-extras
	@poetry run sh ./example/build.sh

.PHONY: serve
serve: require-poetry
	@poetry run python3 -m http.server --directory ./example/docs/_build/html

.PHONY: clean
clean: require-poetry
	@git clean -dfqX

.PHONY: test
test: require-tox type-check
	@tox

.PHONY: type-check
type-check: require-poetry
	@poetry install --all-extras
	@poetry run mypy talondoc


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
