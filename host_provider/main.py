from flask import Flask, request, jsonify, make_response
from host_provider.providers import get_provider_to
from host_provider.models import Host
from traceback import print_exc

app = Flask(__name__)


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
        node = provider._create_host(cpu, memory, name, group)
    except Exception as e:
        print_exc()
        return response_invalid_request(str(e))

    address = node.private_ips[0]
    host = Host(
        name=name, group=group, engine=engine, environment=env,
        cpu=cpu, memory=memory, provider=provider_name, identifier=node.id,
        address=address
    )
    host.save()

    return response_created(address=address, id=host.id)


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


def response_invalid_request(error, status_code=500):
    return _response(status_code, error=error)


def response_created(status_code=201, **kwargs):
    return _response(status_code, **kwargs)


def _response(status, **kwargs):
    content = jsonify(**kwargs)
    return make_response(content, status)
