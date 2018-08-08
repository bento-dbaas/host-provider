from collections import namedtuple

NodeSize = namedtuple("EC2BasicInfo", "id, extra, ram")


LIST_SIZES = [
    NodeSize(1, {'cpu': 1}, 512),
    NodeSize(2, {'cpu': 1}, 1024),
    NodeSize(3, {'cpu': 2}, 1024)
]

FAKE_TAGS = {
    'cliente-id': 'fake_client-id',
    'componente-id': 'fake_component_id',
    'consumo-detalhado': True,
    'equipe-id': 'fake_team_id',
    'servico-de-negocio-id': 'fake_business_service_id',
    'sub-componente-id': 'fake_sub_component_id'
}
