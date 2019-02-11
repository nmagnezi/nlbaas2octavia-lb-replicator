import argparse
import json
from os import environ

from keystoneauth1 import loading
from keystoneauth1 import session
from keystoneclient.v3 import client as keystoneclient
from neutronclient.v2_0 import client as neutronclient
from octaviaclient.api.v2 import octavia as octaviaclient
from pprint import pprint

OS_PROJECT_NAME = environ.get('OS_PROJECT_NAME')
OS_USERNAME = environ.get('OS_USERNAME')
OS_PASSWORD = environ.get('OS_PASSWORD')
OS_AUTH_URL = environ.get('OS_AUTH_URL')
OS_PROJECT_DOMAIN_NAME = environ.get('OS_PROJECT_DOMAIN_NAME', 'Default')
OS_USER_DOMAIN_NAME = environ.get('OS_USER_DOMAIN_NAME', 'Default')


def process_args():

    parser = argparse.ArgumentParser(
        description='Replicate a Neutron-LBaaS Load Balancer to Octavia via '
                    'API'
    )
    parser.add_argument(
        '-l', '--lb_id',
        required=True,
        help='Load balancer ID. '
             'When no --to/from a file specified, will create it in Octavia.'
    )
    parser.add_argument(
        '-v', '--reuse_vip',
        default=False,
        action='store_true',
        help='When specified, use the same Load balancer VIP address. Should '
             'only be used when the source load balancer is already gone.'
    )
    file_options = parser.add_mutually_exclusive_group()
    file_options.add_argument(
        '--to_file',
        action='store_true',
        help="Save load balancer details to a local file. "
             "Does not create it in Octavia."
    )
    file_options.add_argument(
        '--from_file',
        action='store_true',
        help="Read load balancer details from a local file. "
             "Create in Octavia."
    )
    parser.add_argument(
        '-p', '--project_name',
        required=False if OS_PROJECT_NAME else True,
        help='Project ID or name. When not specified, '
             'will read it from environment variable: OS_PROJECT_NAME.'
    )
    parser.add_argument(
        '-u', '--username',
        required=False if OS_USERNAME else True,
        help='Username ID or name. When not specified, '
             'will read it from environment variable: OS_USERNAME.'
    )
    parser.add_argument(
        '-pa', '--password',
        required=False if OS_PASSWORD else True,
        help='Password ID or name. When not specified, '
             'will read it from environment variable: OS_PASSWORD.'
    )
    parser.add_argument(
        '-a', '--auth_url',
        required=False if OS_AUTH_URL else True,
        help='Auth URL. When not specified, '
             'will read it from environment variable: OS_AUTH_URL.'
    )
    return parser.parse_args()


def _remove_empty(lb_dict):
    """
    Removes keys from dictionary and sub objs such as dictionaries and list of
    dictionaries, if they value is an empty string.
    :param lb_dict: dict
    """
    for key, val in lb_dict.items():
        if isinstance(val, dict):
            _remove_empty(val)
        if isinstance(val, list):
            for x in val:
                if isinstance(x, dict):
                    _remove_empty(x)
        if val in ['', u'']:
            lb_dict.pop(key)


class OpenStackClients(object):

    def __init__(self, project_name=OS_PROJECT_NAME, username=OS_USERNAME,
                 password=OS_PASSWORD, auth_url=OS_AUTH_URL,
                 project_domain_name=OS_PROJECT_DOMAIN_NAME,
                 user_domain_name=OS_USER_DOMAIN_NAME):

        # Handle user-feed data vs environment variables.
        self.keystone_credentials = {
            'username': username,
            'password': password,
            'project_name': project_name,
            'auth_url': auth_url,
            'project_domain_name':  project_domain_name,
            'user_domain_name': user_domain_name
        }
        self._keystone_session = self.get_keystone_session()
        self.octaviaclient = self.get_octaviaclient()
        self.neutronclient = self.get_neutronclient()

    def get_keystone_session(self):
        loader = loading.get_plugin_loader('password')
        auth = loader.load_from_options(**self.keystone_credentials)
        return session.Session(auth=auth, verify=False)

    def get_octaviaclient(self):
        keystone = keystoneclient.Client(session=self._keystone_session)
        service_id = keystone.services.list(name='octavia')[0].id
        octavia_endpoint = keystone.endpoints.list(service=service_id,
                                                   interface='public')[0].url
        return octaviaclient.OctaviaAPI(session=self._keystone_session,
                                        endpoint=octavia_endpoint)

    def get_neutronclient(self):
        return neutronclient.Client(session=self._keystone_session)


class LbReplicator(object):

    def __init__(self, lb_id):
        self.os_clients = OpenStackClients()
        self._lb_id = lb_id
        self._lb_tree = {}
        self._lb_details = {}
        self._lb_listeners = {}
        self._lb_pools = {}
        self._lb_def_pool_id = ''
        self._lb_healthmonitors = {}
        self._lb_members = {}

    def _pools_deep_scan(self, pools_list):
        for pool in pools_list:
            pool_id = pool['id']
            lb_pool = self.os_clients.neutronclient.show_lbaas_pool(pool_id)
            self._lb_pools[pool_id] = lb_pool
            if pool.get('healthmonitor'):
                # Health monitor is optional
                healthmonitor_id = pool['healthmonitor']['id']
                lb_healthmonitor = (
                    self.os_clients.neutronclient
                    .show_health_monitor(healthmonitor_id)
                )
                self._lb_healthmonitors[healthmonitor_id] = lb_healthmonitor
            for member in pool['members']:
                member_id = member['id']
                lb_member = (
                    self.os_clients.neutronclient
                    .show_lbaas_member(member_id, pool_id)
                )
                self._lb_members[member_id] = lb_member

    def collect_lb_info_from_api(self):
        self._lb_tree = (
            self.os_clients.neutronclient.retrieve_loadbalancer_status(
                loadbalancer=self._lb_id)
        )
        self._lb_details = self.os_clients.neutronclient.show_loadbalancer(
            self._lb_id)

        # Scan lb_tree and retrive all objects to backup all the info
        # that tree is missing out. The Octavia lb tree contain more details.
        for listener in (
                self._lb_tree['statuses']['loadbalancer']['listeners']):
            listener_id = listener['id']
            lb_listener = (
                self.os_clients.neutronclient.show_listener(listener_id)
                           )
            self._lb_listeners[listener_id] = lb_listener
            self._pools_deep_scan(listener['pools'])

        self._pools_deep_scan(
            self._lb_tree['statuses']['loadbalancer']['pools'])

    def write_lb_data_file(self, filename):
        lb_data = {
            'lb_id': self._lb_id,
            'lb_tree': self._lb_tree,
            'lb_details': self._lb_details,
            'lb_listeners': self._lb_listeners,
            'lb_pools': self._lb_pools,
            'lb_healthmonitors': self._lb_healthmonitors,
            'lb_members': self._lb_members
        }
        with open(filename, 'w') as f:
            json.dump(lb_data, f, sort_keys=True, indent=4)

    def read_lb_data_file(self, filename):
        # Read load balancer data from a local JSON file.
        with open(filename) as f:
            lb_data = json.load(f)
        try:
            if self._lb_id == lb_data['lb_id']:
                self._lb_tree = lb_data['lb_tree']
                self._lb_details = lb_data['lb_details']
                self._lb_listeners = lb_data['lb_listeners']
                self._lb_pools = lb_data['lb_pools']
                self._lb_healthmonitors = lb_data['lb_healthmonitors']
                self._lb_members = lb_data['lb_members']
        except ValueError:
            print('The file content does not match the lb_id you specified')

    def _build_healthmonitor_obj(self, pool_id):
        nlbaas_pool_data = self._lb_pools[pool_id]['pool']
        octavia_hm = None

        if nlbaas_pool_data.get('healthmonitor_id'):
            healthmonitor_id = nlbaas_pool_data['healthmonitor_id']
            healthmonitor_data = self._lb_healthmonitors[healthmonitor_id]
            octavia_hm = {
                'type': healthmonitor_data.get('type'),
                'delay': healthmonitor_data.get('delay'),
                'expected_codes': healthmonitor_data.get('expected_codes'),
                'http_method': healthmonitor_data.get('http_method'),
                'max_retries': healthmonitor_data.get('max_retries'),
                'timeout': healthmonitor_data.get('timeout'),
                'url_path': healthmonitor_data.get('url_path')
            }
        return octavia_hm

    def _build_members_list(self, pool_id):
        nlbaas_pool_data = self._lb_pools[pool_id]['pool']
        octavia_lb_members = []

        for member in nlbaas_pool_data['members']:
            member_id = member['id']
            member_data = self._lb_members[member_id]['member']
            octavia_member = {
                'admin_state_up': member_data['admin_state_up'],
                'name': member_data['name'],
                'address': member_data['address'],
                'protocol_port': member_data['protocol_port'],
                'subnet_id': member_data['subnet_id'],
                'weight': member_data['weight']
            }
            octavia_lb_members.append(octavia_member)
        return octavia_lb_members

    def _build_listeners_list(self):
        nlbaas_lb_tree = self._lb_tree['statuses']['loadbalancer']
        octavia_lb_listeners = []
        for listener in nlbaas_lb_tree['listeners']:
            listener_id = listener['id']
            nlbaas_listener_data = self._lb_listeners[listener_id]['listener']

            self._lb_def_pool_id = nlbaas_listener_data['default_pool_id']
            nlbaas_default_pool_data = \
                self._lb_pools[self._lb_def_pool_id]['pool']

            octavia_listener = {
                'name': nlbaas_listener_data['name'],
                'protocol': nlbaas_listener_data['protocol'],
                'protocol_port': nlbaas_listener_data['protocol_port'],
                'default_pool': {
                    'name': nlbaas_default_pool_data['name'],
                    'protocol': nlbaas_default_pool_data['protocol'],
                    'lb_algorithm': nlbaas_default_pool_data['lb_algorithm'],
                    'healthmonitor':
                        self._build_healthmonitor_obj(
                            self._lb_def_pool_id) or '',
                    'members': self._build_members_list(
                        self._lb_def_pool_id) or ''
                }
            }
            octavia_lb_listeners.append(octavia_listener)
        return octavia_lb_listeners

    def _build_pools_list(self):
        nlbaas_lb_tree = self._lb_tree['statuses']['loadbalancer']
        octavia_lb_pools = []
        for pool in nlbaas_lb_tree['pools']:
            pool_id = pool['id']
            if pool_id == self._lb_def_pool_id:
                continue
            else:
                nlbaas_pool_data = self._lb_pools[pool_id]['pool']

                octavia_pool = {
                    'name': nlbaas_pool_data['name'],
                    'description': nlbaas_pool_data['description'],
                    'protocol': nlbaas_pool_data['protocol'],
                    'lb_algorithm': nlbaas_pool_data['lb_algorithm'],
                    'healthmonitor':
                        self._build_healthmonitor_obj(pool_id) or '',
                    'members': self._build_members_list(pool_id) or ''
                 }
                octavia_lb_pools.append(octavia_pool)
        return octavia_lb_pools

    def build_octavia_lb_tree(self, reuse_vip):
        nlbaas_lb_details = self._lb_details['loadbalancer']

        octavia_lb_tree = {
            'loadbalancer': {
                'name': nlbaas_lb_details['name'],
                'description': nlbaas_lb_details['description'],
                'admin_state_up': nlbaas_lb_details['admin_state_up'],
                'project_id': nlbaas_lb_details['tenant_id'],
                'flavor_id': '',
                'listeners': self._build_listeners_list(),
                'pools': self._build_pools_list(),
                'vip_subnet_id': nlbaas_lb_details['vip_subnet_id'],
                'vip_address': nlbaas_lb_details['vip_address']
                if reuse_vip else ''
            }
        }
        _remove_empty(octavia_lb_tree)
        return octavia_lb_tree

    def octavia_load_balancer_create(self, reuse_vip):
        octavia_lb_tree = self.build_octavia_lb_tree(reuse_vip)
        pprint(octavia_lb_tree)
        self.os_clients.octaviaclient.load_balancer_create(
            json=octavia_lb_tree)


def main():

    args = process_args()
    lb_data_filename = ''.join([args.lb_id, '_data', '.json'])
    lb_replicator = LbReplicator(args.lb_id)

    # Collect all the data about the Neutron-LBaaS based load balancer.

    if args.from_file:
        lb_replicator.read_lb_data_file(lb_data_filename)
    else:
        # Get load balancer from OpenStack Neutron API.
        lb_replicator.collect_lb_info_from_api()

    # Either backup all the data about the Neutron-LBaaS based load balancer to
    # to a file or directly create it in Octavia.

    if args.to_file:
        # Backup to a JSON file.
        lb_replicator.write_lb_data_file(lb_data_filename)

    else:
        # Build an Octavia load balancer tree and create it.
        lb_replicator.octavia_load_balancer_create(args.reuse_vip)


if __name__ == '__main__':
    main()
