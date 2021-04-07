# coding=utf8

import csv
import requests
from bs4 import BeautifulSoup
import re
import numpy as np
import pandas as pd
from collections import defaultdict
from datetime import datetime

file_name = 'test.csv'

# 抓取网页
def get_url(url, params=None, proxies=None):
    rsp = requests.get(url, params=params, proxies=proxies)
    rsp.raise_for_status()
    return rsp.text

# 从网页抓取数据
def get_fund_data(code,per=10,sdate='',edate='',proxies=None):
    url = 'http://fund.eastmoney.com/f10/F10DataApi.aspx'
    params = {'type': 'lsjz', 'code': code, 'page':1,'per': per, 'sdate': sdate, 'edate': edate}
    html = get_url(url, params, proxies)
    soup = BeautifulSoup(html, 'html.parser')

    # 获取总页数
    pattern=re.compile(r'pages:(.*),')
    result=re.search(pattern,html).group(1)
    pages=int(result)

    # 获取表头
    heads = []
    for head in soup.findAll("th"):
        heads.append(head.contents[0])

    # 数据存取列表
    records = []

    # 从第1页开始抓取所有页面数据
    page=1
    while page<=pages:
        params = {'type': 'lsjz', 'code': code, 'page':page,'per': per, 'sdate': sdate, 'edate': edate}
        html = get_url(url, params, proxies)
        soup = BeautifulSoup(html, 'html.parser')

        # 获取数据
        for row in soup.findAll("tbody")[0].findAll("tr"):
            row_records = []
            for record in row.findAll('td'):
                val = record.contents

                # 处理空值
                if val == []:
                    row_records.append(np.nan)
                else:
                    row_records.append(val[0])

            # 记录数据
            records.append(row_records)

        # 下一页
        page=page+1

    # 数据整理到dataframe
    np_records = np.array(records)
    data= pd.DataFrame()
    for col,col_name in enumerate(heads):
        data[col_name] = np_records[:,col]

    return data


# 平均成本法返回收益，收益波动范围+3% ~ -3%，两位小数正常取整
ratio = 0.03
low_ratio, high_ratio = 1-ratio, 1+ratio
def method_1(data):
    buy, avg_cost = [data[0]], data[0]
    # 下一次买入和卖出的价格
    next_buy, next_sell = round(avg_cost * low_ratio, 2), round(avg_cost * high_ratio, 2)

    earning = 0.0
    costs = []
    buy_count = sell_count = 0
    # 交易模拟
    for i in range(1, len(data)):
        if data[i] <= next_buy:     # 如果当天价格符合买入条件
            buy.append(data[i])
            buy = sorted(buy)
            buy_count += 1          # 买入次数+1
        elif data[i] >= next_sell:  # 如果当天价格符合卖出条件
            # 卖出所有符合卖出条件的份额
            while buy and round(buy[0] * high_ratio, 2) <= next_sell:
                earning += (data[i] - buy[0]) * 100
                buy.pop(0)
            # 保留底仓，最后一份卖出后计入收益，同时按照原价买入
            # 等价于：不卖出，但是计算收益，更新下次买入和卖出价格
            if len(buy) == 0: buy.append(data[i])
            sell_count += 1         # 卖出次数+1
        costs.append(sum(buy))      # 当前交易日的持仓金额
        avg_cost = sum(buy) / len(buy)
        # avg_cost变化后即更新下次的买入和卖出价格
        next_buy, next_sell = round(avg_cost * low_ratio, 2), round(avg_cost * high_ratio, 2)

    # print(sorted(costs), sum(costs)//len(costs), buy)
    # print('历史全部套牢金额：%s' % [round(v * 100, 1) for v in sorted(list(set(costs))) if v > 0])
    avg_price = sum(costs)/len(costs)
    end_total_cost = int(sum(buy) * 100)
    end_total_market = int(data[-1] * len(buy) * 100)
    # 如果期末卖出持有的份额的总盈利
    end_total_earnings = end_total_market + earning - end_total_cost
    # 如果期末不卖出，只计算拿到手的盈利
    # print('\033[1m平均套牢金额持仓收益率：%.2f%%\033[0m' % (end_total_earnings / avg_price))
    return end_total_earnings / avg_price


"""
军工ETF: 512810
银行ETF: 512800
白酒ETF: 512690
上证红利ETF: 510880
地产ETF: 512200
H股ETF: 510900
恒生ETF: 159920
"""

# 主程序
ETFs = {
    '512800': '银行ETF',
    '510880': '上证红利ETF',
    '512200': '地产ETF',
    '159920': '恒生ETF',
    '501301': '香港大盘',
    '510900': 'H股ETF',
}
dates_6 = [
        ('2017-10-01', '2018-04-01'), ('2018-01-01', '2018-07-01'), ('2018-04-01', '2018-10-01'), ('2018-07-01', '2019-01-01'),
        ('2018-10-01', '2019-04-01'), ('2019-01-01', '2019-07-01'), ('2019-04-01', '2019-10-01'), ('2019-07-01', '2020-01-01'),
        ('2019-10-01', '2020-04-01'), ('2020-01-01', '2020-07-01'), ('2020-04-01', '2020-10-01'), ('2020-07-01', '2021-01-01'),
        ('2020-10-01', '2021-04-01'),
        ]
dates_12 = [('2017-10-01', '2018-10-01'), ('2018-04-01', '2019-04-01'), ('2018-10-01', '2019-10-01'), ('2019-04-01', '2020-04-01'), ('2019-10-01', '2020-10-01'), ('2020-04-01', '2021-04-01'),]
if __name__ == "__main__":
    etf_data_dic = {}
    for etf_code in ETFs:
        data = get_fund_data(etf_code, per=49, sdate='2017-10-01', edate='2021-04-01')
        # 修改数据类型
        data['净值日期']=pd.to_datetime(data['净值日期'],format='%Y/%m/%d')
        data['单位净值']= data['单位净值'].astype(float)
        data['累计净值']=data['累计净值'].astype(float)
        data['日增长率']=data['日增长率'].str.strip('%').astype(float)
        # 按照日期升序排序并重建索引
        data=data.sort_values(by='净值日期',axis=0,ascending=True).reset_index(drop=True)

        etf_data_dic[etf_code] = data[['净值日期', '单位净值']]
        
    print('获取数据完毕，开始进行数据分析...')
    print('投资年限为六个月：')
    results = defaultdict(list)
    for etf_code in ETFs:
        df = etf_data_dic[etf_code]
        for date in dates_6:
            curr_data = df.loc[(df['净值日期'] >= datetime.strptime(date[0], "%Y-%m-%d"))&(df['净值日期'] < datetime.strptime(date[1], "%Y-%m-%d"))]['单位净值'].tolist()
            rate_of_return = method_1(curr_data)
            results[ETFs[etf_code]].append(round(rate_of_return, 2))

    for key, value in sorted(results.items(), key=lambda x: x[0]):
        print("%s,%s" % (key, ','.join([str(v) for v in value])))

    print('投资年限为一年：')
    results = defaultdict(list)
    for etf_code in ETFs:
        df = etf_data_dic[etf_code]
        for date in dates_12:
            curr_data = df.loc[(df['净值日期'] >= datetime.strptime(date[0], "%Y-%m-%d"))&(df['净值日期'] < datetime.strptime(date[1], "%Y-%m-%d"))]['单位净值'].tolist()
            rate_of_return = method_1(curr_data)
            results[ETFs[etf_code]].append(round(rate_of_return, 2))

    for key, value in sorted(results.items(), key=lambda x: x[0]):
        print("%s,%s" % (key, ','.join([str(v) for v in value])))


"""
获取数据完毕，开始进行数据分析...
投资年限为六个月：
H股ETF,-0.96,-3.35,17.77,16.23,23.02,16.06,10.68,14.92,6.19,12.52,-17.73,10.68,16.73
上证红利ETF,-6.13,-13.14,13.9,4.94,17.4,9.48,8.08,11.24,-14.18,-0.49,8.99,9.46,14.47
地产ETF,0.47,-33.08,-7.87,16.94,33.99,1.52,1.03,14.14,17.22,15.01,9.44,-10.52,13.88
恒生ETF,0.48,8.47,6.36,6.61,21.63,20.0,12.42,18.64,-7.41,6.76,-13.38,10.45,17.55
银行ETF,-14.02,-24.32,19.15,2.88,21.47,22.84,8.7,9.88,-9.29,-0.93,9.43,22.0,31.46
香港大盘,6.52,9.23,13.31,13.56,20.91,17.85,12.4,17.43,1.3,4.74,-19.57,14.6,16.42
投资年限为一年：
H股ETF,14.56,33.76,33.91,19.24,6.74,28.61
上证红利ETF,8.49,20.22,22.38,-5.7,19.0,32.04
地产ETF,-29.22,31.1,9.7,9.21,39.32,-5.57
恒生ETF,7.17,24.43,33.4,16.16,1.22,24.65
银行ETF,12.98,39.83,27.9,1.25,22.48,51.51
香港大盘,22.73,32.63,32.48,21.56,0.04,30.85
"""







