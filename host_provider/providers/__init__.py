from host_provider.providers.base import ProviderBase
from host_provider.providers.cloudstack import CloudStackProvider


def factory(provider_name, environment, engine):
    for cls in ProviderBase.__subclasses__():
        if cls.get_provider() == provider_name:
            return cls(environment, engine)

    raise NotImplementedError("No provider to '{}'".format(provider_name))
