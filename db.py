#!/usr/bin/env python
import os
import sys
import json
from pymongo import Connection

def mongodb_uri():
    local = os.environ.get("MONGODB", None)
    if local:
        return local
    services = json.loads(os.environ.get("VCAP_SERVICES", "{}"))
    if services:
        creds = services['mongodb-1.8'][0]['credentials']
        uri = "mongodb://%s:%s@%s:%d/%s" % (
            creds['username'],
            creds['password'],
            creds['hostname'],
            creds['port'],
            creds['db'])
        #print >> sys.stderr, uri
        return uri
    else:
        raise Exception, "No services configured"

def purge():
    uri = mongodb_uri()
    conn = Connection(uri)
    conn.db.users.remove({})

def insert_user_info(user_id, access_token, expires):
    uri = mongodb_uri()
    conn = Connection(uri)
    users = conn.db['users']

    found = users.find_one({'user_id': user_id})
    if not found: 
        user = { 
            'user_id': user_id, 
            'access_token': access_token , 
            'expires' : expires 
        }
        users.insert(user)
    else:
        users.update({'user_id': user_id},
            {'$set': {'access_token': access_token , 'expires' : expires }})

def update_last_scan_time(user_id, time):
	uri = mongodb_uri()
	conn = Connection(uri)
	users = conn.db['users']
	users.update({'user_id': user_id}, {'$set': {'last_scan_time': time}})

def get_last_scan_time(user_id):
	uri = mongodb_uri()
	conn = Connection(uri)
	users = conn.db['users']
	user = users.find_one({'user_id': user_id})
	if user:
		return user.get('last_scan_time', 0)

	return 0