# -*- coding:utf-8 -*-
# project name: project
# file name : ExcuHttp

import datetime
import os
import hashlib
import random
import string

from configparser import ConfigParser
import requests as req

import LBank.Util as Util


class client:

    def __init__(self):

        configfile=u'./config/constant.ini'

        cfg=ConfigParser()
        cfg.read(configfile)

        self.host=cfg.get("BASE","host")
        self.port=cfg.get("BASE","port")
        if self.port=='80':
            self.baseUrl=self.host
        else:
            self.baseUrl=self.host+":"+self.port

        self.util=Util.Util()

        # Use a dedicated requests Session and, by default, ignore system proxy
        # env to avoid unintended SOCKS routing that can cause connection refused.
        # Set HBOT_TRUST_ENV=1 (or HBOT_USE_PROXY=1) to honor HTTP(S)_PROXY/ALL_PROXY.
        self.session = req.Session()
        use_env_proxy = os.environ.get("HBOT_TRUST_ENV") == "1" or os.environ.get("HBOT_USE_PROXY") == "1"
        if not use_env_proxy:
            self.session.trust_env = False
            self.session.proxies = {}


    def excuteRequestsRSA(self, par, url, method, privKey):
        '''execute requests with RSA signature'''
        urlstr=self.baseUrl+url

        num = string.ascii_letters + string.digits

        randomstr = "".join( random.sample( num, 35 ) )

        t = str( datetime.datetime.now().timestamp() * 1000 ).split( "." )[ 0 ]

        header = {"Accept-Language": 'zh-CN', "signature_method": 'RSA', 'timestamp': t, 'echostr': randomstr}

        par['echostr'] = randomstr

        sign = self.util.buildRSASignV2( params=par, privKey=privKey, t=t )

        par[ 'sign' ] = sign

        del par["signature_method"]
        del par["timestamp"]
        del par['echostr']


        # print('get response with header {h} and param {p} by {url}'.format(h=header,p=par,url=urlstr))

        if method == 'post':
            res = self.session.post(url=urlstr, data=par, headers=header, timeout=30)
        else:
            res = self.session.get(url=urlstr, params=par, headers=header, timeout=30)

        if res.status_code == 200:
            resp = res.json()
            # print("resp", resp )
            return resp
        else:
            print( res.status_code )

    def excuteRequestsHmac(self, par, url, method,secrtkey):
        '''execute requests with HmacSHA256 signature'''
        urlstr = self.baseUrl + url

        num = string.ascii_letters + string.digits
        randomstr = "".join(random.sample(num, 35))

        t = str( datetime.datetime.now().timestamp() * 1000 ).split( "." )[ 0 ]

        header = {"Accept-Language": 'zh-CN', "signature_method":"HmacSHA256", 'timestamp': t, 'echostr': randomstr}

        par[ 'echostr' ] = randomstr

        # sign = self.util.buildRSASignV2( params=par, privKey=privKey, t=t )
        sign=self.util.buildHmacSHA256(params=par,secrtkey=secrtkey,t=t)

        par[ 'sign' ] = sign

        del par["signature_method"]
        del par["timestamp"]
        del par['echostr']

        # print( 'get response with header {h} and param {p} by {url}'.format( h=header, p=par, url=urlstr ) )

        if method == 'post':
            res = self.session.post(url=urlstr, data=par, headers=header, timeout=30)
        else:
            res = self.session.get(url=urlstr, params=par, headers=header, timeout=30)

        if res.status_code == 200:
            resp = res.json()
            # print( resp )
            return resp
        else:
            print( res.status_code )


