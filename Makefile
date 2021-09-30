run:
	export LIBCLOUD_CA_CERTS_PATH=""; export FLASK_DEBUG=1; export VERIFY_SSL_CERT=1; export DBAAS_AWS_PROXY=;export FLASK_APP=./host_provider/main.py; python -m flask run --host 0.0.0.0 --port 5002

test:
	export DBAAS_HTTP_PROXY=; export DBAAS_HTTPS_PROXY=;coverage run --source=./ -m unittest discover --start-directory ./host_provider/tests -p "*.py"

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

docker_mysql_57:
	docker-compose run --publish="3306:3306" mysqldb57

docker_mongo:
	docker-compose run --publish="27017:27017" mongodb42

mysql_shell:
	mysql -h ${DBAAS_MYSQL_HOSTS} -u  ${DBAAS_MYSQL_USER} -p${DBAAS_MYSQL_PASSWORD}