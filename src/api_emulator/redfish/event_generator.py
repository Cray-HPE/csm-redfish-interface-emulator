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

# Redfish Event Generator

import strgen
import datetime
import copy
from uuid import uuid4

_GENERIC = \
{
    "EventType": "",
    "Severity": "OK",
    "Message": "",
    "MessageId": "Alert.1.0",
    "MessageArgs": [],
    "OriginOfCondition": "",
    "Context": "{Context}"
}

templates = {}
count = 1

# GenEvent
#
# Create a redfish event with the given EventRecords
def GenEvent(events):
    """
    Event constructor
    """
    config = {
        "@odata.context": "/redfish/v1/$metadata#Event.Event",
        "@odata.type": "#Event.v1_3_1.Event",
        "@odata.id": "/redfish/v1/EventService/Events",
        "Id": "1",
        "Name": "Event Array",
        "Events@odata.count": len(events),
        "Events": events
    }
    return config

# GenEventRecord
#
# Create a redfish event record with the given parameters. How the parameters
# affect the event record is determined by the template used.
# This function generates a timestamp (timestamp), uuid(uuid), random alphanumaric
# string (rnd_str), and counter (count) for use with a template if those arguments
# are specified in the template.
def GenEventRecord(schemaType='Generic', **wildcards):
    """
    Event record constructor
    """
    global count
    
    # See if we want to use one of our predefined event
    # schemas to more closely mimic our bmc_type.
    if schemaType in templates:
        wildcards['count'] = count
        count += 1
        wildcards['uuid'] = str(uuid4())
        wildcards['rnd_str'] = strgen.StringGenerator('[A-Z]{3}[0-9]{10}').render()
        wildcards['timestamp'] = datetime.datetime.now().isoformat()
        template = templates[schemaType]

        config = copy.deepcopy(template)
        # Apply event type defaults
        for field in config:
            if field == 'MessageArgs':
                for i in range(len(config[field])):
                    config[field][i] = config[field][i].format(**wildcards)
            elif field == 'OriginOfCondition' and '@odata.id' in config[field]:
                config[field]['@odata.id'] = config[field]['@odata.id'].format(**wildcards)
            elif field != 'Context':
                # Don't add Context here, that will get added later
                config[field] = config[field].format(**wildcards)
    else:
        # If it doesn't match one of our pre-defined event templates the
        # wildcards will just be used to do a striaght field replacement.
        config = copy.deepcopy(_GENERIC)
        for field, value in wildcards.items():
            if field != 'Context':
                config[field] = value
        config['EventId'] = strgen.StringGenerator('[A-Z]{3}[0-9]{10}').render()
        config['EventTimestamp'] = datetime.datetime.now().isoformat()
    return config

# EventGenerator
#
# Initialize the EventGenerator with the templates to use for generating events.
class EventGenerator:
    def __init__(self, eventTemplates):
        global templates
        templates = eventTemplates
