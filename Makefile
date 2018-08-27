dev:
	export FLASK_DEBUG=1
	export LIBCLOUD_CA_CERTS_PATH=""


run:
	export DBAAS_AWS_PROXY=;export FLASK_APP=./host_provider/main.py; python -m flask run


test:
	export DBAAS_AWS_PROXY=;coverage run --source=./ -m unittest discover --start-directory ./tests -p "*.py"


test_report: test
	coverage report -m
