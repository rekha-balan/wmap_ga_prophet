from __future__ import print_function
import httplib2
import os

from apiclient import discovery
from oauth2client import client
from oauth2client import tools
from oauth2client.file import Storage

from datetime import datetime as dt

import pandas as pd
import numpy as np
from fbprophet import Prophet
import matplotlib.pyplot as plt

try:
    import argparse
    flags = argparse.ArgumentParser(parents=[tools.argparser]).parse_args()
except ImportError:
    flags = None

SCOPES = 'https://www.googleapis.com/auth/analytics.readonly' # GoogleAnalyticsの権限
CLIENT_SECRET_FILE = './secret/client_secret_XXXXXXXXXXXXXXX.apps.googleusercontent.com.json' # Google API Consoleから事前に取得して設置する。自身の環境に合わせて変更してください。
APPLICATION_NAME = '' # Google API Consoleにて設定したアプリケーション名。自身の環境に合わせて変更してください。
DISCOVERY_URI = ('https://analyticsreporting.googleapis.com/$discovery/rest') # API実行のエンドポイント

# 実行権限取得
def get_credentials():

    home_dir = os.path.expanduser('~')
    credential_dir = os.path.join(home_dir, '.credentials') # 権限設定ファイル(json)の設置ディレクトリ設定
    if not os.path.exists(credential_dir):
        os.makedirs(credential_dir)
    credential_path = os.path.join(credential_dir,'ga.googleapis.com-XXXXXXXXXXXXXXX.json')# 権限設定ファイル(json)のファイル名を指定。自身の環境に合わせて変更してください。

    store = Storage(credential_path)
    credentials = store.get()

    # 権限設定ファイル(json)が無い場合は取得する
    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
        flow.user_agent = APPLICATION_NAME
        if flags:
            credentials = tools.run_flow(flow, store, flags)
        print('Storing credentials to ' + credential_path)
    return credentials

# GAから日次セッションを取得
def get_results(service, profile_id, limit):
    return service.reports().batchGet(
        body={
            'reportRequests': [
            {
            'viewId': profile_id,
            'dateRanges': [{'startDate': '2017-01-01', 'endDate': 'today'}],
            'metrics': [{'expression': 'ga:sessions'}],
            'dimensions': [{'name': 'ga:date'}],
            'pageSize': limit
            }]
        }
     ).execute()

# 日付フォーマットをyyyymmdd -> yyyy/mm/ddに変換
def date_format_yyyymmdd(date_yyyymmdd):
    adt = dt.strptime(date_yyyymmdd, '%Y%m%d')
    newstr = adt.strftime('%Y/%m/%d')
    return newstr

# プログラムの実行
def main():
    credentials = get_credentials()
    http = credentials.authorize(httplib2.Http())
    service = discovery.build('analytics', 'v4', http=http, discoveryServiceUrl=DISCOVERY_URI)
    profile = '' #自身の環境に合わせて変更してください。
    limit = '10000'

    data = get_results(service, profile, limit)
    data_len = len(data['reports'][0]['data']['rows'])

    data_li = []

    for i in range(data_len):
        data_dim = data['reports'][0]['data']['rows'][i]['dimensions'][0]
        data_met = data['reports'][0]['data']['rows'][i]['metrics'][0]['values'][0]

        data_dim = date_format_yyyymmdd(data_dim)

        data_li.append([data_dim,data_met])

    df = pd.DataFrame(data_li,columns=['ds','y'])
    model = Prophet()
    model.fit(df)

    future_data = model.make_future_dataframe(periods=365, freq = 'd')
    forecast_data = model.predict(future_data)

    model.plot(forecast_data)
    model.plot_components(forecast_data)
    plt.show()

# 実行の実態はここ
if __name__ == '__main__':
    main()