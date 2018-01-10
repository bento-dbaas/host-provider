from flask import Flask, request, jsonify, make_response
from providers import factory


app = Flask(__name__)


@app.route("/<string:provider_name>/<string:env>/host/new", methods=['POST'])
def create_host(provider_name, env):
    data = request.get_json()
    engine = data.get("engine", None)
    cpu = data.get("cpu", None)
    memory = data.get("memory", None)
    name = data.get("name", None)

    if not(engine and cpu and memory and name):
        return response_invalid_request("invalid data {}".format(data))

    try:
        provider = factory(provider_name, env, engine)
        node = provider.create_host(cpu, memory, name)
    except Exception as e:
        return response_invalid_request(str(e))
    else:
        return response_created(ip=node.private_ips[0], id=node.id)


def response_invalid_request(error, status_code=500):
    return _response(status_code, error=error)


def response_created(status_code=201, **kwargs):
    return _response(status_code, **kwargs)


def _response(status, **kwargs):
    content = jsonify(**kwargs)
    return make_response(content, status)
