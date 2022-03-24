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

# EventService API File

"""
Dynamic resources:
 - Event Service
    GET/PATCH        /redfish/v1/EventService
    GET/POST         /redfish/v1/EventService/Subscriptions
    GET/PATCH/DELETE /redfish/v1/EventService/Subscriptions/{id}
Resources that sent events:
 - computer_systems_api.ResetAction_API
"""

import g

import sys, traceback
import logging
import copy
import json
import urllib.request
from flask import Flask, request, make_response, render_template
from flask_restful import reqparse, Api, Resource

from .response import success_response, simple_error_response, error_404_response, error_not_allowed_response

from threading import Thread

e_config = {}
s_config = {}
s_generator = None
members = {}
required = {'Destination', 'EventTypes'}
eventTemplates = {}
id = 1

NOT_FOUND_ERROR = {"Status": 404, "Message": "Attribute Does Not Exist"}
INTERNAL_ERROR = 500

# EventWorker
#
# EventWorker threads are spawned per subscription per event for sending
# redfish events to subscribers to the EventService.
class EventWorker(Thread):
    """
    Worker class for sending event messages to clients
    """
    def __init__(self, dest_uri, event):
        super(EventWorker, self).__init__()
        self.dest_uri = dest_uri
        self.event = event

    def run(self):
        try:
            logging.debug('Sending event')
            logging.debug(self.event)
            request = urllib.request.Request(self.dest_uri)
            request.add_header('Content-Type', 'application/json')
            urllib.request.urlopen(request, json.dumps(self.event).encode('utf-8'), 15)
            logging.debug('Send succeeded')
        except Exception:
            traceback.print_exc()
            logging.debug('Send failed')
            pass

# send_event
#
# Spawns threads per subscription per event for sending
# redfish events to subscribers of the EventService.
# This function adds the Context field to the event and
# its event records (if specified by the template).
def send_event(event, type):
    for name, sub in members.items():
        e = event.copy()
        event_types = sub['EventTypes']
        dest_uri = sub['Destination']
        ctx = ""
        if 'Context' in sub:
            ctx = sub['Context']

        e['Context'] = ctx
        for er in e['Events']:
            # Adds Context but only if our event template allows us to
            er['Context'] = er['Context'].format(Context = ctx)
        if type in event_types:
            EventWorker(dest_uri, e).start()

# EventServiceAPI
#
# Services GET and PATCH requests for the EventService resource.
class EventServiceAPI(Resource):

    def __init__(self, **kwargs):
        logging.info('EventServiceAPI init called')
        self.allow = 'GET, PATCH'

    # HTTP GET
    def get(self):
        logging.info('EventServiceAPI GET called')
        try:
            resp = e_config, 200
        except Exception:
            traceback.print_exc()
            resp = simple_error_response('Server encountered an unexpected Error', 500)
        return resp

    # HTTP PUT
    def put(self):
        logging.info('EventServiceAPI PUT called')
        return error_not_allowed_response(e_config['@odata.id'], 'PUT', {'Allow': self.allow})

    # HTTP POST
    def post(self):
        logging.info('EventServiceAPI POST called')
        return error_not_allowed_response(e_config['@odata.id'], 'POST', {'Allow': self.allow})

    # HTTP PATCH
    def patch(self):
        logging.info('EventServiceAPI PATCH called')
        raw_dict = request.get_json(force=True)
        try:
            resp = success_response('PATCH request successful', 200)
            for key, value in raw_dict.items():
                if key in {'DeliveryRetryAttempts', 'DeliveryRetryIntervalSeconds'}:
                    e_config[key] = value
                else:
                    resp = simple_error_response('Invalid setting for PATCH', 400)
        except Exception:
            traceback.print_exc()
            resp = simple_error_response('Server encountered an unexpected Error', 500)
        return resp

    # HTTP DELETE
    def delete(self):
        logging.info('EventServiceAPI DELETE called')
        return error_not_allowed_response(e_config['@odata.id'], 'DELETE', {'Allow': self.allow})

# SubscriptionCollectionAPI
#
# Services GET and POST requests for the subscriptions collection.
# POST requests will add new subscriptions.
class SubscriptionCollectionAPI(Resource):

    def __init__(self, **kwargs):
        logging.info('SubscriptionCollectionAPI init called')
        self.allow = 'GET, POST'

    # HTTP GET
    def get(self):
        logging.info('SubscriptionCollectionAPI GET called')
        try:
            resp = s_config, 200
        except Exception:
            traceback.print_exc()
            resp = simple_error_response('Server encountered an unexpected Error', 500)
        return resp

    # HTTP PUT
    def put(self):
        logging.info('SubscriptionCollectionAPI PUT called')
        return error_not_allowed_response(s_config['@odata.id'], 'PUT', {'Allow': self.allow})

    # HTTP POST
    def post(self):
        global id
        logging.info('SubscriptionCollectionAPI POST called')
        raw_dict = request.get_json(force=True)
        for field in required:
            if field not in raw_dict:
                return simple_error_response('%s is required' % (field) , 400)
        ident = '%d' % id
        id += 1
        
        destination = raw_dict['Destination']
        event_types = raw_dict['EventTypes']
        for evType in event_types:
            if evType not in e_config['EventTypesForSubscription']:
                return 'Invalid EventType %s' % evType, 400
        if 'Context' in raw_dict:
            context = raw_dict['Context']
        else:
            context = None
        if 'RegistryPrefixes' in raw_dict:
            registry_prefixes = raw_dict['RegistryPrefixes']
        else:
            registry_prefixes = None
        CreateSubscription().put(ident, destination, event_types, context, registry_prefixes)
        return success_response('/redfish/v1/EventService/Subscriptions/%s' % ident, 201)

    # HTTP PATCH
    def patch(self):
        logging.info('SubscriptionCollectionAPI PATCH called')
        return error_not_allowed_response(s_config['@odata.id'], 'PATCH', {'Allow': self.allow})

    # HTTP DELETE
    def delete(self):
        logging.info('SubscriptionCollectionAPI DELETE called')
        return error_not_allowed_response(s_config['@odata.id'], 'DELETE', {'Allow': self.allow})

# SubscriptionAPI
#
# Services GET, PATCH, and DELETE requests for managing Redfish event subscriptions.
# DELETE requests will remove the subscription from the subscription collection.
class SubscriptionAPI(Resource):

    def __init__(self, **kwargs):
        logging.info('SubscriptionAPI init called')
        self.allow = 'GET, PATCH, DELETE'

    # HTTP GET
    def get(self, ident):
        logging.info('SubscriptionAPI GET called')
        try:
            resp = error_404_response(request.path)
            if ident in members:
                resp = members[ident], 200
        except Exception:
            traceback.print_exc()
            resp = simple_error_response('Server encountered an unexpected Error', 500)
        return resp

    # HTTP PUT
    def put(self, ident):
        logging.info('SubscriptionAPI PUT called')
        try:
            resp = error_404_response(request.path)
            if ident in members:
                resp = error_not_allowed_response(members[ident]['@odata.id'], 'PUT', {'Allow': self.allow})
        except Exception:
            traceback.print_exc()
            resp = simple_error_response('Server encountered an unexpected Error', 500)
        return resp

    # HTTP POST
    def post(self, ident):
        logging.info('SubscriptionAPI POST called')
        try:
            resp = error_404_response(request.path)
            if ident in members:
                resp = error_not_allowed_response(members[ident]['@odata.id'], 'POST', {'Allow': self.allow})
        except Exception:
            traceback.print_exc()
            resp = simple_error_response('Server encountered an unexpected Error', 500)
        return resp

    # HTTP PATCH
    def patch(self, ident):
        logging.info('SubscriptionAPI PATCH called')
        raw_dict = request.get_json(force=True)
        try:
            resp = error_404_response(request.path)
            if ident in members:
                for field, value in raw_dict.items():
                    if field not in {'RegistryPrefixes', 'Destination', 'Context'}:
                        return 'Field %s is not patchable' % field, 400
                    else:
                        if field == 'RegistryPrefixes' and value != []:
                            for evType in value:
                                if evType not in e_config['EventTypesForSubscription']:
                                    return 'Invalid EventType %s' % evType, 400
                        members[ident][field] = value
                resp = success_response('PATCH request successful', 200)
        except Exception:
            traceback.print_exc()
            resp = simple_error_response('Server encountered an unexpected Error', 500)
        return resp

    # HTTP DELETE
    def delete(self, ident):
        logging.info('SubscriptionAPI DELETE called')
        try:
            resp = error_404_response(request.path)
            if ident in members:
                s_config['Members'].remove(members[ident]['@odata.id'])
                del members[ident]
                resp = success_response('Resource deleted', 200)
        except Exception:
            traceback.print_exc()
            resp = simple_error_response('Server encountered an unexpected Error', 500)
        return resp

# CreateEventService
#
# Called internally to create an instance of the EventService and initialize its subresources. This
# adds '/redfish/v1/EventService', '/redfish/v1/EventService/Subscriptions', and
# '/redfish/v1/EventService/Subscriptions/<string:ident>' resources to flask. These resources are
# affected by EventServiceAPI(), SubscriptionCollectionAPI(), and SubscriptionAPI()
class CreateEventService(Resource):

    def __init__(self, **kwargs):
        logging.info('CreateEventService init called')

    # Attach APIs for subordinate resource(s). Attach the APIs for
    # a resource collection and its singletons.
    def put(self, event_config, sub_config, sub_generator):
        logging.info('CreateEventService put called')
        try:
            global e_config
            global s_config
            global s_generator
            e_config = event_config
            s_config = sub_config
            s_generator = sub_generator
            g.api.add_resource(EventServiceAPI,             '/redfish/v1/EventService')
            g.api.add_resource(SubscriptionCollectionAPI,   '/redfish/v1/EventService/Subscriptions')
            g.api.add_resource(SubscriptionAPI,             '/redfish/v1/EventService/Subscriptions/<string:ident>')
            resp = e_config, 200
        except Exception:
            traceback.print_exc()
            resp = simple_error_response('Server encountered an unexpected Error', 500)
        return resp

# CreateSubscription
#
# Called internally to create an instance of an event subscription resource for the EventService.
# This resource is affected by SubscriptionCollectionAPI() and SubscriptionAPI().
class CreateSubscription(Resource):

    def __init__(self, **kwargs):
        logging.info('CreateSubscription init called')

    # Attach APIs for subordinate resource(s). Attach the APIs for
    # a resource collection and its singletons.
    def put(self, ident, destination, event_types, context=None, registry_prefixes=None):
        logging.info('CreateSubscription put called')
        try:
            wildcards['id'] = ident
            config = s_generator(wildcards)
            config['Destination'] = destination
            config['EventTypes'] = event_types
            if context is not None:
                config['Context'] = context
            if registry_prefixes is not None:
                config['RegistryPrefixes'] = registry_prefixes
            members[ident] = config
            s_config['Members'].append(config['@odata.id'])
            resp = config, 200
        except Exception:
            traceback.print_exc()
            resp = simple_error_response('Server encountered an unexpected Error', 500)
        return resp