.PHONY: all clean pytest coverage flake8 black mypy isort tles

# Run all the checks which do not change files
all: isort black flake8 pytest

# Run the unit tests using `pytest`
pytest:
	poetry run pytest src tests

# Lint the code using `flake8`
flake8:
	poetry run flake8 src tests

# Automatically format the code using `black`
black:
	poetry run black src tests

# Order the imports using `isort`
isort:
	poetry run isort src tests

tles:
	poetry run python -c "import pandoraspacecraft as psc; psc.utils.convert_tles()"

# Serve docs
serve:
	$(CMD) mkdocs serve

deploy:
	$(CMD) mkdocs gh-deploy --force