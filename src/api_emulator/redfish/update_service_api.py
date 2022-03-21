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

# Update Service API File

"""
Dynamic resources:
 - Firmware Update
    GET       /redfish/v1/UpdateService/FirmwareInventory/{target_id}
    POST      /redfish/v1/UpdateService/SimpleUpdate
    GET/PATCH /redfish/v1/UpdateService/FirmwareInventory/Config
"""

import g

import sys, traceback
import logging
import copy
from flask import Flask, request, make_response, render_template
from flask_restful import reqparse, Api, Resource
from queue import Queue
from threading import Thread
from time import sleep

members = {}
configAPI = {}
q = Queue(maxsize = 10)

INTERNAL_ERROR = 500

_CONFIG_TEMPLATE = \
{
  "Id": "UpdateServiceConfigInfo",
  "Name": "UpdateServiceConfig",
  "Description": "Use PATCH operations to set the below values to affect Update Service actions.",
  "Parameters": [
    {
      "DataType": "StringArray",
      "Name": "Fail",
      "Description": "List of targets that will fail update actions.",
      "AllowableValues": []
    },
    {
      "DataType": "Int",
      "Name": "Hang",
      "Description": "Amount of time in seconds to Hang."
    },
    {
      "DataType": "Int",
      "Name": "UpdateTime",
      "Description": "Amount of time in seconds to for updates to take."
    }
  ],
  "CurrentValues": {
    "Fail": [],
    "Hang": 0,
    "UpdateTime": 30
  }
}

# firmware_update
#
# The object that gets constructed and queued by SimpleUpdateAPI() to be used
# by the UpdateWorker() thread. Behavior of the updates is configured using the
# UpdateServiceConfigAPI() values at the time the firmware_update is construced
# by SimpleUpdateAPI().
#
class firmware_update:
    def __init__(self, imageURI, target):
        self.imageURI = imageURI
        self.target = target
        self.updateTime = configAPI['config']['CurrentValues']['UpdateTime']
        if target in configAPI['config']['CurrentValues']['Fail']:
            self.fail = True
        else:
            self.fail = False

# UpdateWorker
#
# Worker thread for performing emulated asynchronous SimpleUpdates. Updates are
# queued by SimpleUpdateAPI(). Behavior of the updates is configured using the
# UpdateServiceConfigAPI() values at the time the update is constructed by
# SimpleUpdateAPI().
#
class UpdateWorker(Thread):
    def __init__(self):
        super(UpdateWorker, self).__init__()

    def run(self):
        logging.info('Starting update thread')
        while True:
            update = q.get()
            logging.info('Starting update - Image = %s, Target = %s, UpdateTime = %d, Fail = %s' % (update.imageURI, update.target, update.updateTime, update.fail))
            #TODO: Make this follow the image URL
            if update.updateTime > 0:
                sleep(update.updateTime)
            if update.fail:
                members[update.target]['Status']['Health'] = 'ERROR'
            else:
                members[update.target]['Status']['Health'] = 'OK'
                members[update.target]['Version'] = update.imageURI
            logging.info('Starting complete for %s' % update.target)

# Start the SimpleUpdate worker thread.
worker = UpdateWorker().start()

# UpdateServiceConfigAPI
#
# This services GET and PATCH requests to affect the behavior of SimpleUpdateAPI()
# POST requests. Used for customizing the behavior of the SimpleUpdateAPI such as
# changing the update time or simulating failures.
#
class UpdateServiceConfigAPI(Resource):

    def __init__(self, **kwargs):
        logging.info('UpdateServiceConfigAPI init called')

    # HTTP GET
    def get(self):
        logging.info('UpdateServiceConfigAPI GET called')
        try:
            resp = configAPI['config'], 200
        except Exception:
            traceback.print_exc()
            resp = INTERNAL_ERROR
        return resp

    # HTTP PUT
    def put(self, ident):
        logging.info('UpdateServiceConfigAPI PUT called')
        return 'PUT is not supported', 405, {'Allow': 'GET, PATCH'}

    # HTTP POST
    def post(self):
        logging.info('UpdateServiceConfigAPI POST called')
        return 'POST is not supported', 405, {'Allow': 'GET, PATCH'}

    # HTTP PATCH
    def patch(self):
        logging.info('UpdateServiceConfigAPI PATCH called')
        raw_dict = request.get_json(force=True)
        logging.info(raw_dict)
        tempValues = {}
        try:
            resp = configAPI['config']['CurrentValues'], 200
            for setting in {'Fail', 'Hang', 'UpdateTime'}:
                if setting in raw_dict:
                    value = raw_dict[setting]
                    if setting == 'Fail':
                        for target in value:
                            if target not in configAPI['config']['Parameters'][0]['AllowableValues']:
                                resp = 'Invalid target for Fail, %s' % target, 400
                                return resp
                    else:
                        if not isinstance(value, int):
                            resp = 'Invalid value for %s, %s. Must be int.' % (setting, value), 400
                            return resp
                    tempValues[setting] = value
                else:
                    tempValues[setting] = configAPI['config']['CurrentValues'][setting]
            configAPI['config']['CurrentValues'] = tempValues
            resp = configAPI['config']['CurrentValues'], 200
        except Exception:
            traceback.print_exc()
            resp = INTERNAL_ERROR
        return resp

    # HTTP DELETE
    def delete(self):
        logging.info('UpdateServiceAPI DELETE called')
        return 'DELETE is not supported', 405, {'Allow': 'GET, PATCH'}

# UpdateServiceAPI
#
# This services GET requests for firmware targets. These are affected by
# POST requests to SimpleUpdateAPI()
#
class UpdateServiceAPI(Resource):

    def __init__(self, **kwargs):
        logging.info('UpdateServiceAPI init called')
        try:
            global wildcards
            wildcards = kwargs
        except Exception:
            traceback.print_exc()

    # HTTP GET
    def get(self, ident):
        logging.info('UpdateServiceAPI GET called')
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
        logging.info('UpdateServiceAPI PUT called')
        return 'PUT is not supported', 405, {'Allow': 'GET'}

    # HTTP POST
    def post(self, ident):
        logging.info('UpdateServiceAPI POST called')
        return 'POST is not supported', 405, {'Allow': 'GET'}

    # HTTP PATCH
    def patch(self, ident):
        logging.info('UpdateServiceAPI POST called')
        return 'PATCH is not supported', 405, {'Allow': 'GET'}

    # HTTP DELETE
    def delete(self, ident):
        logging.info('UpdateServiceAPI DELETE called')
        return 'DELETE is not supported', 405, {'Allow': 'GET'}

# CreateFirmwareTarget
#
# Called internally to create instances of a FirmwareTarget. These
# resources are affected by SimpleUpdateAPI()
#
class CreateFirmwareTarget(Resource):

    def __init__(self, **kwargs):
        logging.info('CreateFirmwareTarget init called')
        if 'resource_class_kwargs' in kwargs:
            global wildcards
            wildcards = copy.deepcopy(kwargs['resource_class_kwargs'])

    # PUT
    # - Create the resource (since URI variables are avaiable)
    def put(self,target_id,config):
        logging.info('CreateFirmwareTarget put called')
        try:
            global wildcards
            logging.debug('added config for %s' % target_id)
            members[target_id]=config
            configAPI['config'] = copy.deepcopy(_CONFIG_TEMPLATE)
            for member in members.keys():
                configAPI['config']['Parameters'][0]['AllowableValues'].append(member)
            resp = config, 200
        except Exception:
            traceback.print_exc()
            resp = INTERNAL_ERROR
        return resp

# SimpleUpdateAPI
#
# This services SimpleUpdate POST requests to emulate firmware updates.
#
class SimpleUpdateAPI(Resource):
    def __init__(self, **kwargs):
        logging.info('SimpleUpdateAPI init called')
        try:
            global wildcards
            wildcards = kwargs
        except Exception:
            traceback.print_exc()

    # HTTP GET
    def get(self):
        return 'GET is not supported', 405, {'Allow': 'POST'}

    # HTTP PUT
    def put(self):
        logging.info('SimpleUpdateAPI PUT called')
        return 'PUT is not supported', 405, {'Allow': 'POST'}

    # HTTP POST
    def post(self):
        logging.info('SimpleUpdateAPI POST called')
        raw_dict = request.get_json(force=True)
        logging.info(raw_dict)
        imageURI = ''
        update_targets = []
        
        try:
            if configAPI['config']['CurrentValues']['Hang'] > 0:
                logging.info('Hanging for %d seconds' % configAPI['config']['CurrentValues']['Hang'])
                sleep(configAPI['config']['CurrentValues']['Hang'])
                logging.info('Finished hanging')
                return 'Hung', 500
            
            # Update specific portions of the identified object
            if 'ImageURI' in raw_dict:
                imageURI = raw_dict['ImageURI']
            else:
                return 'ImageURI is required', 400
            if 'Targets' in raw_dict:
                targets = raw_dict['Targets']
                for targetURL in targets:
                    target = targetURL.replace('/redfish/v1/UpdateService/FirmwareInventory/', '')
                    if target not in members:
                        return 'Invalid target, %s' % target, 400
                    if members[target]['Updateable'] == False:
                        return 'Invalid target, %s. Not Updateable.' % target, 400
                    if members[target]['Status'] == 'UPDATING':
                        return 'Invalid target, %s. Target is updating.' % target, 400
                    update_targets.append(target)
            if len(update_targets) == 0:
                update_targets.append('BMC')
            for target in update_targets:
                update = firmware_update(imageURI, target)
                q.put(update)
                members[target]['Status']['Health'] = 'UPDATING'
            resp = 'Request Secceeded', 200
        except Exception:
            traceback.print_exc()
            resp = INTERNAL_ERROR
        return resp

    # HTTP PATCH
    def patch(self):
        logging.info('SimpleUpdateAPI PATCH called')
        return 'PATCH is not supported', 405, {'Allow': 'POST'}

    # HTTP DELETE
    def delete(self):
        logging.info('UpdateServiceAPI DELETE called')
        return 'DELETE is not supported', 405, {'Allow': 'POST'}
