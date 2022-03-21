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

# Olympus Power Control API File

"""
Dynamic resources:
 - Power Capping
    GET/PATCH /redfish/v1/Chassis/{sys_id}/Controls/{control_id}
"""

import g

import sys, traceback
import logging
import copy
from flask import Flask, request, make_response, render_template
from flask_restful import reqparse, Api, Resource

members = {}

INTERNAL_ERROR = 500


# PowerAPI
#
# This services GET and PATCH requests for computer system power controls.
#
class PowerAPI(Resource):

    def __init__(self, **kwargs):
        logging.info('PowerAPI init called')
        try:
            global wildcards
            wildcards = kwargs
        except Exception:
            traceback.print_exc()

    # HTTP GET
    def get(self, ident):
        logging.info('PowerAPI GET called')
        try:
            # Find the entry with the correct value for Id
            resp = 404
            if ident in members:
                resp = members[ident], 200
        except Exception:
            traceback.print_exc()
            resp = INTERNAL_ERROR
        return resp

    # HTTP PUT
    def put(self, ident):
        logging.info('PowerAPI PUT called')
        return 'PUT is not supported', 405, {'Allow': 'GET, PATCH'}

    # HTTP POST
    def post(self, ident):
        logging.info('PowerAPI POST called')
        return 'POST is not supported', 405, {'Allow': 'GET, PATCH'}

    # HTTP PATCH
    def patch(self, ident):
        logging.info('PowerAPI PATCH called')
        raw_dict = request.get_json(force=True)
        try:
            resp = 404
            if ident in members:
                # Update specific portions of the identified object
                if 'SetPoint' in raw_dict:
                    value = raw_dict['SetPoint']
                    min = members[ident]['SettingRangeMin']
                    max = members[ident]['SettingRangeMax']
                    if value == 0 or (value >= min and value <= max):
                        members[ident]['SetPoint'] = value
                        resp = members[ident], 200
                    else:
                        resp = 'SetPoint out of bounds', 400
                else:
                    resp = 'Invalid setting for PATCH', 400
        except Exception:
            traceback.print_exc()
            resp = INTERNAL_ERROR
        return resp

    # HTTP DELETE
    def delete(self, ident):
        logging.info('PowerAPI DELETE called')
        return 'DELETE is not supported', 405, {'Allow': 'GET, PATCH'}

# CreatePower
#
# Called internally to create instances of a ComputerSystem power control.
# These resources are affected by PowerAPI()
#
class CreatePower(Resource):

    def __init__(self, **kwargs):
        logging.info('CreatePower init called')
        if 'resource_class_kwargs' in kwargs:
            global wildcards
            wildcards = copy.deepcopy(kwargs['resource_class_kwargs'])

    # PUT
    # - Create the resource (since URI variables are avaiable)
    def put(self,ch_id,control_id,config):
        logging.info('CreatePower put called')
        try:
            global wildcards
            logging.debug('added config for %s/Controls/%s' % (ch_id, control_id))
            members[control_id]=config
            resp = config, 200
        except Exception:
            traceback.print_exc()
            resp = INTERNAL_ERROR
        return resp