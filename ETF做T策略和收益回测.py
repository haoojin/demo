# coding=utf8

import csv
import requests
from bs4 import BeautifulSoup
import re
import numpy as np
import pandas as pd

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


def load_data():
    data = []

    with open("test.csv") as f:
        reader = csv.reader(f)
        for ix, line in enumerate(reader):
            if ix == 0: continue
            data.append(eval(line[2]))
    # 净值列表：[1.2, 1.3, 1.1, ...]
    return data


# 平均成本法返回收益，收益波动范围+3% ~ -3%，两位小数正常取整
low_ratio, high_ratio = 0.97, 1.03
def way_1(data):
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
    print('平均套牢金额：%.2f' % (avg_price * 100))
    print('\033[1m最大套牢金额：%d, 大于平均套牢金额的资金占有天数比例：%.2f%%\033[0m' % (max(costs) * 100, 100 * sum([1 if cost > avg_price else 0 for cost in costs])/len(costs)))
    end_total_cost = int(sum(buy) * 100)
    end_total_market = int(data[-1] * len(buy) * 100)
    print('\033[1m期末持仓成本：%d\033[0m' % end_total_cost)
    print('期末持仓市值：%d' % end_total_market)
    # 如果期末卖出持有的份额的总盈利
    end_total_earnings = end_total_market + earning - end_total_cost
    print('\033[1m期末清仓收益率：%.2f%%\033[0m' % round(100 * end_total_earnings / end_total_cost, 2))
    # 如果期末不卖出，只计算拿到手的盈利
    print('期末持仓收益率：%.2f%%' % round(earning * 100 / end_total_cost, 2))
    print('\033[1m平均套牢金额持仓收益率：%.2f%%\033[0m' % (end_total_earnings / avg_price))
    print('\033[1m最大套牢金额持仓收益率：%.2f%%\033[0m' % (end_total_earnings / max(costs)))
    print('平均交易次数：%.2f，交易总天数%d，其中买%d次，卖%d次' % (round((buy_count + sell_count) / len(data), 2), len(data), buy_count, sell_count))

    return end_total_earnings


# 以单日最大涨跌幅衡量
def way_2(data):
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
        next_buy, next_sell = round(buy[0] * low_ratio, 2), round(buy[0] * high_ratio, 2)

    # print(sorted(costs), sum(costs)//len(costs), buy)
    # print('历史全部套牢金额：%s' % [round(v * 100, 1) for v in sorted(list(set(costs))) if v > 0])
    avg_price = sum(costs)/len(costs)
    print('平均套牢金额：%.2f' % (avg_price * 100))
    print('\033[1m最大套牢金额：%d, 大于平均套牢金额的资金占有天数比例：%.2f%%\033[0m' % (max(costs) * 100, 100 * sum([1 if cost > avg_price else 0 for cost in costs])/len(costs)))
    end_total_cost = int(sum(buy) * 100)
    end_total_market = int(data[-1] * len(buy) * 100)
    print('\033[1m期末持仓成本：%d\033[0m' % end_total_cost)
    print('期末持仓市值：%d' % end_total_market)
    # 如果期末卖出持有的份额的总盈利
    end_total_earnings = end_total_market + earning - end_total_cost
    print('\033[1m期末清仓收益率：%.2f%%\033[0m' % round(100 * end_total_earnings / end_total_cost, 2))
    # 如果期末不卖出，只计算拿到手的盈利
    print('期末持仓收益率：%.2f%%' % round(earning * 100 / end_total_cost, 2))
    print('\033[1m平均套牢金额持仓收益率：%.2f%%\033[0m' % (end_total_earnings / avg_price))
    print('\033[1m最大套牢金额持仓收益率：%.2f%%\033[0m' % (end_total_earnings / max(costs)))
    print('平均交易次数：%.2f，交易总天数%d，其中买%d次，卖%d次' % (round((buy_count + sell_count) / len(data), 2), len(data), buy_count, sell_count))

    return earning


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
if __name__ == "__main__":
    data=get_fund_data('512690', per=49, sdate='2020-01-01', edate='2020-04-01')
    # 修改数据类型
    data['净值日期']=pd.to_datetime(data['净值日期'],format='%Y/%m/%d')
    data['单位净值']= data['单位净值'].astype(float)
    data['累计净值']=data['累计净值'].astype(float)
    data['日增长率']=data['日增长率'].str.strip('%').astype(float)
    # 按照日期升序排序并重建索引
    data=data.sort_values(by='净值日期',axis=0,ascending=True).reset_index(drop=True)
    data.to_csv("test.csv")
    data = load_data()
    earnings = way_1(data)
    print('收益：', round(earnings, 2))
