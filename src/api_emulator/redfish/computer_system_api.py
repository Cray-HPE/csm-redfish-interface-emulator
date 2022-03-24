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

# ComputerSystem API File

"""
Dynamic resources:
 - System Power Actions
    GET      /redfish/v1/Systems/{sys_id}
    GET/POST /redfish/v1/Systems/{sys_id}/Actions/ComputerSystem.Reset
"""

import g

import sys, traceback
import logging
import copy
from flask import Flask, request, make_response, render_template
from flask_restful import reqparse, Api, Resource

from threading import Thread
from time import sleep

from .event_generator import GenEvent, GenEventRecord
from .event_service_api import send_event
from .response import success_response, simple_error_response, error_404_response, error_not_allowed_response

members = {}
members_actions = {}
members_reset_thread = {}

reboot_actions = {'GracefulRestart', 'ForceRestart', 'PushPowerButton'}
off_actions = {'Off', 'ForceOff', 'GracefulShutdown', 'Nmi'}
on_actions = {'On', 'ForceOn'}

# ResetWorker
#
# Worker thread for performing emulated asynchronous computer system power resets.
#
class ResetWorker(Thread):
    def __init__(self, sys_id):
        super(ResetWorker, self).__init__()
        self.sys_id = sys_id

    def run(self):
        members[self.sys_id]['PowerState'] = 'Off'
        members[self.sys_id]['Status']['State'] = 'Disabled'
        send_power_event(self.sys_id, 'Off')
        sleep(5)
        members[self.sys_id]['PowerState'] = 'PoweringOn'
        members[self.sys_id]['Status']['State'] = 'Starting'
        send_power_event(self.sys_id, 'On')
        sleep(5)
        members[self.sys_id]['PowerState'] = 'On'
        members[self.sys_id]['Status']['State'] = 'Enabled'

# PowerOnWorker
#
# Worker thread for performing emulated asynchronous computer system power on actions.
#
class PowerOnWorker(Thread):
    def __init__(self, sys_id):
        super(PowerOnWorker, self).__init__()
        self.sys_id = sys_id

    def run(self):
        members[self.sys_id]['PowerState'] = 'PoweringOn'
        members[self.sys_id]['Status']['State'] = 'Starting'
        send_power_event(self.sys_id, 'On')
        sleep(5)
        members[self.sys_id]['PowerState'] = 'On'
        members[self.sys_id]['Status']['State'] = 'Enabled'

def send_power_event(id, power_state):
    ooc = members[id]['@odata.id']
    er = GenEventRecord('Power', powerState=power_state, OriginOfCondition=ooc)
    e = GenEvent([er])
    send_event(e, 'Alert')

# ComputerSystemAPI
#
# This services GET requests for computer systems. These are affected by
# POST requests to ResetAction_API()
#
class ComputerSystemAPI(Resource):

    def __init__(self, **kwargs):
        logging.info('ComputerSystemAPI init called')
        self.allow = 'GET'
        try:
            global wildcards
            wildcards = kwargs
        except Exception:
            traceback.print_exc()

    # HTTP GET
    def get(self, ident):
        logging.info('ComputerSystemAPI GET called')
        try:
            # Find the entry with the correct value for Id
            resp = error_404_response(request.path)
            if ident in members:
                resp = members[ident], 200
        except Exception:
            traceback.print_exc()
            resp = simple_error_response('Server encountered an unexpected Error', 500)
        return resp

    # HTTP PUT
    def put(self, ident):
        logging.info('ComputerSystemAPI PUT called')
        try:
            resp = error_404_response(request.path)
            if ident in members:
                resp = error_not_allowed_response(members[ident]['@odata.id'], request.method, {'Allow': self.allow})
        except Exception:
            traceback.print_exc()
            resp = simple_error_response('Server encountered an unexpected Error', 500)
        return resp

    # HTTP POST
    def post(self, ident):
        logging.info('ComputerSystemAPI POST called')
        try:
            resp = error_404_response(request.path)
            if ident in members:
                resp = error_not_allowed_response(members[ident]['@odata.id'], request.method, {'Allow': self.allow})
        except Exception:
            traceback.print_exc()
            resp = simple_error_response('Server encountered an unexpected Error', 500)
        return resp

    # HTTP PATCH
    def patch(self, ident):
        logging.info('ComputerSystemAPI PATCH called')
        try:
            resp = error_404_response(request.path)
            if ident in members:
                resp = error_not_allowed_response(members[ident]['@odata.id'], request.method, {'Allow': self.allow})
        except Exception:
            traceback.print_exc()
            resp = simple_error_response('Server encountered an unexpected Error', 500)
        return resp

    # HTTP DELETE
    def delete(self, ident):
        logging.info('ComputerSystemAPI DELETE called')
        try:
            resp = error_404_response(request.path)
            if ident in members:
                resp = error_not_allowed_response(members[ident]['@odata.id'], request.method, {'Allow': self.allow})
        except Exception:
            traceback.print_exc()
            resp = simple_error_response('Server encountered an unexpected Error', 500)
        return resp

# CreateComputerSystem
#
# Called internally to create instances of a ComputerSystem. These
# resources are affected by ResetAction_API()
#
class CreateComputerSystem(Resource):
    def __init__(self, **kwargs):
        logging.info('CreateComputerSystem init called')
        if 'resource_class_kwargs' in kwargs:
            global wildcards
            wildcards = copy.deepcopy(kwargs['resource_class_kwargs'])

    # Create instance
    def put(self, ident, config, rst_actions):
        logging.info('CreateComputerSystem put called')
        try:
            # global config
            global wildcards
            logging.debug('added config for Systems/%s' % ident)
            members[ident] = config
            members_actions[ident] = rst_actions
            members_reset_thread[ident] = None

            resp = config, 200
        except Exception:
            traceback.print_exc()
            resp = INTERNAL_ERROR
        logging.info('CreateComputerSystem init exit')
        return resp

# ResetAction_API
#
# This services ResetAction POST requests to emulate computer system power actions.
# POST requests that result in PowerState changes will generate Redfish events for
# subscribers to the EventService.
#
class ResetAction_API(Resource):

    def __init__(self, **kwargs):
        self.allow = 'POST'
    
    # HTTP POST
    def post(self, ident):
        logging.info('ResetAction_API POST called')
        raw_dict = request.get_json(force=True)
        logging.info(raw_dict)
        try:
            resp = error_404_response(request.path)
            if ident in members:
                if 'ResetType' in raw_dict:
                    value = raw_dict['ResetType']
                    if value in members_actions[ident]['Parameters'][0]['AllowableValues']:
                        state = members[ident]['PowerState']
                        
                        if members_reset_thread[ident] is not None and members_reset_thread[ident].is_alive():
                            # Ignore other power actions if we have a pending thread.
                            logging.info('Thread is running. Ignoring request')
                        elif value in reboot_actions:
                            if state == 'On':
                                logging.info('Starting reset thread')
                                members_reset_thread[ident] = ResetWorker(ident)
                                members_reset_thread[ident].start()
                            else:
                                logging.info('Reset action with current PowerState Off. Starting reset thread')
                                members_reset_thread[ident] = PowerOnWorker(ident)
                                members_reset_thread[ident].start()
                        elif value in off_actions:
                            logging.info('Powering Off')
                            members[ident]['PowerState'] = 'Off'
                            members[ident]['Status']['State'] = 'Disabled'
                            send_power_event(ident, 'Off')
                        elif value in on_actions:
                            logging.info('Starting reset thread')
                            members_reset_thread[ident] = PowerOnWorker(ident)
                            members_reset_thread[ident].start()
                        resp = members[ident], 200
                    else:
                        resp = simple_error_response('Invalid ResetType', 400)
                else:
                    resp = simple_error_response('Invalid setting for POST', 400)
        except Exception:
            traceback.print_exc()
            resp = INTERNAL_ERROR
        return resp

    # HTTP GET
    def get(self, ident):
        try:
            resp = error_404_response(request.path)
            if ident in members:
                resp = error_not_allowed_response(request.path, request.method, {'Allow': self.allow})
        except Exception:
            traceback.print_exc()
            resp = simple_error_response('Server encountered an unexpected Error', 500)
        return resp

    # HTTP PATCH
    def patch(self, ident):
        try:
            resp = error_404_response(request.path)
            if ident in members:
                resp = error_not_allowed_response(request.path, request.method, {'Allow': self.allow})
        except Exception:
            traceback.print_exc()
            resp = simple_error_response('Server encountered an unexpected Error', 500)
        return resp

    # HTTP PUT
    def put(self, ident):
        try:
            resp = error_404_response(request.path)
            if ident in members:
                resp = error_not_allowed_response(request.path, request.method, {'Allow': self.allow})
        except Exception:
            traceback.print_exc()
            resp = simple_error_response('Server encountered an unexpected Error', 500)
        return resp

    # HTTP DELETE
    def delete(self, ident):
        try:
            resp = error_404_response(request.path)
            if ident in members:
                resp = error_not_allowed_response(request.path, request.method, {'Allow': self.allow})
        except Exception:
            traceback.print_exc()
            resp = simple_error_response('Server encountered an unexpected Error', 500)
        return resp