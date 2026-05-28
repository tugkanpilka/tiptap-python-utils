.PHONY: test build check clean

test:
	pytest -q

build:
	python -m build

check: build
	python -m twine check dist/*

clean:
	rm -rf build dist *.egg-info src/*.egg-info .pytest_cache
