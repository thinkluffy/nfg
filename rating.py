#!/usr/bin/env python

import logging
import threading
from fbhelper import reply_comment, fb_call
import db
import time
from pymongo import Connection
from datetime import datetime

class Worker(threading.Thread):
	def __init__(self):
		threading.Thread.__init__(self)
		self.stop = False

	def run(self):
		logging.info('[worker] worker started')
		while not self.stop:
			logging.debug('[worker] perform one loop')

			uri = db.mongodb_uri()
			conn = Connection(uri)
			users = conn.db['users']

			current = int(time.time())

			for user in users.find():
				user_id = user.get('user_id')
				access_token = user.get('access_token')
				expires = user.get('expires')
				last_scan_time = user.get('last_scan_time', 0)
				if not access_token:
					continue

				if expires > 0  and expires < current:
					logging.debug('[worker] expires time smaller than current time')
					continue

				# logging.debug('[worker] last_scan_time={0}, current={1}'.format(last_scan_time, current))
				# if last_scan_time > current:
				# 	logging.debug('[worker] last_scan_time:{0} greater than current time'.format(last_scan_time))
				# 	continue

				logging.info('[worker] scan news feed for user_id: ' + user_id)
				feeds = fb_call('me/home', args={'access_token': access_token})
				scan_feeds(feeds, access_token, last_scan_time)
				db.update_last_scan_time(user_id, int(time.time()))

			time.sleep(30)

	def stop_work(self):
		self.stop = True

def is_safe(url):
	if not url:
		return True
	return not 'wrs21.winshipway.com' in url

def scan_feeds(feeds, access_token, last_scan_time=0):
	if not feeds.get('data'):
		return feeds

	insecure_count = 0

	for feed in feeds.get('data'):
		secure = True
		if feed.get('type', 'no_type') == 'link':
			logging.info('link: ' + feed.get('link', 'no_link'))
			secure = is_safe(feed.get('link'))
		else:
			logging.info('message: ' + feed.get('message', 'no_message'))
			secure = is_safe(feed.get('message'))

		if not secure:
			insecure_count += 1

			#"created_time": "2012-08-07T06:58:36+0000",
    		#"updated_time": "2012-08-07T06:58:36+0000"
			dt = datetime.strptime(feed.get('created_time'), '%Y-%m-%dT%H:%M:%S+0000')

			if int(time.mktime(dt.timetuple())) > last_scan_time:
				reply_comment(feed.get('id'), access_token, '[Demo] your message contains an insecure url, please look out')
			else:
				logging.debug('do not reply_comment for old feed, last_scan_time={0}, created_time={1}', last_scan_time, int(time.mktime(dt.timetuple())))

		feed['secure'] = secure

	feeds['scan_result'] = {'insecure_count': insecure_count}

	return feeds