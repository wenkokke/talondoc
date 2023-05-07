#################################################################################
# Tests
#################################################################################

.PHONY: test
test:
	tox

#################################################################################
# Build Docs
#################################################################################

.PHONY: docs
docs: .venv/
	@bash -c "source .venv/bin/activate; pip install -q .[docs]; ./example/build.sh"

.venv/:
	python -m venv .venv

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
