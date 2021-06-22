import requests
import datetime
from slugify import slugify
from host_provider.settings import TEAM_API_URL


class TeamClient(object):

    API_URL = TEAM_API_URL

    @staticmethod
    def slugify(name):
        return slugify(
            name,
            regex_pattern=r'[^\w\S-]'
        )

    @staticmethod
    def get_by_name(cls, name):
        slugify_name = cls.slugify(name)
        url = '{}/slug/{}'.format(cls.API_URL,slugify_name)
        res = requests.get(url)
        if res.ok:
            return res.json()
        return {}

    @classmethod
    def make_tags(cls,
        team_name='', engine_name='', infra_name='', database_name=''):

        if not team_name or not cls.API_URL:
            return {}

        team = cls.get_by_name(team_name)

        if not team:
            return {}

        tags = {
            'servico_de_negocio': team.get('servico-de-negocio'),
            'cliente': team.get('cliente'),
            'team_slug_name': team.get('slug'),
            'create_at': datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S'),
            'engine': engine_name,
            'infra_name': infra_name,
            'database_name': database_name,
            'origin': 'dbaas'
        }

        return tags
