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

FAKE_CREDENTIAL = {
    'provider': 'ec2',
    'mimOfSubnets': "1",
    'environment': 'dev',
    'region': 'sa-east-1',
    'keyname': 'elesbom',
    'security_group_id': 'fake_security_group_id',
    'access_id': 'fake_access_id',
    'secret_key': 'fake_secret_key',
    'templates': {
        'redis': 'fake_so_image_id'
    },
    'subnets': {
        'fake_subnet_id_1': {
            'id': 'fake_subnet_id_1',
            'name': 'fake_subnet_name_1',
            'active': True
        },
        'fake_subnet_id_2': {
            'id': 'fake_subnet_id_2',
            'name': 'fake_subnet_name_2',
            'active': True
        }
    }
}
