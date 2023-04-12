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



# Docker part, for deploy, for GCP
# TODO, standardize with other providers
docker_build:
	GIT_BRANCH=$$(git branch --show-current); \
	GIT_COMMIT=$$(git rev-parse --short HEAD); \
	DATE=$$(date +"%Y-%M-%d_%T"); \
	INFO="date:$$DATE  branch:$$GIT_BRANCH  commit:$$GIT_COMMIT"; \
	docker build -t dbaas/host_provider --label git-commit=$(git rev-parse --short HEAD) --build-arg build_info="$$INFO" .

docker_run:
	make docker_stop
	docker rm host_provider
	docker run --name=host_provider -d -p 80:80 dbaas/host_provider 

docker_stop:
	docker stop host_provider	

docker_deploy_gcp:
	@echo "tag usada:${TAG}"
	@echo "exemplo de uso:"
	@echo "make docker_deploy_gcp TAG=v1.02"
	@echo "Checar as tags atuais: https://console.cloud.google.com/artifacts/docker/gglobo-dbaas-hub/us-east1/dbaas-docker-images?project=gglobo-dbaas-hub"
	make docker_deploy_build TAG=${TAG}
	make docker_deploy_push TAG=${TAG}

docker_deploy_build: 
	@echo "tag usada:${TAG}"
	@echo "exemplo de uso make docker_deploy_build TAG=v1.02"
	docker build . -t us-east1-docker.pkg.dev/gglobo-dbaas-hub/dbaas-docker-images/host-provider:${TAG}

docker_deploy_build:
	@echo "tag usada:${TAG}"
	@echo "exemplo de uso make docker_deploy_build TAG=v1.02"
	GIT_BRANCH=$$(git branch --show-current); \
	GIT_COMMIT=$$(git rev-parse --short HEAD); \
	DATE=$$(date +"%Y-%M-%d_%T"); \
	INFO="date:$$DATE  branch:$$GIT_BRANCH  commit:$$GIT_COMMIT"; \
	docker build . -t us-east1-docker.pkg.dev/gglobo-dbaas-hub/dbaas-docker-images/host-provider:${TAG} \
		--label git-commit=$(git rev-parse --short HEAD) \
		--build-arg build_info="$$INFO"

docker_deploy_push:
	@echo "tag usada:${TAG}"
	@echo "exemplo de uso make docker_deploy_push TAG=v1.02"
	docker push us-east1-docker.pkg.dev/gglobo-dbaas-hub/dbaas-docker-images/host-provider:${TAG}