dev:
	export FLASK_DEBUG=1
	export LIBCLOUD_CA_CERTS_PATH=""


run:
	FLASK_APP=main.py
	python -m flask run


test:
	coverage run --source=./ -m unittest discover --start-directory ./tests -p "*.py"
