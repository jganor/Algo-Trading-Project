# Library imports
import numpy as np
import pandas as pd
import requests
import xlsxwriter
import math
from scipy import stats

# Importing A List of Stocks & API Token
stocks = pd.read_csv(r"C:\Users\jgano\PycharmProjects\pythonProject1\sp_500_stocks.csv")
stocks = stocks[~stocks['Ticker'].isin(['DISCA', 'HFC', 'VIAC', 'WLTW'])]
from secrets import IEX_CLOUD_API_TOKEN

# Making A First API Call
symbol = 'AAPL'
batch_api_call_url = f'https://sandbox.iexapis.com/stable/stock/market/batch/?types=advanced-stats,quote&symbols={symbol}&token={IEX_CLOUD_API_TOKEN}'
data = requests.get(batch_api_call_url).json()

# Executing A Batch API Call & Building Our DataFrame
def chunks(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


symbol_group = list(chunks(stocks['Ticker'], 100))
symbol_strings = []
for i in range(0, len(symbol_group)):
    symbol_strings.append(','.join(symbol_group[i]))

my_columns = [
    'Ticker',
    'Price',
    'Number of Shares to Buy',
    'Price-to-Earnings Ratio',
    'PE Percentile',
    'Price-to-Book Ratio',
    'PB Percentile',
    'Price-to-Sales Ratio',
    'PS Percentile',
    'EV/EBITDA',
    'EV/EBITDA Percentile',
    'EV/GP',
    'EV/GP Percentile',
    'RV Score'
]
final_dataframe = pd.DataFrame(columns=my_columns)

# Price-to-earnings ratio - The stock price divided by the company's earnings per share.
pe_ratio = data[symbol]['quote']['peRatio']

# Price-to-book ratio - Dividing the company's stock price per share by its book value per share.
pb_ratio = data[symbol]['advanced-stats']['priceToBook']

# Price-to-sales ratio- Market capitalization divided by the company's total sales or revenue.
ps_ratio = data[symbol]['advanced-stats']['priceToSales']

# EV/EBITDA - Enterprise Value divided by Earnings Before Interest, Taxes, Depreciation, and Amortization (EV/EBITDA)
enterprise_value = data[symbol]['advanced-stats']['enterpriseValue']
ebitda = data[symbol]['advanced-stats']['EBITDA']
ev_to_ebitda = enterprise_value/ebitda

# EV/GP- Enterprise Value divided by Gross Profit
gross_profit = data[symbol]['advanced-stats']['grossProfit']
ev_to_gross_profit = enterprise_value/gross_profit

for symbol_string in symbol_strings:
    batch_api_call_url = f'https://sandbox.iexapis.com/stable/stock/market/batch?symbols={symbol_string}&types=quote,advanced-stats&token={IEX_CLOUD_API_TOKEN}'
    data = requests.get(batch_api_call_url).json()
    for symbol in symbol_string.split(','):
        enterprise_value = data[symbol]['advanced-stats']['enterpriseValue']
        ebitda = data[symbol]['advanced-stats']['EBITDA']
        gross_profit = data[symbol]['advanced-stats']['grossProfit']
        try:
            ev_to_ebitda = enterprise_value/ebitda
        except TypeError:
            ev_to_ebitda = np.NaN
        try:
            ev_to_gross_profit = enterprise_value/gross_profit
        except TypeError:
            ev_to_gross_profit = np.NaN

        final_dataframe = final_dataframe.append(
            pd.Series([symbol,
                       data[symbol]['quote']['latestPrice'],
                       'N/A',
                       data[symbol]['quote']['peRatio'],
                       'N/A',
                       data[symbol]['advanced-stats']['priceToBook'],
                       'N/A',
                       data[symbol]['advanced-stats']['priceToSales'],
                       'N/A',
                       ev_to_ebitda,
                       'N/A',
                       ev_to_gross_profit,
                       'N/A',
                       'N/A'
                       ],
                      index=my_columns),
            ignore_index=True)

# Taking care of missing data in our data frame
for column in ['Price-to-Earnings Ratio', 'Price-to-Book Ratio', 'Price-to-Sales Ratio', 'EV/EBITDA', 'EV/GP']:
    final_dataframe[column].fillna(final_dataframe[column].mean(), inplace=True)
# Calculating percentiles
metrics = {
            'Price-to-Earnings Ratio': 'PE Percentile',
            'Price-to-Book Ratio': 'PB Percentile',
            'Price-to-Sales Ratio': 'PS Percentile',
            'EV/EBITDA': 'EV/EBITDA Percentile',
            'EV/GP': 'EV/GP Percentile'
}

for row in final_dataframe.index:
    for metric in metrics.keys():
        final_dataframe.loc[row, metrics[metric]] = stats.percentileofscore(final_dataframe[metric], final_dataframe.loc[row, metric])/100

# Calculating Final Score
from statistics import mean
for row in final_dataframe.index:
    value_percentiles = []
    for metric in metrics.keys():
        value_percentiles.append(final_dataframe.loc[row, metrics[metric]])
    final_dataframe.loc[row, 'RV Score'] = mean(value_percentiles)

final_dataframe.sort_values(by='RV Score', ascending=True, inplace=True)
final_dataframe = final_dataframe[:50]
final_dataframe.reset_index(drop=True, inplace=True)

portfolio_size = input('Enter the value of your portfolio: ')
try:
    val = float(portfolio_size)
except ValueError:
    print('That is not an integer!! \n Please try again: ')
    portfolio_size = input('Enter the value of your portfolio: ')
    val = float(portfolio_size)
position_size = val/len(final_dataframe.index)
for i in range(0, len(final_dataframe['Ticker'])):
    final_dataframe.loc[i, 'Number of Shares to Buy'] = math.floor(position_size/final_dataframe['Price'][i])

pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)
print(final_dataframe)
