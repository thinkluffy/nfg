#!/usr/bin/env python

import urllib
import logging
import json
import requests
import hmac
import hashlib
import base64
from base64 import urlsafe_b64decode, urlsafe_b64encode
from flask import Flask, Request, Response, request, redirect, render_template, url_for

# def oauth_login_url(preserve_path=True, next_url=None):
#     fb_login_uri = ("https://www.facebook.com/dialog/oauth"
#                     "?client_id=%s&redirect_uri=%s" %
#                     (FB_APP_ID, get_home()))

#     if FB_API_SCOPE:
#         fb_login_uri += "&scope=%s" % ",".join(FB_API_SCOPE)
#     return fb_login_uri

def simple_dict_serialisation(params):
    return "&".join(map(lambda k: "%s=%s" % (k, params[k]), params.keys()))

def base64_url_encode(data):
    return base64.urlsafe_b64encode(data).rstrip('=')

def base64_url_decode(inp):
    padding_factor = (4 - len(inp) % 4) % 4
    inp += "="*padding_factor 
    return base64.b64decode(unicode(inp).translate(dict(zip(map(ord, u'-_'), u'+/'))))

def parse_signed_request(signed_request, secret):
    (encoded_sig, payload) = signed_request.split('.', 2)

    sig = base64_url_decode(encoded_sig)
    data = json.loads(base64_url_decode(payload))

    if data.get('algorithm').upper() != 'HMAC-SHA256':
        logging.error('Unknown algorithm')
        return None
    
    expected_sig = hmac.new(secret, msg=payload, digestmod=hashlib.sha256).digest()

    if sig != expected_sig:
        logging.error('Bad Signed JSON signature!')
        return None

    logging.debug('valid signed request received..')
    return data

def fbapi_get_string(path,
    domain=u'graph', params=None, access_token=None,
    encode_func=urllib.urlencode):
    """Make an API call"""

    if not params:
        params = {}
    params[u'method'] = u'GET'
    if access_token:
        params[u'access_token'] = access_token

    for k, v in params.iteritems():
        if hasattr(v, 'encode'):
            params[k] = v.encode('utf-8')

    url = u'https://' + domain + u'.facebook.com' + path
    params_encoded = encode_func(params)
    url = url + params_encoded
    result = requests.get(url).content

    return result

def fbapi_auth(code, app_id, app_secret):
    params = {'client_id': app_id,
              'redirect_uri': get_home(),
              'client_secret': app_secret,
              'code': code}

    result = fbapi_get_string(path=u"/oauth/access_token?", params=params,
                              encode_func=simple_dict_serialisation)
    pairs = result.split("&", 1)
    result_dict = {}
    for pair in pairs:
        (key, value) = pair.split("=")
        result_dict[key] = value
    return (result_dict["access_token"], result_dict["expires"])

def fbapi_get_application_access_token(client_id, app_secret):
    token = fbapi_get_string(
        path=u"/oauth/access_token",
        params=dict(grant_type=u'client_credentials', client_id=client_id,
                    client_secret=app_secret),
        domain=u'graph')

    token = token.split('=')[-1]
    if not str(id) in token:
        print 'Token mismatch: %s not in %s' % (id, token)
    return token

def fql(fql, token, args=None):
    if not args:
        args = {}

    args["query"], args["format"], args["access_token"] = fql, "json", token

    url = "https://api.facebook.com/method/fql.query"

    r = requests.get(url, params=args)
    return json.loads(r.content)
    
def fb_call(call, args=None):
    url = "https://graph.facebook.com/{0}".format(call)
    r = requests.get(url, params=args)
    return json.loads(r.content)

def get_home():
    return 'https://' + request.host + '/'

def get_token(signed_request, app_secret):
    # if request.args.get('code', None):
    #     return fbapi_auth(request.args.get('code'))[0]

    data = parse_signed_request(signed_request, app_secret)
    logging.debug('data=' + str(data))

    if data.get('user_id') and data.get('oauth_token'):
        return (data.get('user_id'), data.get('oauth_token'), data.get('expires'))

    # cookie_key = 'fbsr_{0}'.format(FB_APP_ID)

    # if cookie_key in request.cookies:
    #     logging.info('cookie_key=' + str(cookie_key) + ' in cookies')

    #     c = request.cookies.get(cookie_key)
    #     encoded_data = c.split('.', 2)

    #     sig = encoded_data[0]
    #     data = json.loads(urlsafe_b64decode(str(encoded_data[1])))

    #     if not data['algorithm'].upper() == 'HMAC-SHA256':
    #         raise ValueError('unknown algorithm {0}'.format(data['algorithm']))

    #     h = hmac.new(FB_APP_SECRET, digestmod=hashlib.sha256)
    #     h.update(encoded_data[1])
    #     expected_sig = urlsafe_b64encode(h.digest()).replace('=', '')

    #     if sig != expected_sig:
    #         raise ValueError('bad signature')

    #     code =  data['code']

    #     params = {
    #         'client_id': FB_APP_ID,
    #         'client_secret': FB_APP_SECRET,
    #         'redirect_uri': '',
    #         'code': data['code']
    #     }

    #     from urlparse import parse_qs
    #     r = requests.get('https://graph.facebook.com/oauth/access_token', params=params)
    #     token = parse_qs(r.content).get('access_token')

    #     return token

def reply_comment(feed_id, access_token, message):
    params = {
        'access_token': access_token,
        'message': message
    }
    r = requests.post('https://graph.facebook.com/{0}/comments'.format(feed_id), params=params)
    print r.content