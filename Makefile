#################################################################################
# Tests
#################################################################################

.PHONY: test
test:
	tox

#################################################################################
# Build Docs
#################################################################################

.PHONY: serve
serve:
	@python -m venv .venv
	@.venv/bin/python -m http.server --directory ./example/docs/_build/html

.PHONY: docs
docs: .venv/
	@python -m venv .venv
	@bash -c "source .venv/bin/activate; pip install -q .[docs]; ./example/build.sh"

#################################################################################
# Version management
#################################################################################

.PHONY: bump-patch
bump-patch:
	@pipx run bumpver update --patch

.PHONY: bump-minor
bump-minor:
	@pipx run bumpver update --minor

.PHONY: bump-major
bump-major:
	@pipx run bumpver update --major
