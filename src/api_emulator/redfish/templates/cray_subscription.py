# MIT License
#
# (C) Copyright [2022] Hewlett Packard Enterprise Development LP
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR
# OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
# ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.

# Cray Style Subscription Template File

import copy

_TEMPLATE = \
{
    "@odata.etag": "W/\"1645566542\"",
    "@odata.id": "/redfish/v1/EventService/Subscriptions/{id}",
    "@odata.type": "#EventDestination.v1_2_1.EventDestination",
    "Destination": "http://www.dnsname.com/Destination{id}",
    "Id": "{id}",
    "Name": "Subscription {id}",
    "OriginResources@odata.count": 0,
    "Protocol": "Redfish"
}

def get_subscription_instance(wildcards):
    """
    Instantiate and format the template

    Arguments:
        wildcard - A dictionary of wildcards strings and their replacement values

    """
    c = copy.deepcopy(_TEMPLATE)
    
    for field in c:
        if field != 'OriginResources@odata.count':
            c[field] = c[field].format(**wildcards)

    return c
