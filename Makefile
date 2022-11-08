build:
	poetry build

build-doc:
	sh ./scripts/build-doc

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
