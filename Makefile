.PHONY: coverage cov

coverage:
	coverage run --branch --source=app --omit='*/test_*.py' -m pytest -q && coverage report -m

cov: coverage


test:
	pytest -q --disable-warnings --maxfail=1