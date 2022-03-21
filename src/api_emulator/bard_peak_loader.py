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

# Resource and SubResource imports
from .redfish.olympus_power_api import PowerAPI, CreatePower
from .redfish.computer_system_api import ComputerSystemAPI, CreateComputerSystem, ResetAction_API
from .redfish.update_service_api import UpdateServiceAPI, CreateFirmwareTarget, SimpleUpdateAPI, UpdateServiceConfigAPI
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

        # Add dynamic resources here. This will override any previously loaded static URL
        
        # Power Capping
        g.api.add_resource(PowerAPI, '/redfish/v1/Chassis/Node0/Controls/<string:ident>',
            resource_class_kwargs={'rb': g.rest_base})
        pwrControls = resource_dictionary.get_resource('BardPeak/Chassis/Node0/Controls')
        for pwrControl in pwrControls['Members']:
            control_id = pwrControl['@odata.id']
            control_id = control_id.replace('/redfish/v1/Chassis/Node0/Controls/', '')
            config = resource_dictionary.get_resource('BardPeak/Chassis/Node0/Controls/' + control_id)
            CreatePower(resource_class_kwargs={'rb': g.rest_base, 'ch_id': 'Node0', 'control_id': control_id}).put('Node0', control_id, config)

        # System Reset Actions
        g.api.add_resource(ComputerSystemAPI, '/redfish/v1/Systems/<string:ident>',
                resource_class_kwargs={'rb': g.rest_base})
        g.api.add_resource(ResetAction_API, '/redfish/v1/Systems/<string:ident>/Actions/ComputerSystem.Reset',
                resource_class_kwargs={'rb': g.rest_base})
        systems = resource_dictionary.get_resource('BardPeak/Systems')
        for system in systems['Members']:
            sys_id = system['@odata.id']
            sys_id = sys_id.replace('/redfish/v1/Systems/', '')
            config = resource_dictionary.get_resource('BardPeak/Systems/' + sys_id)
            rst_actions = resource_dictionary.get_resource('BardPeak/Systems/%s/ResetActionInfo' % sys_id)
            CreateComputerSystem(resource_class_kwargs={'rb': g.rest_base, 'sys_id': sys_id}).put(sys_id, config, rst_actions)

        # Firmware Update
        g.api.add_resource(UpdateServiceAPI, '/redfish/v1/UpdateService/FirmwareInventory/<string:ident>',
                resource_class_kwargs={'rb': g.rest_base})
        g.api.add_resource(SimpleUpdateAPI, '/redfish/v1/UpdateService/SimpleUpdate',
                resource_class_kwargs={'rb': g.rest_base})
        updateService = resource_dictionary.get_resource('BardPeak/UpdateService/FirmwareInventory')
        for member in updateService['Members']:
            target_id = member['@odata.id']
            target_id = target_id.replace('/redfish/v1/UpdateService/FirmwareInventory/', '')
            config = resource_dictionary.get_resource('BardPeak/UpdateService/FirmwareInventory/' + target_id)
            CreateFirmwareTarget(resource_class_kwargs={'rb': g.rest_base, 'target_id': target_id}).put(target_id, config)

        # Firmware Update Configurations
        g.api.add_resource(UpdateServiceConfigAPI, '/redfish/v1/UpdateService/FirmwareInventory/Config',
                resource_class_kwargs={'rb': g.rest_base})

    # Get the BMC type
    def get_type(self):
        return self.BMC_Type