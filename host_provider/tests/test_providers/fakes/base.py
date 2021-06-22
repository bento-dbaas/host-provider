from collections import namedtuple
from unittest.mock import MagicMock
from host_provider.models import Host


FAKE_ENGINE = namedtuple(
    'FakeEngine', 'id name'
    )(
        'fake_engine_id',
        'fake_engine_name'
    )

# FAKE_HOST_OBJ = type('FakeHostObj', '', 'id name zone identifier recreating')
# FAKE_HOST = type(
#     'FakeHost',
#     (object,),
#     {
#         'id': 'fake_id',
#         'name': 'fake_host_name',
#         'zone': 'fake_host_zone',
#         'identifier': 'fake_identifier',
#         'recreating': False
#     }
# )
# FAKE_HOST = FAKE_HOST_OBJ(
#     'fake_id', 'fake_host_name', 'fake_host_zone', 'fake_identifier', False
# )

FAKE_HOST = MagicMock(spec=Host)
FAKE_HOST.id = 'fake_id'
FAKE_HOST.name = 'fake_host_name'
FAKE_HOST.zone = 'fake_host_zone'
FAKE_HOST.identifier = 'fake_identifier'
FAKE_HOST.recreating = False

FAKE_TAGS = {
    'servico_de_negocio': 'servico_de_negocio',
    'cliente': 'cliente',
    'team_slug_name': 'team_slug_name',
    'create_at': 'create_at',
    'engine': 'engine',
    'infra_name': 'infra_name',
    'database_name': 'database_name',
    'origin': 'dbaas'
}