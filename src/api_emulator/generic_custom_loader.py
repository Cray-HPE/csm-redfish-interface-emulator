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

# Generic Custom Static Mockup

import g
import logging

# Resource and SubResource imports
from .static_loader import load_static

# GenericCustom
#
# Called to build the static resources to emulate a Custom BMC.
#
# When merged with the Redfish-Interface-Emulator project:
# - The custom static files live in api_emulator/redfish/static/<MyBMC>
# - This file will live in api_emulator
#
# Dynamic resources:
# - None
class GenericCustom:

    def __init__(self, bmc_type, spec, mode, rest_base, resource_dictionary):
        logging.info('GenericCustom init called')
        self.BMC_Type = bmc_type

        # Add static resources here.
        self.Root = load_static(bmc_type, 'redfish', mode, rest_base, resource_dictionary)

        # Add dynamic resources here. This will override any previously loaded static URL

    # Get the BMC type
    def get_type(self):
        return self.BMC_Type