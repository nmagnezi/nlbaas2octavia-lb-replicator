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
from nlbaas2octavia_lb_replicator.constants import env_variables

from keystoneauth1 import loading
from keystoneauth1 import session
from keystoneclient.v3 import client as keystoneclient
from neutronclient.v2_0 import client as neutronclient
from octaviaclient.api.v2 import octavia as octaviaclient


class OpenStackClients(object):

    def __init__(
        self,
        project_name=env_variables.OS_PROJECT_NAME,
        username=env_variables.OS_USERNAME,
        password=env_variables.OS_PASSWORD,
        auth_url=env_variables.OS_AUTH_URL,
        project_domain_name=env_variables.OS_PROJECT_DOMAIN_NAME,
        user_domain_name=env_variables.OS_USER_DOMAIN_NAME,
    ):

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
