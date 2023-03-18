build:
	poetry install -E docs
	poetry run sh ./example/build.sh

serve:
	python3 -m http.server --directory ./example/docs/_build/html

test:
	tox

clean:
	@git clean -dfqX

bump-patch:
	@poetry run bumpver update --patch

bump-minor:
	@poetry run bumpver update --minor

bump-major:
	@poetry run bumpver update --major

.PHONY: build serve clean bump-patch bump-minor bump-major
