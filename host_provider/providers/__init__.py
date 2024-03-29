from host_provider.providers.base import ProviderBase
from host_provider.providers.cloudstack import CloudStackProvider
from host_provider.providers.aws import AWSProvider
from host_provider.providers.k8s import K8sProvider
from host_provider.providers.gce import GceProvider
from host_provider.providers.azure import AzureProvider


def get_provider_to(provider_name):
    for cls in ProviderBase.__subclasses__():
        if cls.get_provider() == provider_name:
            return cls

    raise NotImplementedError("No provider to '{}'".format(provider_name))
