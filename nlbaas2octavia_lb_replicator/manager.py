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
import json

from pprint import pprint

from nlbaas2octavia_lb_replicator.common import os_clients
from nlbaas2octavia_lb_replicator.common import utils


class Manager(object):

    def __init__(self, lb_id):
        self.os_clients = os_clients.OpenStackClients()
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
        utils._remove_empty(octavia_lb_tree)
        return octavia_lb_tree

    def octavia_load_balancer_create(self, reuse_vip):
        octavia_lb_tree = self.build_octavia_lb_tree(reuse_vip)
        pprint(octavia_lb_tree)
        self.os_clients.octaviaclient.load_balancer_create(
            json=octavia_lb_tree)
