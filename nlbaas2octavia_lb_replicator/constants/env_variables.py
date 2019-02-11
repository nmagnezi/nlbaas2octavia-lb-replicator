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
from os import environ

OS_PROJECT_NAME = environ.get('OS_PROJECT_NAME')
OS_USERNAME = environ.get('OS_USERNAME')
OS_PASSWORD = environ.get('OS_PASSWORD')
OS_AUTH_URL = environ.get('OS_AUTH_URL')
OS_PROJECT_DOMAIN_NAME = environ.get('OS_PROJECT_DOMAIN_NAME', 'Default')
OS_USER_DOMAIN_NAME = environ.get('OS_USER_DOMAIN_NAME', 'Default')
