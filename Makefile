run:
	export LIBCLOUD_CA_CERTS_PATH=""; export FLASK_DEBUG=1; export VERIFY_SSL_CERT=1; export DBAAS_AWS_PROXY=;export FLASK_APP=./host_provider/main.py; python -m flask run --host 0.0.0.0 --port 5002

test:
	export DBAAS_AWS_PROXY=;coverage run --source=./ -m unittest discover --start-directory ./host_provider/tests -p "*.py"

test_report: test
	coverage report -m

shell:
	export LIBCLOUD_CA_CERTS_PATH=""; export FLASK_DEBUG=1; export VERIFY_SSL_CERT=1; export DBAAS_AWS_PROXY=; PYTHONPATH=. ipython

deploy_dev:
	tsuru app-deploy -a host-provider-dev .

deploy_prod:
	tsuru app-deploy -a host-provider .

db_initialize:
	@python -m host_provider.dbscripts.initialize

db_migrate:
	@python -m host_provider.dbscripts.migrate