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
from nlbaas2octavia_lb_replicator.constants import env_variables


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
        required=False if env_variables.OS_PROJECT_NAME else True,
        help='Project ID or name. When not specified, '
             'will read it from environment variable: OS_PROJECT_NAME.'
    )
    parser.add_argument(
        '-u', '--username',
        required=False if env_variables.OS_USERNAME else True,
        help='Username ID or name. When not specified, '
             'will read it from environment variable: OS_USERNAME.'
    )
    parser.add_argument(
        '-pa', '--password',
        required=False if env_variables.OS_PASSWORD else True,
        help='Password ID or name. When not specified, '
             'will read it from environment variable: OS_PASSWORD.'
    )
    parser.add_argument(
        '-a', '--auth_url',
        required=False if env_variables.OS_AUTH_URL else True,
        help='Auth URL. When not specified, '
             'will read it from environment variable: OS_AUTH_URL.'
    )
    return parser.parse_args()
