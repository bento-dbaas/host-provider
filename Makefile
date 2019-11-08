run:
	export LIBCLOUD_CA_CERTS_PATH=""; export FLASK_DEBUG=1; export VERIFY_SSL_CERT=1; export DBAAS_AWS_PROXY=;export FLASK_APP=./host_provider/main.py; python -m flask run --port 5002

test:
	export DBAAS_AWS_PROXY=;coverage run --source=./ -m unittest discover --start-directory ./tests -p "*.py"

test_report: test
	coverage report -m

shell:
	export LIBCLOUD_CA_CERTS_PATH=""; export FLASK_DEBUG=1; export VERIFY_SSL_CERT=1; export DBAAS_AWS_PROXY=; PYTHONPATH=. ipython
