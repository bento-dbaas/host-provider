import requests
from os import getenv
from host_provider.settings import TEAM_API_URL


class TeamClient(object):

    API_URL = TEAM_API_URL
    SUB_COMPONENTS_BY_ENGINE = {
        'redis': 'c672e379db9f43409fc15458dc96195f',
        'mongodb': 'ea26a7fddb9f43409fc15458dc96199b',
        'mysql': 'c672e379db9f43409fc15458dc96195f'
    }

    @staticmethod
    def get_by_name(name):
        res = requests.get(
            u'{}/{}'.format(TEAM_API_URL, name)
        )

        if res.ok:
            return res.json()

        return {}

    @classmethod
    def make_tags(cls, team_name, engine):

        if not team_name or not cls.API_URL:
            return {}

        team = cls.get_by_name(team_name)

        if not team:
            return {}

        return {
            'servico-de-negocio-id': team.get('servico-de-negocio'),
            'equipe-id': team.get('id'),
            'componente-id': 'ce72e379db9f43409fc15458dc961962',
            'sub-componente-id': cls.SUB_COMPONENTS_BY_ENGINE[engine.split('_')[0]],
            'cliente-id': team.get('cliente'),
            'consumo-detalhado': True
        }
