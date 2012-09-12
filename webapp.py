#!/usr/bin/env python

import time
import sys
import os
import logging
import json
import requests
from flask import Flask, Request, Response, request, redirect, render_template, url_for
from pymongo import Connection

from fbhelper import get_token, fb_call 
from rating import Worker, scan_feeds
import db

logging.basicConfig(level=0, format='%(levelname)s - - %(asctime)s %(message)s', datefmt='[%d/%b/%Y %H:%M:%S]')

FB_APP_ID = os.environ.get('FB_API_ID')
requests = requests.session()

app_url = 'https://graph.facebook.com/{0}'.format(FB_APP_ID)
FB_APP_NAME = json.loads(requests.get(app_url).content).get('name')
FB_APP_SECRET = os.environ.get('FB_API_SECRET')

FB_API_SCOPE = ['user_likes', 'user_photos', 'user_photo_video_tags']

app = Flask(__name__)
app.config.from_object(__name__)

@app.route('/welcome')
def welcome():
    return 'hello to appfog!'

@app.route('/env')
def env():
    return os.environ.get("VCAP_SERVICES", "{}")

@app.route('/mongo')
def mongotest():
    uri = db.mongodb_uri()
    conn = Connection(uri)
    coll = conn.db['ts']
    coll.insert(dict(now=int(time.time())))
    last_few = [str(x['now']) for x in coll.find(sort=[("_id", -1)], limit=10)]
    body = "\n".join(last_few)
    return Response(body, content_type="text/plain;charset=UTF-8")
    
@app.route('/userinfo')
def echo_users():
    uri = db.mongodb_uri()
    conn = Connection(uri)
    users = conn.db['users']

    body = ''
    for user in users.find():
        body += user.get('user_id', 'no_user_id') + ', ' + user.get('access_token', 'no_access_token')  + ', ' + str(user.get('expires', -1)) + ', ' + str(user.get('last_scan_time', -1)) + '\n'

    return Response(body, content_type="text/plain;charset=UTF-8")

@app.route('/purge')
def purge():
    db.purge()
    return Response('DB purged', content_type="text/plain;charset=UTF-8")

@app.route('/channel.html', methods=['GET', 'POST'])
def get_channel():
    return render_template('channel.html')

@app.route('/', methods=['GET', 'POST'])
def get_newsfeed():
    signed_request = request.form.get('signed_request')
    logging.info('signed_request=' + signed_request)
    result = get_token(signed_request, FB_APP_SECRET)
    if not result:
        return render_template('login.html', app_id=FB_APP_ID, namespace='newsfeedguardian')

    (user_id, access_token, expires) = result

    logging.info('access_token=' + str(access_token))

    channel_url = url_for('get_channel', _external=True)
    channel_url = channel_url.replace('http:', '').replace('https:', '')
    
    if access_token:
        db.insert_user_info(user_id, access_token, expires)
        last_scan_time = db.get_last_scan_time(user_id)

        feeds = fb_call('me/home', args={'access_token': access_token})

        scaned_feeds = scan_feeds(feeds, access_token, last_scan_time)
        db.update_last_scan_time(user_id, int(time.time()))
        return render_template('newsfeedlist.html', app_id=FB_APP_ID, token=access_token, url=request.url, 
            channel_url=channel_url, name=FB_APP_NAME, feeds=scaned_feeds)
    else:
        return render_template('login.html', app_id=FB_APP_ID, url=request.url, 
            channel_url=channel_url, name=FB_APP_NAME, namespace='newsfeedguardian')

w = None

@app.route('/startpolling', methods=['GET', 'POST'])
def start_polling():
    global w
    if w and not w.stop:
        logging.warning('Worker is already started, do not start it again')
    else:
        w = Worker()
        w.start()
    return Response('polling started', content_type="text/plain;charset=UTF-8")

@app.route('/stoppolling', methods=['GET', 'POST'])
def stop_polling():
    global w
    if w:  
        w.stop_work()
    return Response('polling stopped', content_type="text/plain;charset=UTF-8")

if __name__ == '__main__':
    app.run(debug=True)
