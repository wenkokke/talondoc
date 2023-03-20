bump-patch:
	@poetry run bumpver update --patch

bump-minor:
	@poetry run bumpver update --minor

bump-major:
	@poetry run bumpver update --major

clean:
	@git clean -dfqX

docs:
	@poetry install -E docs
	@poetry run sh ./example/build.sh

serve:
	@python3 -m http.server --directory ./example/docs/_build/html

test:
	@tox

type:
	@poetry run mypy talondoc

.PHONY: bump-patch bump-minor bump-major clean docs serve
