# Copyright 2019 Nir Magnezi
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import argparse
from os import environ

from keystoneclient.v3 import client as keystoneclient
from neutronclient.v2_0 import client as neutronclient
from octaviaclient.api.v2 import octavia as octaviaclient


OS_PROJECT_NAME = environ.get('OS_PROJECT_NAME')
OS_USERNAME = environ.get('OS_USERNAME')
OS_PASSWORD = environ.get('OS_PASSWORD')
OS_AUTH_URL = environ.get('OS_AUTH_URL')
OS_PROJECT_DOMAIN_NAME = environ.get('OS_PROJECT_DOMAIN_NAME') or 'Default'
OS_USER_DOMAIN_NAME = environ.get('OS_USER_DOMAIN_NAME') or 'Default'


class OpenStackClients(object):

    def __init__(self, project_name=None, username=None, password=None,
                 auth_url=None, project_domain_name=None,
                 user_domain_name=None):

        # Handle user-feed data vs environment variables.
        if not project_name:
            project_name = OS_PROJECT_NAME
        if not username:
            username = OS_USERNAME
        if not password:
            password = OS_PASSWORD
        if not auth_url:
            auth_url = OS_AUTH_URL
        if not project_domain_name:
            project_domain_name = OS_PROJECT_DOMAIN_NAME
        if not user_domain_name:
            user_domain_name = OS_USER_DOMAIN_NAME

        self.keystone_credentials = {
            'username': username,
            'password': password,
            'project_name': project_name,
            'auth_url': auth_url,
            'project_domain_name': project_domain_name,
            'user_domain_name': user_domain_name
        }
        self._keystone_session = self.get_keystone_session()
        self.octaviaclient = self.get_octaviaclient()
        self.neutronclient = self.get_neutronclient()

    def get_keystone_session(self):
        from keystoneauth1 import loading
        from keystoneauth1 import session
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


def process_args():

    parser = argparse.ArgumentParser(
        description='Migrate a Neutron-LBaaS Load Balancer to Octavia via API'
    )
    parser.add_argument(
        '-l', '--lb_id',
        required=True,
        help='Load balancer ID. '
             'When no --to/from file specified, will create it in Octavia.'
    )
    file_options = parser.add_mutually_exclusive_group()
    file_options.add_argument(
        '--to_file',
        default=None,
        help="Save load balancer details to local file. "
             "Does not create it in Octavia."
    )
    file_options.add_argument(
        '--from_file',
        default=None,
        help="Read load balancer details from local file. "
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
    Removes keys from dictionary and sub dictionaries if they value is an empty
    string.
    :param lb_dict: dict
    """
    for key, val in lb_dict.items():
        if isinstance(val, dict):
            return _remove_empty(val)
        if val is '' or val is u'':
            # if val in ['', u'']:
            lb_dict.pop(key)


def build_octavia_lb_tree(nlbaas_lb_details, lb_statuses_tree,
                          reuse_vip=False):
    nlbaas_lb_details = nlbaas_lb_details['loadbalancer']
    nlbaas_lb_tree = lb_statuses_tree['statuses']['loadbalancer']

    octavia_lb_listeners = []
    octavia_lb_pools = []

    # WIP!
    # for listener in nlbaas_lb_tree['listeners']:
    #     pass

    # for pool in nlbaas_lb_tree['pools']:
    #     pass

    octavia_lb_tree = {
        "loadbalancer": {
            "description": nlbaas_lb_details['description'],
            "admin_state_up": nlbaas_lb_details['admin_state_up'],
            "project_id": nlbaas_lb_details['tenant_id'],
            "flavor_id": "",
            "listeners": octavia_lb_listeners,
            "pools": octavia_lb_pools,
            "vip_subnet_id": nlbaas_lb_details['vip_subnet_id'],
            "vip_address": nlbaas_lb_details['vip_address']
            if reuse_vip else ""
        }
    }
    _remove_empty(octavia_lb_tree)
    return octavia_lb_tree


def main():
    args = process_args()
    os_clients = OpenStackClients()

    # Collect all the data about the neutron-lbaas based load balancer
    lb_statuses_tree = os_clients.neutronclient.retrieve_loadbalancer_status(
        loadbalancer=args.lb_id)
    lb_details = os_clients.neutronclient.show_loadbalancer(args.lb_id)

    # Build an Octavia API load balancer tree
    octavia_lb_tree = build_octavia_lb_tree(lb_details, lb_statuses_tree)

    import pdb ; pdb.set_trace()
    os_clients.octaviaclient.load_balancer_create(json=octavia_lb_tree)


if __name__ == '__main__':
    main()
