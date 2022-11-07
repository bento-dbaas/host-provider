import json
import logging
from traceback import print_exc
from bson import json_util, ObjectId
from flask import Flask, request, jsonify, make_response
from flask_cors import CORS
from flask_httpauth import HTTPBasicAuth
from raven.contrib.flask import Sentry
from host_provider.settings import APP_USERNAME, APP_PASSWORD, SENTRY_DSN
from host_provider.settings import LOGGING_LEVEL
from host_provider.credentials.base import CredentialAdd
from host_provider.providers import get_provider_to
from host_provider.models import Host, IP

from dbaas_base_provider.log import log_this

# TODO: remove duplicate code and write more tests

app = Flask(__name__)
auth = HTTPBasicAuth()
cors = CORS(app)
if SENTRY_DSN:
    sentry = Sentry(app, dsn=SENTRY_DSN)

logging.basicConfig(level=LOGGING_LEVEL)

@auth.verify_password
def verify_password(username, password):
    if APP_USERNAME and username != APP_USERNAME:
        return False

    if APP_PASSWORD and password != APP_PASSWORD:
        return False

    return True

def build_provider(provider_name, env, engine):
    provider_cls = get_provider_to(provider_name)
    return provider_cls(env, engine, dict(request.headers))

@app.route(
    "/<string:provider_name>/<string:env>/prepare", methods=['POST']
)
@auth.login_required
@log_this
def prepare(provider_name, env):
    data = request.get_json()
    group = data.get("group", None)
    name = data.get("name", None)
    engine = data.get("engine", None)
    ports = data.get("ports", [])

    if not (group and name and engine):
        return response_invalid_request("invalid data {}".format(data))

    try:
        provider = build_provider(provider_name, env, engine)
        provider.prepare(name, group, engine, ports)
    except Exception as e:
        print_exc()
        return response_invalid_request(str(e))
    return response_created()


@app.route("/<string:provider_name>/<string:env>/host/new", methods=['POST'])
@auth.login_required
@log_this
def create_host(provider_name, env):
    data = request.get_json()
    group = data.get("group", None)
    name = data.get("name", None)
    engine = data.get("engine", None)
    cpu = data.get("cpu", None)
    memory = data.get("memory", None)
    zone = data.get("zone", None)
    team_name = data.get("team_name", None)
    database_name = data.get("database_name", "")
    static_ip_id = data.get("static_ip_id", "")
    service_account = data.get("service_account", "")

    # TODO improve validation and response
    if not (group and name and engine and cpu and memory):
        return response_invalid_request("invalid data {}".format(data))

    provider = build_provider(provider_name, env, engine)
    extra_params = {
        'team_name': team_name,
        'database_name': database_name,
        'port': data.get('port', None),
        'volume_name': data.get('volume_name', None),
        'node_ip': data.get('node_ip', ''),
        'init_user': data.get('init_user', ''),
        'init_password': data.get('init_password', ''),
        'static_ip_id': static_ip_id,
        'service_account': service_account
    }
    for attempt in range(provider.create_attempts):
        try:
            created_host_metadata = provider.create_host(
                cpu, memory, name, group, zone, **extra_params
            )
            host_obj = provider.create_host_object(
                provider, data, env, created_host_metadata, static_ip_id
            )
            provider.associate_ip_with_host(host_obj, static_ip_id)
            return response_created(address=host_obj.address, id=host_obj.id)
        except Exception as e:
            print_exc()
            if attempt == provider.create_attempts - 1:
                return response_invalid_request(str(e))


@app.route("/<string:provider_name>/<string:env>/ip/", methods=['POST'])
@auth.login_required
@log_this
def create_ip(provider_name, env):
    data = request.get_json()
    group = data.get("group", None)
    name = data.get("name", None)
    engine = data.get("engine", None)

    # TODO improve validation and response
    if not (group and name and engine):
        return response_invalid_request("invalid data {}".format(data))

    provider = build_provider(provider_name, env, engine)

    ip = provider.create_static_ip(group, name)
    if ip:
        return response_created(
            address=ip.address,
            identifier=ip.name,
            id=ip.id
        )
    return response_empty_content()


@app.route(
    "/<string:provider_name>/<string:env>/ip/<string:ip_name>",
    methods=['DELETE']
)
@auth.login_required
@log_this
def destroy_ip(provider_name, env, ip_name):
    provider = build_provider(provider_name, env, "")
    provider.destroy_static_ip(ip_name)
    ip = IP.get(name=ip_name)
    ip.delete_instance()
    return response_ok()


@app.route("/<string:provider_name>/<string:env>/host/stop", methods=['POST'])
@auth.login_required
@log_this
def stop_host(provider_name, env):
    data = request.get_json()
    host_id = data.get("host_id", None)

    # TODO improve validation and response
    if not host_id:
        return response_invalid_request("invalid data {}".format(data))

    try:
        host = Host.get(id=host_id)
    except Host.DoesNotExist:
        return response_not_found(host_id)

    try:
        provider = build_provider(provider_name, env, host.engine)
        provider.stop(host.identifier)
    except Exception as e:  # TODO What can get wrong here?
        print_exc()  # TODO Improve log
        return response_invalid_request(str(e))

    return response_ok()


@app.route("/<string:provider_name>/<string:env>/host/start", methods=['POST'])
@auth.login_required
@log_this
def start_host(provider_name, env):
    data = request.get_json()
    host_id = data.get("host_id", None)

    # TODO improve validation and response
    if not host_id:
        return response_invalid_request("invalid data {}".format(data))

    try:
        host = Host.get(id=host_id)
    except Host.DoesNotExist:
        return response_not_found(host_id)

    try:
        provider = build_provider(provider_name, env, host.engine)
        provider.start(host)
    except Exception as e:  # TODO What can get wrong here?
        print_exc()  # TODO Improve log
        return response_invalid_request(str(e))

    return response_ok()


@app.route(
    "/<string:provider_name>/<string:env>/host/resize", methods=['POST']
)
@auth.login_required
@log_this
def resize_host(provider_name, env):
    data = request.get_json()
    host_id = data.get("host_id", None)
    cpus = data.get("cpus", None)
    memory = data.get("memory", None)

    # TODO improve validation and response
    if not cpus or not host_id or not memory:
        return response_invalid_request(
            "cpus, host_id and memory are required. Payload: {}".format(data)
        )

    try:
        host = Host.get(id=host_id)
    except Host.DoesNotExist:
        return response_not_found(host_id)

    try:
        provider = build_provider(provider_name, env, host.engine)
        if int(cpus) == host.cpu and int(memory) == host.memory:
            logging.error(
                "Notting to resize for host {}, offering already done".format(
                    host.id
                )
            )
            return response_ok()
        provider.resize(host, cpus, memory)
    except Exception as e:  # TODO What can get wrong here?
        print_exc()  # TODO Improve log
        return response_invalid_request(str(e))

    host.cpu = int(cpus)
    host.memory = int(memory)
    host.save()
    return response_ok()


@app.route(
    "/<string:provider_name>/<string:env>/host/reinstall", methods=['POST']
)
@auth.login_required
@log_this
def reinstall_host(provider_name, env):
    data = request.get_json()
    host_id = data.get("host_id", None)
    engine = data.get("engine", None)
    service_account = data.get("service_account", None)
    extra_params = {
        'team_name': data.get("team_name", None),
        'database_name': data.get("database_name", None),
        'group': data.get("group", None),
        'service_account': service_account
    }

    # TODO improve validation and response
    if not host_id:
        return response_invalid_request(
            "host_id are required. Payload: {}".format(data)
        )

    try:
        host = Host.get(id=host_id)
    except Host.DoesNotExist:
        return response_not_found(host_id)

    try:
        provider = build_provider(provider_name, env, host.engine)
        provider.restore(host, engine, **extra_params)
        if engine and engine != host.engine:
            host.engine = engine
            host.save()
    except Exception as e:  # TODO What can get wrong here?
        print_exc()  # TODO Improve log
        return response_invalid_request(str(e))

    return response_ok()


@app.route(
    "/<string:provider_name>/<string:env>/host/<host_id>", methods=['DELETE']
)
@auth.login_required
@log_this
def destroy_host(provider_name, env, host_id):
    # TODO improve validation and response
    if not host_id:
        return response_invalid_request("invalid data")

    try:
        host = Host.get(id=host_id)
    except Host.DoesNotExist:
        return response_not_found(host_id)

    try:
        provider = build_provider(provider_name, env, host.engine)
        provider.destroy(
            group=host.group,
            identifier=host.identifier
        )
    except Exception as e:  # TODO What can get wrong here?
        print_exc()  # TODO Improve log
        return response_invalid_request(str(e))

    host.delete_instance()

    return response_ok()


@app.route(
    "/<string:provider_name>/<string:env>/clean/<string:name>",
    methods=['DELETE']
)
@auth.login_required
@log_this
def clean(provider_name, env, name):
    if not name:
        return response_invalid_request("invalid data")

    try:
        provider = build_provider(provider_name, env, None)
        provider.clean(name)
    except Exception as e:
        print_exc()
        return response_invalid_request(str(e))
    return response_ok()


@app.route("/<string:provider_name>/<string:env>/host/metadata", methods=['POST'])
@auth.login_required
@log_this
def update_host_metadata(provider_name, env):
    data = request.get_json()
    host_id = data.get("host_id", None)

    # TODO improve validation and response
    if not host_id:
        return response_invalid_request("invalid data {}".format(data))

    try:
        host = Host.get(id=host_id)
    except Host.DoesNotExist:
        return response_not_found(host_id)

    try:
        provider = build_provider(provider_name, env, host.engine)
        provider.update_host_metadata(host.identifier)
    except Exception as e:  # TODO What can get wrong here?
        print_exc()  # TODO Improve log
        return response_invalid_request(str(e))

    return response_ok()


@app.route(
    "/<string:provider_name>/<string:env>/host/configure", methods=['POST']
)
@auth.login_required
@log_this
def configure(provider_name, env):
    data = request.get_json()
    host = data.get("host", None)
    group = data.get("group", None)
    engine = data.get("engine", None)
    configuration = data.get("configuration", None)
    if not host or not group or not engine or not configuration:
        return response_invalid_request(
            ("host, group, engine and configuration required. "
             "Payload: {}").format(data)
        )
    try:
        provider = build_provider(provider_name, env, engine)
        provider.configure(host, group, configuration)
    except Exception as e:
        print_exc()
        return response_invalid_request(str(e))
    return response_ok()


@app.route(
    "/<string:provider_name>/<string:env>/host-ids/<group_id>/", methods=['GET']
)
@auth.login_required
@log_this
def get_hosts_ids(provider_name, env, group_id):
    try:
        provider = build_provider(provider_name, env, None)
        host_ids = provider.get_host_ids(group_id)
    except Exception as e:
        print_exc()
        return response_invalid_request(str(e))
    return response_ok(**{"ids": host_ids})


@app.route(
    "/<string:provider_name>/<string:env>/host-names/<group_id>/", methods=['GET']
)
@auth.login_required
@log_this
def get_hosts_names(provider_name, env, group_id):
    try:
        provider = build_provider(provider_name, env, None)
        host_names = provider.get_host_names(group_id)
    except Exception as e:
        print_exc()
        return response_invalid_request(str(e))
    return response_ok(**{"names": host_names})


@app.route(
    "/<string:provider_name>/<string:env>/host/configure/<string:host>",
    methods=['DELETE']
)
@auth.login_required
@log_this
def configure_delete(provider_name, env, host):
    try:
        provider = build_provider(provider_name, env, None)
        provider.remove_configuration(host)
    except Exception as e:
        print_exc()
        return response_invalid_request(str(e))
    return response_ok()


def _host_info(provider_name, env, host_id, refresh=False):
    if not host_id:
        return response_invalid_request("Missing parameter host_id")

    try:
        host = Host.get(id=host_id, environment=env)
        provider = build_provider(provider_name, env, host.engine)
        if refresh:
            provider.refresh_metadata(host)
        database_host_metadata = host.to_dict
        if hasattr(provider, 'fqdn'):
            database_host_metadata.update({'fqdn': provider.fqdn(host)})
        return response_ok(**database_host_metadata)
    except Host.DoesNotExist:
        return response_not_found(host_id)


@app.route(
    "/<string:provider_name>/<string:env>/host/<host_id>/", methods=['GET']
)
@auth.login_required
@log_this
def get_host(provider_name, env, host_id):
    return _host_info(provider_name, env, host_id)


@app.route(
    "/<string:provider_name>/<string:env>/host/<host_id>/refresh/",
    methods=['GET']
)
@auth.login_required
@log_this
def get_host_refresh(provider_name, env, host_id):
    return _host_info(provider_name, env, host_id, True)


@app.route(
    "/<string:provider_name>/<string:env>/status/<host_id>", methods=['GET']
)
@auth.login_required
@log_this
def status_host(provider_name, env, host_id):
    if not host_id:
        return response_invalid_request("Missing parameter host_id")

    try:
        host = Host.get(id=host_id, environment=env)
        provider = build_provider(provider_name, env, host.engine)
        host_status, version_id = provider.get_status(host)
        return response_ok(host_status=host_status, version_id=version_id)
    except Host.DoesNotExist:
        return response_not_found(host_id)


@app.route(
    "/<string:provider_name>/<string:env>/credential/new", methods=['POST']
)
@auth.login_required
@log_this
def create_credential(provider_name, env):
    data = request.get_json()
    try:
        provider = build_provider(provider_name, env, None)
        success, resp = provider.credential_add(data)
    except Exception as e:
        return response_invalid_request(str(e))
    else:
        if not success:
            return response_created(
                status_code=422, success=success, reason=str(resp)
            )
        return response_created(success=success, id=str(resp))


@app.route(
    "/<string:provider_name>/credentials", methods=['GET']
)
@auth.login_required
@log_this
def get_all_credential(provider_name):
    try:
        provider = build_provider(provider_name, None, None)
        credential = provider.build_credential().credential
        return make_response(
            json.dumps(
                list(map(lambda x: x, credential.find({}))),
                default=json_util.default
            )
        )
    except Exception as e:
        return response_invalid_request(str(e))


@app.route(
    "/<string:provider_name>/credential/<string:uuid>", methods=['GET']
)
@auth.login_required
@log_this
def get_credential(provider_name, uuid):
    try:
        provider = build_provider(provider_name, None, None)
        credential = provider.build_credential().credential
        return make_response(
            json.dumps(
                credential.find_one({'_id': ObjectId(uuid)}),
                default=json_util.default
            )
        )
    except Exception as e:
        return response_invalid_request(str(e))


@app.route(("/<string:provider_name>/<string:env>/credential/<string:cpus>"
            "/<string:memory>"), methods=['GET'])
@auth.login_required
@log_this
def get_credential_by_offering(provider_name, env, cpus, memory):
    try:
        provider = build_provider(provider_name, env, None)
        credential = provider.build_credential()
        return make_response(
            json.dumps(
                {'offering_id': credential.offering_to(cpus, memory)},
                default=json_util.default
            )
        )
    except Exception as e:
        return response_invalid_request(str(e))


@app.route(
    "/<string:provider_name>/credential/<string:uuid>", methods=['PUT']
)
@auth.login_required
@log_this
def update_credential(provider_name, uuid):
    data = request.get_json()
    if not data:
        return response_invalid_request("No data".format(data))

    try:
        provider = build_provider(provider_name, None, None)
        credential = provider.build_credential().credential

        data.get('_id') and data.pop('_id')

        return make_response(
            json.dumps(
                credential.update(
                    {'_id': ObjectId(uuid)},
                    data
                ),
                default=json_util.default
            )
        )
    except Exception as e:
        return response_invalid_request(str(e))


@app.route(
    "/<string:provider_name>/<string:env>/credential/", methods=['DELETE']
)

@auth.login_required
@log_this
def destroy_credential(provider_name, env):
    try:
        credential = CredentialAdd(provider_name, env, {})
        deleted = credential.delete()
    except Exception as e:
        return response_invalid_request(str(e))

    if deleted.deleted_count <= 0:
        return response_not_found("{}-{}".format(provider_name, env))

    return response_ok()


@app.route(
    "/<string:provider_name>/<string:env>/zones", methods=['GET']
)
@auth.login_required
@log_this
def list_zones(provider_name, env):
    try:
        provider = build_provider(provider_name, env, None)
        credential = provider.build_credential()
        return make_response(
            json.dumps(
                {
                    'zones': [
                        {
                            'name': zone['name'],
                            'is_active': zone['active']
                        } for zone in credential.all_zones.values()]
                },
                default=json_util.default
            )
        )
    except Exception as e:
        return response_invalid_request(str(e))


@app.route("/<string:provider_name>/<string:env>/sa/", methods=['POST'])
@auth.login_required
@log_this
def create_service_account(provider_name, env):
    data = request.get_json()
    name = data.get("name", None)

    # TODO improve validation and response
    if not name:
        return response_invalid_request("invalid data {}".format(data))

    provider = build_provider(provider_name, env, "")

    service_account = provider.create_service_account(name)
    if service_account:
        return response_created(
            service_account=service_account
        )
    return response_empty_content()


@app.route(
    "/<string:provider_name>/<string:env>/sa/<string:sa>",
    methods=['DELETE']
)
@auth.login_required
@log_this
def destroy_service_account(provider_name, env, sa):
    provider = build_provider(provider_name, env, "")
    provider.destroy_service_account(sa)
    return response_ok()


@app.route(
    "/<string:provider_name>/<string:env>/sa-set-role/<string:sa>",
    methods=['POST'])
@auth.login_required
@log_this
def sa_set_role(provider_name, env, sa):
    provider = build_provider(provider_name, env, "")

    set_role = provider.sa_set_role(sa)
    if set_role:
        return response_ok()
    return response_empty_content()

@app.route('/')
def default_route():
    response = "host-provider, from dbaas/dbdev <br>"
    try:
        f = open("./build_info.txt")
        response += f.readline()
    except:
        response += "build_info.txt not found"
    return response

def response_invalid_request(error, status_code=500):
    return _response(status_code, error=error)


def response_not_found(identifier):
    error = "Could not found with {}".format(identifier)
    return _response(404, error=error)


def response_created(status_code=201, **kwargs):
    return _response(status_code, **kwargs)


def response_ok(message=None, **kwargs):
    if not message and not kwargs:
        message = "ok"
    response = {}
    if message:
        response['message'] = message
    if kwargs:
        response.update(**kwargs)
    return _response(200, **response)


def response_empty_content():
    return _response(200, **{})


def _response(status, **kwargs):
    content = jsonify(**kwargs)
    return make_response(content, status)
