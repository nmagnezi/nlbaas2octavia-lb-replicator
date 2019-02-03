# nlbaas2octavia-lb-migrator

##The problem
OpenStack does not** currently provide users with a migration path from Neutron-LBaaS to  Octavia.
Such migration should take into account: data plane downtime, VIP migration, rollback options and more.

** it does provide a tool for cloud admins, see [Alternatives](##Alternatives).

## The migration tool
nlbaas2octavia-lb-migrator is a script to allow users to capture everything about their Neutron LBaaS based load balancers, and eventually, create the very same load balancer (with all of its sub-objects) in Octavia.

## Pre-requisites 
 Users need to have access to:
- Neutron API
- Octavia API

Users don't necessarily have to operate with admin permissions as long as they are working with API objects they are allowed to access.

## Working Assumptions
- A load balancer VIP might be associated with a [Neutron floating-ip](https://www.rdoproject.org/networking/difference-between-floating-ip-and-private-ip/). In that case, The user may simply create the new Octavia loadbalancer using the same Neutron subnet of the exiting Neutron LBaaS loadbalancer (check the script help for --reuse_vip). Lastly, the user should disassociate the floating-ip from the Neutron LBaaS load balancer and associate it with the newly created Octavia load balancer. The script won't do it for you.

- In a case where the load balancer VIP is the neuron subnet port, Users will need to delete their old loadbalancer before creating a new one in Octavia. For that, the script provides the option to store all of the load balancer data in a JSON file. Additionally, the script can read the very same JSON file to create a [fully populated load balancer]( https://developer.openstack.org/api-ref/load-balancer/v2/index.html?expanded=create-a-load-balancer-detail#creating-a-fully-populated-load-balancer) in Octavia.

## Design Decisions and Known limitations
- nlbaas2octavia-lb-migrator does not handle with L7 rules since those were only supported by third-party drivers in Neutron LBaaS (excluding Octavia as a Neutron-LBaaS provider). While HAProxy itself is fully capable of handling L7 rules, the Neutron LBaaS plugin for it did not include it. To overcome this, users may either make additions to the script or copy L7 Rules manually.

- Neutron API provides the option to dump a JSON output for a [load balancer status]( https://developer.openstack.org/api-ref/network/v2/?expanded=show-load-balancer-status-tree-detail#load-balancer-statuses), yet the [Octavia fully populated]( https://developer.openstack.org/api-ref/load-balancer/v2/index.html?expanded=create-a-load-balancer-detail#creating-a-fully-populated-load-balancer) JSON object requires some information that is absent from that Neutron output. To work around that (and assuming that a given load balancer might be deleted by the time users which to create a replica in Octavia), the script captures all of the information about each load balancer sub-object such as listeners, pools, health monitors and pool members.

## How does it work
The script is capable of reading Keystone authentication options either from [OpenStack related environment variables](https://docs.openstack.org/mitaka/install-guide-obs/keystone-openrc.html) or via CLI (using python argparse).

As a first step, the script will either query the Neutron API for all the details (see Design Decisions and Known limitations #2) or read a ready JSON file that stores information about a given load balancer.

The next step will depend on what option user chose.
The script will either:
- Back up all of the information to a JSON file (if initially read from a file to begin with).
- Generate a JSON object that fits Octavia, and sent it to Octavia API in order to create a fully populated load balancer.  

## What it does not do
- Modify or delete any existing load balancer configuration.
- Moves floating IPs around.

## Usage example
Backup a load balancer to a JSON file
> `$ python lb_migrator.py --l 3badc500-b24a-425a-88c6-c32a5f790ae4 --to_file`

Read load balancer information from a JSON file and create it in Octavia
> `$ python lb_migrator.py --l 3badc500-b24a-425a-88c6-c32a5f790ae4 --from_file --reuse_vip`

Read load balancer information from a Neutron API and immediately create it in Octavia
> `$ python nlbaas2octavia-lb-migrator/lb_migrator.py --l 3badc500-b24a-425a-88c6-c32a5f790ae4`

## Options
      -h, --help            show this help message and exit
      -l LB_ID, --lb_id LB_ID
                            Load balancer ID. When no --to/from a file specified, 
                            will create it in Octavia.
      -v, --reuse_vip       When specified, use the same Load balancer VIP
                            address. Should only be used when the source load
                            balancer is already gone.
      --to_file             Save load balancer details to local a file. Does not
                            create it in Octavia.
      --from_file           Read load balancer details from a local file. Create in
                            Octavia.
      -p PROJECT_NAME, --project_name PROJECT_NAME
                            Project ID or name. When not specified, will read it
                            from environment variable: OS_PROJECT_NAME.
      -u USERNAME, --username USERNAME
                            Username ID or name. When not specified, will read it
                            from environment variable: OS_USERNAME.
      -pa PASSWORD, --password PASSWORD
                            Password ID or name. When not specified, will read it
                            from environment variable: OS_PASSWORD.
      -a AUTH_URL, --auth_url AUTH_URL
                            Auth URL. When not specified, will read it from
                            environment variable: OS_AUTH_URL.`

## Alternatives
A database migration script that you may find [here](https://github.com/openstack/neutron-lbaas/tree/master/tools/nlbaas2octavia).
Note that only cloud operators will be able to invoke such script.


Notes:
does not delete or modify existing resoucres
at the end of migration users will need to delete the resources.
move floating ip.
in case something fails the script will not role back.

