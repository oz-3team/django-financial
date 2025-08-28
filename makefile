.PHONY: run migrate lint test

migrate:
	python manage.py migrate

docker:
