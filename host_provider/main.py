import json
import logging
from traceback import print_exc
from bson import json_util, ObjectId
from flask import Flask, request, jsonify, make_response
from flask_cors import CORS
from flask_httpauth import HTTPBasicAuth
from host_provider.settings import APP_USERNAME, APP_PASSWORD
from host_provider.credentials.base import CredentialAdd
from host_provider.providers import get_provider_to
from host_provider.models import Host
# TODO: remove duplicate code and write more tests


app = Flask(__name__)
auth = HTTPBasicAuth()
cors = CORS(app)


@auth.verify_password
def verify_password(username, password):
    if APP_USERNAME and username != APP_USERNAME:
        return False

    if APP_PASSWORD and password != APP_PASSWORD:
        return False

    return True


@app.route("/<string:provider_name>/<string:env>/host/new", methods=['POST'])
@auth.login_required
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

    # TODO improve validation and response
    if not(group and name and engine and cpu and memory):
        return response_invalid_request("invalid data {}".format(data))

    try:
        provider_cls = get_provider_to(provider_name)
        provider = provider_cls(env, engine)
        extra_params = {
            'team_name': team_name,
            'database_name': database_name
        }
        node = provider.create_host(
            cpu, memory, name, group, zone, **extra_params
        )
    except Exception as e:  # TODO What can get wrong here?
        print_exc()  # TODO Improve log
        return response_invalid_request(str(e))

    address = node.private_ips[0]
    host = Host(
        name=name, group=group, engine=engine, environment=env,
        cpu=cpu, memory=memory, provider=provider_name, identifier=node.id,
        address=address, zone=provider.credential._zone
    )
    host.save()

    return response_created(address=address, id=host.id)


@app.route("/<string:provider_name>/<string:env>/host/stop", methods=['POST'])
@auth.login_required
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
        provider_cls = get_provider_to(provider_name)
        provider = provider_cls(env, host.engine)
        provider.stop(host.identifier)
    except Exception as e:  # TODO What can get wrong here?
        print_exc()  # TODO Improve log
        return response_invalid_request(str(e))

    return response_ok()


@app.route("/<string:provider_name>/<string:env>/host/start", methods=['POST'])
@auth.login_required
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
        provider_cls = get_provider_to(provider_name)
        provider = provider_cls(env, host.engine)
        provider.start(host.identifier)
    except Exception as e:  # TODO What can get wrong here?
        print_exc()  # TODO Improve log
        return response_invalid_request(str(e))

    return response_ok()


@app.route(
    "/<string:provider_name>/<string:env>/host/resize", methods=['POST']
)
@auth.login_required
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
        provider_cls = get_provider_to(provider_name)
        provider = provider_cls(env, host.engine)
        if int(cpus) == host.cpu and int(memory) == host.memory:
            logging.error(
                "Notting to resize for host {}, offering already done".format(
                    host.id
                )
            )
            return response_ok()
        provider.resize(host.identifier, cpus, memory)
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
def reinstall_host(provider_name, env):
    data = request.get_json()
    host_id = data.get("host_id", None)
    engine = data.get("engine", None)

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
        provider_cls = get_provider_to(provider_name)
        provider = provider_cls(env, host.engine)
        provider.restore(host.identifier, engine)
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
def destroy_host(provider_name, env, host_id):
    # TODO improve validation and response
    if not host_id:
        return response_invalid_request("invalid data")

    try:
        host = Host.get(id=host_id)
    except Host.DoesNotExist:
        return response_ok()
        return response_not_found(host_id)

    try:
        provider_cls = get_provider_to(provider_name)
        provider = provider_cls(env, host.engine)
        provider.destroy(host.group, host.identifier)
    except Exception as e:  # TODO What can get wrong here?
        print_exc()  # TODO Improve log
        return response_invalid_request(str(e))

    host.delete_instance()

    return response_ok()


@app.route(
    "/<string:provider_name>/<string:env>/host/<host_id>", methods=['GET']
)
@auth.login_required
def get_host(provider_name, env, host_id):
    if not host_id:
        return response_invalid_request("Missing parameter host_id")

    try:
        host = Host.get(id=host_id, environment=env)
        database_host_metadata = host.to_dict
        provider_cls = get_provider_to(provider_name)
        provider = provider_cls(env, None)
        if hasattr(provider, 'fqdn'):
            database_host_metadata.update({'fqdn': provider.fqdn(host)})
        return response_ok(**database_host_metadata)
    except Host.DoesNotExist:
        return response_not_found(host_id)


@app.route(
    "/<string:provider_name>/<string:env>/credential/new", methods=['POST']
)
@auth.login_required
def create_credential(provider_name, env):
    data = request.get_json()
    if not data:
        return response_invalid_request("No data".format(data))

    try:
        provider_cls = get_provider_to(provider_name)
        provider = provider_cls(env, None)
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
def get_all_credential(provider_name):
    try:
        provider_cls = get_provider_to(provider_name)
        provider = provider_cls(None, None)
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
def get_credential(provider_name, uuid):
    try:
        provider_cls = get_provider_to(provider_name)
        provider = provider_cls(None, None)
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
def get_credential_by_offering(provider_name, env, cpus, memory):
    try:
        provider_cls = get_provider_to(provider_name)
        provider = provider_cls(env, None)
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
def update_credential(provider_name, uuid):
    data = request.get_json()
    if not data:
        return response_invalid_request("No data".format(data))

    try:
        provider_cls = get_provider_to(provider_name)
        provider = provider_cls(None, None)
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
def list_zones(provider_name, env):
    try:
        provider_cls = get_provider_to(provider_name)
        provider = provider_cls(env, None)
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


def _response(status, **kwargs):
    content = jsonify(**kwargs)
    return make_response(content, status)
