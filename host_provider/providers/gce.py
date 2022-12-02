import json
import logging
import httplib2
import google_auth_httplib2

from time import sleep
import googleapiclient.discovery
from google.oauth2 import service_account
from googleapiclient.errors import HttpError
from host_provider.settings import HTTP_PROXY
from host_provider.credentials.gce import CredentialGce, CredentialAddGce
from host_provider.providers.base import ProviderBase
from host_provider.models import Host, IP
from host_provider.settings import TEAM_API_URL
from dbaas_base_provider.team import TeamClient


LOG = logging.getLogger(__name__)


class WrongStatusError(Exception):
    pass


class StaticIPNotFoundError(Exception):
    pass


class ServiceAccountRoleCheckError(Exception):
    pass


class NotDefinedError(Exception):
    pass


class GceProvider(ProviderBase):
    WAIT_ATTEMPTS = 100
    WAIT_TIME = 3

    def get_service_account_credentials(self):
        service_account_data = self.credential.content['service_account']
        service_account_data['private_key'] = service_account_data[
            'private_key'
        ].replace('\\n', '\n')

        credentials = service_account.Credentials.from_service_account_info(
            service_account_data,
            scopes=self.credential.scopes
        )
        return credentials

    def get_authorized_http(self, credentials):
        _, host, port = HTTP_PROXY.split(':')
        try:
            port = int(port)
        except ValueError:
            raise EnvironmentError('HTTP_PROXY incorrect format')

        proxied_http = httplib2.Http(proxy_info=httplib2.ProxyInfo(
            httplib2.socks.PROXY_TYPE_HTTP,
            host.replace('//', ''),
            port
        ))

        authorized_http = google_auth_httplib2.AuthorizedHttp(
                            credentials,
                            http=proxied_http)

        return authorized_http

    def get_cloudidentity_service_client(self):
        credentials = self.get_service_account_credentials()

        if HTTP_PROXY:
            authorized_http = self.get_authorized_http(credentials)

            service = googleapiclient.discovery.build(
                'cloudidentity',
                'v1',
                http=authorized_http)
        else:
            service = googleapiclient.discovery.build(
                'cloudidentity',
                'v1',
                credentials=credentials,
            )

        return service

    def get_pubsub_service_client(self):
        credentials = self.get_service_account_credentials()

        if HTTP_PROXY:
            authorized_http = self.get_authorized_http(credentials)

            service = googleapiclient.discovery.build(
                'pubsub',
                'v1',
                http=authorized_http)
        else:
            service = googleapiclient.discovery.build(
                'pubsub',
                'v1',
                credentials=credentials,
            )

        return service

    def get_resource_manager_service_client(self):
        credentials = self.get_service_account_credentials()

        if HTTP_PROXY:
            authorized_http = self.get_authorized_http(credentials)

            service = googleapiclient.discovery.build(
                'cloudresourcemanager',
                'v1',
                http=authorized_http)
        else:
            service = googleapiclient.discovery.build(
                'cloudresourcemanager',
                'v1',
                credentials=credentials,
            )

        return service

    def build_client(self):
        credentials = self.get_service_account_credentials()

        if HTTP_PROXY:
            authorized_http = self.get_authorized_http(credentials)

            service = googleapiclient.discovery.build(
                        'compute',
                        'v1',
                        http=authorized_http)
        else:
            service = googleapiclient.discovery.build(
                'compute',
                'v1',
                credentials=credentials,
            )

        return service

    def get_iam_service_client(self):
        credentials = self.get_service_account_credentials()
        print("creating iam service gcp")
        if HTTP_PROXY:
            print("-- using proxy")
            print(HTTP_PROXY)
            authorized_http = self.get_authorized_http(credentials)

            service = googleapiclient.discovery.build(
                        'iam',
                        'v1',
                        http=authorized_http)
        else:
            print("-- not using proxy")
            service = googleapiclient.discovery.build(
                'iam',
                'v1',
                credentials=credentials,
            )

        return service

    @classmethod
    def get_provider(cls):
        return "gce"

    def get_static_ip_by_name(self, name):
        return IP.get(name=name)

    def get_static_ip_by_host_id(self, host_id):
        return IP.get(host_id=host_id)

    def build_credential(self):
        return CredentialGce(
            self.get_provider(), self.environment, self.engine
        )

    def get_credential_add(self):
        return CredentialAddGce

    def start(self, host):
        project = self.credential.project
        zone = host.zone
        instance_name = host.name

        start = self.client.instances().start(
            project=project,
            zone=zone,
            instance=instance_name
        ).execute()

        return self.wait_operation(
            operation=start.get('name'),
            zone=zone
        )

    def stop(self, identifier):
        host = Host.get(identifier=identifier)

        project = self.credential.project
        zone = host.zone
        instance_name = host.name

        stop = self.client.instances().stop(
            project=project,
            zone=zone,
            instance=instance_name
        ).execute()

        return self.wait_operation(
            operation=stop.get('name'),
            zone=zone
        )

    @property
    def disk_image_link(self):
        image_response = self.client.images().get(
            project=self.credential.template_project,
            image=self.credential.template_to(self.engine),
        ).execute()

        return image_response['selfLink']

    def get_machine_type(self, offering, zone):
        return "zones/{}/machineTypes/{}".format(
            zone,
            offering
        )

    def _create_host(self, cpu, memory, name, zone=None, *args, **kw):

        offering = self.credential.offering_to(int(cpu), memory)
        static_ip_id = kw.get('static_ip_id')
        zone = zone or self.credential.zone

        team_name = kw.get('team_name')
        infra_name = kw.get('group')
        database_name = kw.get('database_name')
        service_account = kw.get('service_account')
        team = TeamClient(api_url=TEAM_API_URL, team_name=team_name)
        team_labels = team.make_labels(
            engine_name=self.engine_name,
            infra_name=infra_name,
            database_name=database_name
        )

        if not static_ip_id:
            raise StaticIPNotFoundError(
                'The id of static IP must be provided'
            )
        static_ip = self.get_static_ip_by_name(static_ip_id)

        static_ip_detail = self.get_or_none_resource(
            self.client.addresses,
            project=self.credential.project,
            region=self.credential.region,
            address=static_ip.name
        )
        if static_ip_detail:
            subnetwork = static_ip_detail['subnetwork'].replace('https://www.googleapis.com/compute/v1/', '')
        else:
            subnetwork = self.credential.subnetwork

        network_interface = {
            'subnetwork': subnetwork,
            'aliasIpRanges': [],
            'networkIP': static_ip.address
        }

        service_account = {
            #'email': self.credential.vm_service_account,
            'email': service_account,
            'scopes': [
                'https://www.googleapis.com/auth/devstorage.read_write',
                'https://www.googleapis.com/auth/logging.write'
            ]
        }

        config = {
            'name': name,
            'machineType': self.get_machine_type(offering, zone),

            # Specify the boot disk and the image to use as a source.
            'disks': [
                {
                    'boot': True,
                    'autoDelete': True,
                    'initializeParams': {
                        'sourceImage': self.disk_image_link,
                        'labels': team_labels
                    }
                }
            ],

            'tags': {
                'items': [self.credential.network_tag]
            },

            'labels': team_labels,

            # Specify a network interface with NAT to access the public
            # internet.
            'networkInterfaces': [network_interface],

            # Allow the instance to access cloud storage and logging.
            'serviceAccounts': [service_account],

            'metadata': {
                'items': self.credential.metadata_items
            }

        }

        # Search for the instance on all available zones
        for available_zone in self.credential.availability_zones:
            instance = self.get_or_none_resource(
                self.client.instances,
                project=self.credential.project,
                instance=name,
                zone=available_zone
            )

            if instance is not None:
                # Set zone to instance location
                self.credential.zone = available_zone
                break

        if instance is None:
            operation = self.client.instances().insert(
                project=self.credential.project,
                zone=zone,
                body=config
            ).execute()

            self.wait_operation(
                operation=operation.get('name'),
                zone=zone
            )

            instance = self.get_instance(name, zone)

        return instance

    def _destroy(self, identifier):
        attempt = 0
        host = Host.get(identifier=identifier)

        get_inst = self.get_instance(
            host.name,
            host.zone,
            execute_request=False
        )

        while attempt < self.WAIT_ATTEMPTS:
            try:
                inst = get_inst.execute()
            except Exception as ex:
                if ex.resp.status == 404:
                    return True
                raise ex
            else:
                if (inst.get('status') in ['STOPPING']):
                    sleep(self.WAIT_TIME)
                else:
                    attempt = self.WAIT_ATTEMPTS

            attempt += 1

        destroy = self.client.instances().delete(
            project=self.credential.project,
            zone=host.zone,
            instance=host.name
        ).execute()

        return self.wait_operation(
            operation=destroy.get('name'),
            zone=host.zone
        )

    def create_static_ip(self, group, ip_name):
        self.credential.before_create_host(group)

        address = self.get_or_none_resource(
            self.client.addresses,
            project=self.credential.project,
            region=self.credential.region,
            address=ip_name
        )

        if address is None:
            address = self.client.addresses().insert(
                project=self.credential.project,
                region=self.credential.region,
                body={
                    'subnetwork': self.credential.subnetwork,
                    'addressType': 'INTERNAL',
                    'name': ip_name
                }
            ).execute()

            self.wait_operation(
                operation=address.get('name'),
                region=self.credential.region
            )

        ip_metadata = self.get_internal_static_ip(ip_name)

        ip = IP(
            name=ip_name,
            group=group,
            address=ip_metadata['address']
        )
        ip.save()

        return ip

    def destroy_static_ip(self, ip_name):
        del_addr = self.get_or_none_resource(
            self.client.addresses,
            project=self.credential.project,
            region=self.credential.region,
            address=ip_name
        )

        if del_addr is None:
            return True

        del_addr = self.client.addresses().delete(
            project=self.credential.project,
            region=self.credential.region,
            address=ip_name
        ).execute()

        self.wait_operation(
            operation=del_addr.get('name'),
            region=self.credential.region
        )

    def clean(self, name):
        pass

    def configure(self, name, group, configuration):
        pass

    def resize(self, host, cpus, memory):
        offering = self.credential.offering_to(int(cpus), memory)
        return self.client.instances().setMachineType(
            project=self.credential.project,
            zone=host.zone,
            instance=host.name,
            body={
                'machineType': self.get_machine_type(
                    offering, host.zone
                ),
            }
        ).execute()

    def _is_ready(self, host):
        pass

    def associate_ip_with_host(self, host, static_ip_id):
        ip = self.get_static_ip_by_name(static_ip_id)
        ip.host = host
        ip.save()

    def create_host_object(self, provider, payload, env,
                           created_host_metadata, static_ip_id, **kw):

        zone = provider.credential.zone
        instance_name = payload['name']

        instance = self.get_instance(instance_name, zone)
        address = instance['networkInterfaces'][0]['networkIP']

        host = Host(
            name=payload['name'], group=payload['group'],
            engine=payload['engine'], environment=env, cpu=payload['cpu'],
            memory=payload['memory'], provider=provider.credential.provider,
            identifier=created_host_metadata['id'], address=address,
            zone=zone
        )
        
        host.save()
        return host

    def get_instance(self, instance_name, zone, execute_request=True):
        request = self.client.instances().get(
            project=self.credential.project,
            zone=zone,
            instance=instance_name
        )
        if execute_request:
            return request.execute()
        return request

    def get_internal_static_ip(self, ip_name, execute_request=True):
        request = self.client.addresses().get(
            project=self.credential.project,
            region=self.credential.region,
            address=ip_name
        )
        if execute_request:
            return request.execute()
        return request

    def _restore(self, host, engine, *args, **kw):

        if engine:
            self.engine = engine
        # import ipdb; ipdb.set_trace()
        if host.recreating is False:
            self._destroy(identifier=host.identifier)
            host.recreating = True
            host.save()

        team_name = kw.get('team_name')
        group = kw.get('group')
        database_name = kw.get('database_name')
        service_account = kw.get('service_account')

        created_host_metadata = self._create_host(
            cpu=host.cpu,
            memory=host.memory,
            name=host.name,
            static_ip_id=self.get_static_ip_by_host_id(host.id).name,
            zone=host.zone,
            team_name=team_name,
            group=group,
            database_name=database_name,
            service_account=service_account
        )

        host.identifier = created_host_metadata['id']
        host.recreating = False
        host.save()

    def _create_service_account(self, name):
        iam_client = self.get_iam_service_client()
        service_account = iam_client.projects().serviceAccounts().create(
            name='projects/{}'.format(self.credential.project),
            body={
                'accountId': name,
                'serviceAccount': {
                    'displayName': name
                }
            }).execute()

        sa = service_account['email']
        return sa

    def _destroy_service_account(self, service_account):
        iam_client = self.get_iam_service_client()
        name = 'projects/-/serviceAccounts/{}'.format(service_account)
        try:
            iam_client.projects().serviceAccounts().get(name=name).execute()
        except Exception as ex:
            if ex.resp.status == 404:
                return True
            raise ex
        iam_client.projects().serviceAccounts().delete(name=name).execute()

    def set_role_to_sa(self, sa):
        if not self.credential.pubsub:
            raise NotDefinedError("Pubsub credential is not defined")

        if not self.credential.roles:
            raise NotDefinedError("Roles credential is not defined")

        service = self.get_pubsub_service_client()

        topic = 'projects/{}/topics/{}'.format(
            self.credential.project, self.credential.pubsub
        )

        body = {
            "messages": [{
                "attributes": {
                    "project": self.credential.project,
                    "roles": json.dumps(self.credential.roles),
                    "service_account": sa,
                }
            }]
        }

        try:
            service.projects().topics().publish(
                topic=topic, body=body
            ).execute()
        except Exception as ex:
            raise ex

        wait_try = 0

        # decrease attempts
        while (self.WAIT_ATTEMPTS / 3) > wait_try:
            if self.check_sa_in_roles(sa, self.credential.roles):
                return True
            sleep(self.WAIT_TIME)
            wait_try += 1

        raise ServiceAccountRoleCheckError("Role not applied")

    def get_group_name(self):
        try:
            param = "&groupKey.id=" + self.credential.group_id
            service = self.get_cloudidentity_service_client()
            lookup_group_name_request = service.groups().lookup()
            lookup_group_name_request.uri += param
            lookup_group_name_response = lookup_group_name_request.execute()
            group_name = lookup_group_name_response.get("name")
            return True, group_name
        except Exception as error:
            return False, error

    def list_group_memberships(self, group_name):
        try:
            service = self.get_cloudidentity_service_client()
            response = service.groups().memberships().list(parent=group_name).execute()
            status = True
            msg = response['memberships']
            return status, msg
        except Exception as error:
            return False, error

    def add_sa_to_group(self, sa, group_name):
        try:
            service = self.get_cloudidentity_service_client()
            membership = {
                "preferredMemberKey": {"id": sa},
                "roles": {
                    "name": "MEMBER",
                }
            }
            response = service.groups().memberships().create(parent=group_name, body=membership).execute()
            status = response['done']
            msg = response['response']
            return status, msg
        except Exception as error:
            return False, error

    def _sa_set_role(self, sa):
        '''
            Because of the IAM quota issue, we had to change how to add roles to the new service accounts.
            We need to create a group, associate the roles with the group and add the new service accounts to the group.
            Now the host provider checks if the gce credentials have the fields group_name and group_id to choose which
            function will be used.
            The new function add members to a group otherwise the old function add roles to a service account and use the
            IAM quotas.
        '''
        status, group_name = self.get_group_name()
        if status:
            status, msg = self.add_sa_to_group(sa, group_name)
            logging.info('Status: {}. Message: {}'.format(status, msg))
            return status
        else:
            try:
                return self.set_role_to_sa(sa)
            except Exception as error:
                logging.info('Status: {}. Message: {}'.format(False, error))
                return False

    def check_sa_in_roles(self, service_account: str, roles: list) -> bool:
        service = self.get_resource_manager_service_client()
        bindings = service.projects().getIamPolicy(
                resource=self.credential.project).execute()['bindings']

        for role in roles:
            role_idx = next(
                (index for (index, d) in enumerate(bindings)
                 if d["role"] == role),
                None
            )

            if role_idx is None:
                return False

            sa_string = f"serviceAccount:{service_account}"
            if sa_string not in bindings[role_idx]['members']:
                return False

        return True

    def _update_host_metadata(self, identifier):
        host = Host.get(identifier=identifier)

        project = self.credential.project
        zone = host.zone
        instance_name = host.name

        instance = self.get_instance(instance_name, zone)
        fingerprint = instance['metadata']['fingerprint']
        body = {
            "fingerprint": fingerprint,
            "items": self.credential.metadata_items
        }

        self.client.instances().setMetadata(
            project=project,
            zone=zone,
            instance=instance_name,
            body=body
        ).execute()
