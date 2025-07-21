# -*- coding:utf-8 -*-
# project name: project
# file name : module
import os
from configparser import ConfigParser

from LBank.client import client


class APIV2Excu:

    def __init__(self, _api_key, _secret_key):

        configfile=u'./config/constant.ini'
        filePath=os.path.abspath(configfile)
        # print(filePath)
        self.config = ConfigParser()
        self.config.read(filePath)

        self.apiKey= _api_key
        self.secrtkey= _secret_key
        privKey= _secret_key
        self.privKey="-----BEGIN RSA PRIVATE KEY-----\n"+privKey+"\n-----END RSA PRIVATE KEY-----"
        # print(self.privKey)
        self.signMethod=self.config.get("SIGNMETHOD","signmethod")
        self.excuReq=client()

    def ExcuRequests(self,par,str):
        url,me=self.config.get("URL",str).split(",")
        par["api_key"]=self.apiKey
        if self.signMethod=='RSA':
            res=self.excuReq.excuteRequestsRSA( par=par, url=url, method=me, privKey=self.privKey )
        else:
            res=self.excuReq.excuteRequestsHmac(par=par,url=url,method=me,secrtkey=self.secrtkey)
        return res
















