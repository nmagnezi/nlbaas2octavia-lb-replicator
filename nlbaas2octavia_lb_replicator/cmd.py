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
import sys

from nlbaas2octavia_lb_replicator import parser
from nlbaas2octavia_lb_replicator import manager


def main():

    args = parser.process_args()
    lb_data_filename = ''.join([args.lb_id, '_data', '.json'])
    lb_replicator = manager.Manager(args.lb_id)

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
    sys.exit(main())
