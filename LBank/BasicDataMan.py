# -*- coding:utf-8 -*-
# project name: project
# file name : BaseConfigMan
from LBank.APIV2Excu import APIV2Excu


class BaseConfigMan:
    def __init__(self, _api_key, _secret_key):

        self.excuReq=APIV2Excu(_api_key, _secret_key)

    def getcurrencyPairs(self):
        str = self.getcurrencyPairs.__name__

        par = {}

        self.excuReq.ExcuRequests( par, str )

    def getAccuracyInfo(self):
        str = self.getAccuracyInfo.__name__

        par = {}


        return self.excuReq.ExcuRequests( par, str )

    def getRatio(self,**d):
        str = self.getRatio.__name__

        par = {}

        self.excuReq.ExcuRequests( par, str )

    def getWithdrawConf(self,**d):
        str = self.getWithdrawConf.__name__

        par = {}
        for key in d.keys():
            par[ key ] = d[ key ]

        self.excuReq.ExcuRequests( par, str )

    def getTimestamp(self):
        str = self.getTimestamp.__name__

        par = {}

        self.excuReq.ExcuRequests( par, str )

