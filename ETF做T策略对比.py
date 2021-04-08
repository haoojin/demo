# coding=utf8
import csv
import requests
from bs4 import BeautifulSoup
import re
import numpy as np
import pandas as pd
from collections import defaultdict
from datetime import datetime

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
为了提升资金利用率，分别选择不同市场中的ETF(跌涨不同时，资金互补)
两个美国的(五星+：纳斯达克、标普500)、
两个香港的(五星：恒生、H股)、
三四个中国的(四星-：银行、上证红利、地产、白酒)
"""

# 主程序
ETFs = {
    '513500': '标普500ETF',
    '160213': '纳斯达克ETF',
    '159920': '恒生ETF',
    '510900': 'H股ETF',
    '512800': '银行ETF',
    '510880': '红利ETF',  # 上证红利
    '512200': '地产ETF',
}
dates_6 = [
        ('2017-10-01', '2018-04-01'), ('2018-01-01', '2018-07-01'), ('2018-04-01', '2018-10-01'), ('2018-07-01', '2019-01-01'),
        ('2018-10-01', '2019-04-01'), ('2019-01-01', '2019-07-01'), ('2019-04-01', '2019-10-01'), ('2019-07-01', '2020-01-01'),
        ('2019-10-01', '2020-04-01'), ('2020-01-01', '2020-07-01'), ('2020-04-01', '2020-10-01'), ('2020-07-01', '2021-01-01'),
        ('2020-10-01', '2021-04-01'),
        ]
dates_12 = [('2017-10-01', '2018-10-01'), ('2018-04-01', '2019-04-01'), ('2018-10-01', '2019-10-01'), ('2019-04-01', '2020-04-01'), ('2019-10-01', '2020-10-01'), ('2020-04-01', '2021-04-01'),]

"""__main__() function:"""
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
    print("%s\t\t[%s], 平均值:%.2f%%" % (key, ','.join([str(v) for v in value]), sum(value)/len(value)))

print('投资年限为一年：')
results = defaultdict(list)
for etf_code in ETFs:
    df = etf_data_dic[etf_code]
    for date in dates_12:
        curr_data = df.loc[(df['净值日期'] >= datetime.strptime(date[0], "%Y-%m-%d"))&(df['净值日期'] < datetime.strptime(date[1], "%Y-%m-%d"))]['单位净值'].tolist()
        rate_of_return = method_1(curr_data)
        results[ETFs[etf_code]].append(round(rate_of_return, 2))

for key, value in sorted(results.items(), key=lambda x: x[0]):
    print("%s\t\t[%s], 平均值:%.2f%%" % (key, ','.join([str(v) for v in value]), sum(value)/len(value)))









