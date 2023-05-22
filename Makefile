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
serve: .venv/bin/activate
	@bash -c "source .venv/bin/activate; pip install -q .[docs]; python -m talondoc build ./example/docs ./example/docs/_build --server"

.PHONY: docs
docs: .venv/bin/activate
	@bash -c "source .venv/bin/activate; pip install -q .[docs]; python -m talondoc build ./example/docs ./example/docs/_build"

.PHONY: autogen
autogen: .venv/bin/activate
	@bash -c "source .venv/bin/activate; pip install -q .[docs]; ./example/autogen.sh"

.venv/bin/activate:
	@python -m venv .venv

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
