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
