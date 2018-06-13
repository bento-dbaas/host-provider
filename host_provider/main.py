from flask import Flask, request, jsonify, make_response
from host_provider.credentials.base import CredentialAdd
from host_provider.providers import get_provider_to
from host_provider.models import Host
from traceback import print_exc
from flask_cors import CORS
from bson import json_util, ObjectId
import json
# TODO: remove duplicate code and write more tests


app = Flask(__name__)
cors = CORS(app)



@app.route("/<string:provider_name>/<string:env>/host/new", methods=['POST'])
def create_host(provider_name, env):
    data = request.get_json()
    group = data.get("group", None)
    name = data.get("name", None)
    engine = data.get("engine", None)
    cpu = data.get("cpu", None)
    memory = data.get("memory", None)

    # TODO improve validation and response
    if not(group and name and engine and cpu and memory):
        return response_invalid_request("invalid data {}".format(data))

    try:
        provider_cls = get_provider_to(provider_name)
        provider = provider_cls(env, engine)
        node = provider.create_host(cpu, memory, name, group)
    except Exception as e:  # TODO What can get wrong here?
        print_exc()  # TODO Improve log
        return response_invalid_request(str(e))

    address = node.private_ips[0]
    host = Host(
        name=name, group=group, engine=engine, environment=env,
        cpu=cpu, memory=memory, provider=provider_name, identifier=node.id,
        address=address
    )
    host.save()

    return response_created(address=address, id=host.id)


@app.route("/<string:provider_name>/<string:env>/host/stop", methods=['POST'])
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


@app.route("/<string:provider_name>/<string:env>/host/resize", methods=['POST'])
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
        provider.resize(host.identifier, cpus, memory)
    except Exception as e:  # TODO What can get wrong here?
        print_exc()  # TODO Improve log
        return response_invalid_request(str(e))

    return response_ok()


@app.route("/<string:provider_name>/<string:env>/host/reinstall", methods=['POST'])
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
def destroy_host(provider_name, env, host_id):
    # TODO improve validation and response
    if not host_id:
        return response_invalid_request("invalid data")

    try:
        host = Host.get(id=host_id)
    except Host.DoesNotExist:
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
def get_host(provider_name, env, host_id):
    if not host_id:
        return response_invalid_request("Missing parameter host_id")

    try:
        host = Host.get(id=host_id, environment=env)
        return response_created(**host.to_dict)
    except Host.DoesNotExist:
        return response_not_found(host_id)


@app.route(
    "/<string:provider_name>/<string:env>/credential/new", methods=['POST']
)
def create_credential(provider_name, env):
    data = request.get_json()
    if not data:
        return response_invalid_request("No data".format(data))

    try:
        provider_cls = get_provider_to(provider_name)
        provider = provider_cls(env, None)
        success, credential_id = provider.credential_add(data)
    except Exception as e:
        return response_invalid_request(str(e))
    else:
        return response_created(success=success, id=str(credential_id))


@app.route(
    "/<string:provider_name>/credentials", methods=['GET']
)
def get_all_credential(provider_name):
    try:
        provider_cls = get_provider_to(provider_name)
        provider = provider_cls(None, None)
        print(provider.build_credential())
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


@app.route(
    "/<string:provider_name>/credential/<string:uuid>", methods=['PUT']
)
def update_credential(provider_name, uuid):
    data = request.get_json()
    if not data:
        return response_invalid_request("No data".format(data))

    try:
        provider_cls = get_provider_to(provider_name)
        provider = provider_cls(None, None)
        credential = provider.build_credential().credential

        # remove _id from data
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
def destroy_credential(provider_name, env):
    try:
        credential = CredentialAdd(provider_name, env, {})
        deleted = credential.delete()
    except Exception as e:
        return response_invalid_request(str(e))

    if deleted.deleted_count <= 0:
        return response_not_found("{}-{}".format(provider_name, env))

    return response_ok()


def response_invalid_request(error, status_code=500):
    return _response(status_code, error=error)


def response_not_found(identifier):
    error = "Could not found with {}".format(identifier)
    return _response(404, error=error)


def response_created(status_code=201, **kwargs):
    return _response(status_code, **kwargs)


def response_ok(message=None):
    if not message:
        message = "ok"

    return _response(200, message=message)


def _response(status, **kwargs):
    content = jsonify(**kwargs)
    return make_response(content, status)
