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

# BardPeak Static Mockup and Dynamic Resource Loader

import g
import logging
import strgen
import random

# Resource and SubResource imports
from .redfish.olympus_power_api import PowerAPI, CreatePower, ControlsDeepAPI
from .redfish.computer_system_api import ComputerSystemAPI, CreateComputerSystem, ResetAction_API
from .redfish.update_service_api import UpdateServiceAPI, CreateFirmwareTarget, SimpleUpdateAPI, UpdateServiceConfigAPI
from .redfish.templates.cray_subscription import get_subscription_instance
from .redfish.templates.cray_events import GetEventRecordTemplates
from .redfish.event_generator import EventGenerator
from .redfish.event_service_api import CreateEventService

from .static_loader import load_static

# BardPeak
#
# Called to build the static and dynamic resources to emulate a BardPeak Node.
#
# When merged with the Redfish-Interface-Emulator project:
# - BardPeak static files live in api_emulator/redfish/static/BardPeak
# - BardPeak Dynamic API files live in api_emulator/redfish
# - This file will live in api_emulator
#
# Dynamic resources:
# - Power Capping
#     GET/PATCH /redfish/v1/Chassis/{sys_id}/Controls/{control_id}
# - System Power Actions
#     GET      /redfish/v1/Systems/{sys_id}
#     GET/POST /redfish/v1/Systems/{sys_id}/Actions/ComputerSystem.Reset
# - Firmware Update
#     GET       /redfish/v1/UpdateService/FirmwareInventory/{target_id}
#     POST      /redfish/v1/UpdateService/SimpleUpdate
#     GET/PATCH /redfish/v1/UpdateService/FirmwareInventory/Config
class BardPeak:

    def __init__(self, spec, mode, rest_base, resource_dictionary):
        logging.info('BardPeak init called')

        # Add static resources here.
        self.Root = load_static('BardPeak', 'redfish', mode, rest_base, resource_dictionary)
        self.BMC_Type = 'BardPeak'

        self.randomize(resource_dictionary)

        # Add dynamic resources here. This will override any previously loaded static URL
        
        # Power Capping
        g.api.add_resource(PowerAPI, '/redfish/v1/Chassis/<string:ch_id>/Controls/<string:ident>',
            resource_class_kwargs={'rb': g.rest_base})
        g.api.add_resource(ControlsDeepAPI, '/redfish/v1/Chassis/<string:ch_id>/Controls.Deep',
            resource_class_kwargs={'rb': g.rest_base})
        chassisCollection = resource_dictionary.get_resource('BardPeak/Chassis')
        for chassis in chassisCollection['Members']:
            ch_id = chassis['@odata.id'].replace('/redfish/v1/Chassis/', '')
            ch_config = resource_dictionary.get_resource('BardPeak/Chassis/%s' % ch_id)
            if 'Controls' in ch_config:
                pwrControls = resource_dictionary.get_resource('BardPeak/Chassis/%s/Controls' % ch_id)
                for pwrControl in pwrControls['Members']:
                    control_id = pwrControl['@odata.id'].replace('/redfish/v1/Chassis/%s/Controls/' % ch_id, '')
                    config = resource_dictionary.get_resource('BardPeak/Chassis/%s/Controls/%s' % (ch_id, control_id))
                    CreatePower().put(ch_id, control_id, config)

        # System Reset Actions
        g.api.add_resource(ComputerSystemAPI, '/redfish/v1/Systems/<string:ident>',
                resource_class_kwargs={'rb': g.rest_base})
        g.api.add_resource(ResetAction_API, '/redfish/v1/Systems/<string:ident>/Actions/ComputerSystem.Reset',
                resource_class_kwargs={'rb': g.rest_base})
        systems = resource_dictionary.get_resource('BardPeak/Systems')
        for system in systems['Members']:
            sys_id = system['@odata.id'].replace('/redfish/v1/Systems/', '')
            config = resource_dictionary.get_resource('BardPeak/Systems/' + sys_id)
            rst_actions = resource_dictionary.get_resource('BardPeak/Systems/%s/ResetActionInfo' % sys_id)
            CreateComputerSystem().put(sys_id, config, rst_actions)

        # Firmware Update
        g.api.add_resource(UpdateServiceAPI, '/redfish/v1/UpdateService/FirmwareInventory/<string:ident>',
                resource_class_kwargs={'rb': g.rest_base})
        g.api.add_resource(SimpleUpdateAPI, '/redfish/v1/UpdateService/SimpleUpdate',
                resource_class_kwargs={'rb': g.rest_base})
        updateService = resource_dictionary.get_resource('BardPeak/UpdateService/FirmwareInventory')
        for member in updateService['Members']:
            target_id = member['@odata.id'].replace('/redfish/v1/UpdateService/FirmwareInventory/', '')
            config = resource_dictionary.get_resource('BardPeak/UpdateService/FirmwareInventory/' + target_id)
            CreateFirmwareTarget(resource_class_kwargs={'rb': g.rest_base, 'target_id': target_id}).put(target_id, config)

        # Firmware Update Configurations
        g.api.add_resource(UpdateServiceConfigAPI, '/redfish/v1/UpdateService/FirmwareInventory/Config',
                resource_class_kwargs={'rb': g.rest_base})

        # Event Service
        event_config = resource_dictionary.get_resource('BardPeak/EventService')
        sub_config = resource_dictionary.get_object('BardPeak/EventService/Subscriptions')
        # Remove any existing subscriptions in our static mockup
        for sub in sub_config.configuration['Members']:
            url = sub['@odata.id']
            url = url.replace('/redfish/v1', 'BardPeak')
            resource_dictionary.delete_resource(url)
        sub_config.configuration['Members'] = []
        sub_config.configuration['Members@odata.count'] = 0
        sub_generator = get_subscription_instance
        CreateEventService(resource_class_kwargs={'rb': g.rest_base}).put(event_config, sub_config.configuration, sub_generator)

        # Here we tell the event generator what templates to use for forming
        # redfish events. Since not all BMC types form events the same way.
        eventTemplates = GetEventRecordTemplates()
        EventGenerator(eventTemplates)

    # Get the BMC type
    def get_type(self):
        return self.BMC_Type

    # Randomize serial numbers and MAC addresses just in case multiple instances are created
    def randomize(self, resource_dictionary):
        # List of all of the paths with serial numbers we want to randomize
        paths = {
            'BardPeak/Chassis/Enclosure',
            'BardPeak/Chassis/Mezz0',
            'BardPeak/Chassis/Mezz1',
            'BardPeak/Chassis/Node0/NetworkAdapters/HPCNet0',
            'BardPeak/Chassis/Node0/NetworkAdapters/HPCNet1',
            'BardPeak/Chassis/Node0/NetworkAdapters/HPCNet2',
            'BardPeak/Chassis/Node0/NetworkAdapters/HPCNet3',
            'BardPeak/Systems/Node0',
            'BardPeak/Systems/Node0/Memory/DIMM0',
            'BardPeak/Systems/Node0/Memory/DIMM1',
            'BardPeak/Systems/Node0/Memory/DIMM2',
            'BardPeak/Systems/Node0/Memory/DIMM3',
            'BardPeak/Systems/Node0/Memory/DIMM4',
            'BardPeak/Systems/Node0/Memory/DIMM5',
            'BardPeak/Systems/Node0/Memory/DIMM6',
            'BardPeak/Systems/Node0/Memory/DIMM7',
            'BardPeak/Systems/Node0/Processors/CPU0',
            'BardPeak/Systems/Node0/Processors/GPU0',
            'BardPeak/Systems/Node0/Processors/GPU1',
            'BardPeak/Systems/Node0/Processors/GPU2',
            'BardPeak/Systems/Node0/Processors/GPU3',
            'BardPeak/Systems/Node0/Processors/GPU4',
            'BardPeak/Systems/Node0/Processors/GPU5',
            'BardPeak/Systems/Node0/Processors/GPU6',
            'BardPeak/Systems/Node0/Processors/GPU7'
        }
        foundSNs = {}
        for path in paths:
            page = resource_dictionary.get_object(path)
            sn = page.configuration['SerialNumber']
            # If they have the same SN as something else in our mockup,
            # keep it that way. Except if the value is bogus.
            if sn in foundSNs and sn != '00000000000000':
                page.configuration['SerialNumber'] = foundSNs[sn]
            else:
                rndSN = strgen.StringGenerator('[A-Z]{3}[0-9]{10}').render()
                foundSNs[sn] = rndSN
                page.configuration['SerialNumber'] = rndSN

        path = 'BardPeak/Chassis/Node0/Assembly'
        page = resource_dictionary.get_object(path)
        for assembly in page.configuration['Assemblies']:
            sn = assembly['SerialNumber']
            if sn in foundSNs and sn != '00000000000000':
                assembly['SerialNumber'] = foundSNs[sn]
            else:
                rndSN = strgen.StringGenerator('[A-Z]{3}[0-9]{10}').render()
                foundSNs[sn] = rndSN
                assembly['SerialNumber'] = rndSN

        path = 'BardPeak/Systems/Node0/EthernetInterfaces/ManagementEthernet'
        page = resource_dictionary.get_object(path)
        rndMAC = [ 0x00, 0x40, 0xa6,
            random.randint(0x00, 0x7f),
            random.randint(0x00, 0xff),
            random.randint(0x00, 0xff)]
        newMAC = ':'.join(map(lambda x: "%02x" % x, rndMAC))
        page.configuration['MACAddress'] = newMAC
        page.configuration['PermanentMACAddress'] = newMAC
