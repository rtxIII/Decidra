import csv
import json
import os
import re

from datetime import datetime, timedelta
from multiprocessing import Pool, cpu_count

import humanize
import openpyxl
import pandas as pd
import requests
import tushare as ts
import yahooquery
import yfinance as yf
from deprecated import deprecated
from tqdm import tqdm

from utils import logger
from utils.global_vars import *



class DataProcessingInterface:
    default_logger = logger.get_logger("data_processing")

    @staticmethod
    def validate_dir(dir_path: Path):
        dir_path.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def get_1M_data_range(date_range: list, stock_list: list) -> dict:
        """
            Get 1M Data from CSV based on Stock List. Returned in Dict format
        :param date_range: A list of Date in DateTime Format (YYYY-MM-DD)
        :param stock_list: A List of Stock Code with Format (e.g., [HK.00001, HK.00002])
        :return: Dictionary in Format {'HK.00001': pd.Dataframe, 'HK.00002': pd.Dataframe}
        """
        output_dict = {}
        for stock_code in stock_list:
            # input_df refers to the all the 1M data from start_date to end_date in pd.Dataframe format
            input_df = pd.concat(
                [DataProcessingInterface.get_stock_df_from_file(
                    PATH_DATA / stock_code / f'{stock_code}_{input_date}_1M.parquet')
                    for input_date in date_range if
                    (PATH_DATA / stock_code / f'{stock_code}_{input_date}_1M.parquet').is_file()],
                ignore_index=True)
            input_df[['open', 'close', 'high', 'low']] = input_df[['open', 'close', 'high', 'low']].apply(pd.to_numeric)
            input_df.sort_values(by='time_key', ascending=True, inplace=True)
            output_dict[stock_code] = output_dict.get(stock_code, input_df)
        return output_dict

    @staticmethod
    def get_custom_interval_data(target_date: datetime, custom_interval: int, stock_list: list) -> dict:
        """
            Get 5M/15M/Other Customized-Interval Data from CSV based on Stock List. Returned in Dict format
            Supported Interval: 3M, 5M, 15M, 30M
            Not-Supported Interval: 60M
        :param target_date: Date in DateTime Format (YYYY-MM-DD)
        :param custom_interval: Customized-Interval in unit of "Minutes"
        :param stock_list: A List of Stock Code with Format (e.g., [HK.00001, HK.00002])
        :return: Dictionary in Format {'HK.00001': pd.Dataframe, 'HK.00002': pd.Dataframe}
        """

        input_data = {}
        target_date = target_date.strftime('%Y-%m-%d')
        for stock_code in stock_list:
            input_path = PATH_DATA / stock_code / f'{stock_code}_{target_date}_1M.parquet'

            if not Path(input_path).is_file():
                continue

            input_df = DataProcessingInterface.get_stock_df_from_file(input_path)
            # Non-Trading Day -> Skip
            if input_df.empty:
                continue
            # Set Time-key as Index & Convert to Datetime
            input_df = input_df.set_index('time_key')
            input_df.index = pd.to_datetime(input_df.index, infer_datetime_format=True)
            # Define Function List
            agg_list = {
                "code":          "first",
                "open":          "first",
                "close":         "last",
                "high":          "max",
                "low":           "min",
                "pe_ratio":      "last",
                "turnover_rate": "sum",
                "volume":        "sum",
                "turnover":      "sum",
            }
            # Group from 09:31:00 with Freq = 5 Min
            minute_df = input_df.groupby(
                pd.Grouper(freq=f'{custom_interval}min', closed='left', offset='1min', origin='start')
            ).agg(agg_list)[1:]
            # For 1min -> 5min, need to add Timedelta of 4min
            minute_df.index = minute_df.index + pd.Timedelta(minutes=int(custom_interval - 1))
            # Drop Lunch Time
            minute_df.dropna(inplace=True)

            # Update First Row (Special Cases) e.g. For 1min -> 5min, need to use the first 6min Rows of data
            minute_df.iloc[0] = \
                input_df.iloc[:(custom_interval + 1)].groupby('code').agg(agg_list).iloc[0]

            # Update Last Close Price
            last_index = minute_df.index[0]
            minute_df['change_rate'] = 0
            minute_df['last_close'] = input_df['last_close'][0]
            minute_df.loc[last_index, 'change_rate'] = 100 * (float(minute_df.loc[last_index, 'close']) - float(
                minute_df.loc[last_index, 'last_close'])) / float(minute_df.loc[last_index, 'last_close'])

            # Change Rate = (Close Price - Last Close Price) / Last Close Price * 100
            # Last Close = Previous Close Price
            for index, row in minute_df[1:].iterrows():
                minute_df.loc[index, 'last_close'] = minute_df.loc[last_index, 'close']
                minute_df.loc[index, 'change_rate'] = 100 * (
                        float(row['close']) - float(minute_df.loc[last_index, 'close'])) / float(
                    minute_df.loc[last_index, 'close'])
                last_index = index

            minute_df.reset_index(inplace=True)
            column_names = json.loads(config.get('FutuOpenD.DataFormat', 'HistoryDataFormat'))
            minute_df = minute_df.reindex(columns=column_names)

            # Convert Timestamp type column to standard String format
            minute_df['time_key'] = minute_df['time_key'].dt.strftime('%Y-%m-%d %H:%M:%S')
            input_data[stock_code] = input_data.get(stock_code, minute_df)
        return input_data

    @staticmethod
    def convert_day_interval_to_weekly(input_df: pd.DataFrame):
        """
        For Yahoo Finance format, Index(['Open', 'High', 'Low', 'Close', 'Volume', 'Dividends', 'Stock Splits'], dtype='object')
        Convert from Day-level K-line to Weekly-level K-Line for Stock Filter. Inplace change
        :param input_df: Dataframe extracted from yFinance lib
        """
        logic = {'open':   'first',
                 'high':   'max',
                 'low':    'min',
                 'close':  'last',
                 'volume': 'sum'}
        input_df.columns = [item.lower().strip() for item in input_df]

        input_df.index = pd.to_datetime(input_df.index)
        input_df = input_df.resample('W').apply(logic)
        input_df.index = input_df.index - pd.tseries.frequencies.to_offset("6D")

    @staticmethod
    def validate_1M_data(date_range: list, stock_list: list, trading_days: dict):
        raise NotImplementedError
        # TODO: Validate data against futu records

    @staticmethod
    def save_stock_df_to_file(data: pd.DataFrame, output_path: str, file_type='parquet') -> bool:
        """
        Save Data to File (CSV / Feather)
        :param data: Data to Save
        :param output_path: File Name to Save
        :param file_type: File Type to Save (CSV / Feather / Parquet)
        :return: None
        """
        if not data.empty:
            if file_type == 'csv':
                data.to_csv(output_path, index=False, encoding='utf-8-sig')
            elif file_type == 'parquet':
                try:
                    data.to_parquet(output_path, index=False)
                except OverflowError as e:
                    DataProcessingInterface.default_logger.error(f"OverflowError when saving to parquet {output_path}: {e}")
                    return False
                except Exception as e:
                    DataProcessingInterface.default_logger.error(f"Error saving to parquet {output_path}: {e}")
                    return False
            return True
        return False

    @staticmethod
    def get_stock_df_from_file(input_path: Path) -> pd.DataFrame:
        """
        Load Data from File (CSV / Feather / Parquet)
        :param input_path: File Name to Load
        :return: DataFrame
        """
        data = pd.DataFrame(columns=json.loads(config.get('FutuOpenD.DataFormat', 'HistoryDataFormat')))
        
        if not input_path.exists():
            DataProcessingInterface.default_logger.warning(f"File does not exist: {input_path}")
            return data
            
        try:
            if input_path.suffix == '.csv':
                data = pd.read_csv(input_path, index_col=None, encoding='utf-8-sig')
            elif input_path.suffix == '.parquet':
                data = pd.read_parquet(input_path)
            else:
                DataProcessingInterface.default_logger.warning(f"Unsupported file format: {input_path.suffix}")
        except Exception as e:
            DataProcessingInterface.default_logger.error(f"Error reading file {input_path}: {e}")
            
        return data

    @staticmethod
    def check_empty_data(input_path: Path) -> bool:
        """
        Check if the input file is empty
        :param input_path:
        :return:
        """
        input_df = DataProcessingInterface.get_stock_df_from_file(input_path)
        if input_df.empty:
            input_path.unlink()
            DataProcessingInterface.default_logger.info(f'{input_path} removed.')
            return True
        return False

    @staticmethod
    def clear_empty_data():
        pool = Pool(cpu_count())
        pool.map(DataProcessingInterface.check_empty_data, PATH_DATA.rglob("*/*_1[DWM].parquet"))
        pool.close()
        pool.join()

    @staticmethod
    def convert_csv_to_parquet(input_file: Path) -> bool:
        """
        Convert CSV file to Parquet file
        :param input_file: File to Convert
        :return: bool
        """
        if input_file.suffix == '.csv':
            output_file = input_file.as_posix().replace('.csv', '.parquet')
            output_file = Path(output_file)
            # Temporary
            output_file.parent.mkdir(parents=True, exist_ok=True)
            DataProcessingInterface.default_logger.info(f'Converting {input_file} to {output_file}')
            df = pd.read_csv(input_file, index_col=None)
            df.to_parquet(output_file, index=False)
            return True
        return False

    @staticmethod
    def convert_parquet_to_csv(input_file: Path) -> bool:
        """
        Convert Parquet file to CSV file
        :param input_file: File to Convert
        :return: bool
        """
        if input_file.suffix == '.parquet':
            output_file = input_file.as_posix().replace('.parquet', '.csv')
            DataProcessingInterface.default_logger.info(f'Converting {input_file} to {output_file}')
            df = pd.read_parquet(input_file)
            df.to_csv(output_file, index=False)
            return True
        return False

    @staticmethod
    def convert_all_csv_to_parquet():
        pool = Pool(cpu_count())
        pool.map(DataProcessingInterface.convert_csv_to_parquet, PATH_DATA.rglob("*/*_1[DWM].csv"))
        pool.close()
        pool.join()

    @staticmethod
    def get_num_days_to_update(stock_code) -> int:
        try:
            return (datetime.now() - datetime.fromtimestamp(
                Path(max((PATH_DATA / stock_code).glob('*.parquet'), key=os.path.getctime)).stat().st_mtime)).days
        # Will throw ValueError if the Path is not found
        except ValueError:
            return 365 * 2

    @staticmethod
    def get_file_to_df(input_file: Path) -> pd.DataFrame:
        if input_file.suffix == '.parquet':
            DataProcessingInterface.default_logger.info(f'Loading {input_file}...')
            return pd.read_parquet(input_file)
        return pd.DataFrame()


class TuShareInterface:
    output_df = pd.DataFrame()
    pro = ts.pro_api(config.get('TuShare.Credential', 'token'))
    default_logger = logger.get_logger("tushare_interface")

    @staticmethod
    def __validate_stock_code(stock_list: list) -> list:
        """
            Check stock code format, and always return TuShare Stock Code format
            Use Internally
        :param stock_list: Either in Futu Format (Starts with HK/US) / Yahoo Finance Format (Starts with Number)
        :return: Stock code list in Yahoo Finance format
        """
        return [YahooFinanceInterface.futu_code_to_yfinance_code(stock_code) if stock_code[:1].isalpha() else stock_code
                for stock_code in stock_list]

    @staticmethod
    def update_stocks_history(stock_list: list) -> bool:
        stock_list = TuShareInterface.__validate_stock_code(stock_list)
        # Rate Limit = 6000 data per request
        interval = int(6000 / 300)
        stock_lists = [stock_list[i:i + interval] for i in range(0, len(stock_list), interval)]
        start_date = str((datetime.today() - timedelta(days=round(365 * 1))).date())
        end_date = str(datetime.today().date().strftime("%Y%m%d"))
        super_x = [TuShareInterface.output_df]
        for stock_list in tqdm(stock_lists):
            super_x.append(
                TuShareInterface.pro.daily(ts_code=','.join(stock_list), start_date=start_date, end_date=end_date))
        TuShareInterface.output_df = pd.concat(super_x, ignore_index=True)
        TuShareInterface.output_df.sort_values(by=['ts_code', 'trade_date'], ascending=[True, True], inplace=True)
        TuShareInterface.output_df = TuShareInterface.output_df.rename(
            columns={"ts_code": "code", "trade_date": "time_key", "vol": "volume"})
        return True

    @staticmethod
    def get_stock_history(stock_code: str) -> pd.DataFrame:
        stock_code = TuShareInterface.__validate_stock_code([stock_code])[0]
        return TuShareInterface.output_df[TuShareInterface.output_df['code'] == stock_code].reset_index(drop=True)

    @staticmethod
    def get_stocks_email(stock_list: list) -> dict:
        stock_list = TuShareInterface.__validate_stock_code(stock_list)
        output_dict = {}
        
        try:
            input_df = TuShareInterface.pro.stock_basic(ts_code=','.join(stock_list), exchange='', list_status='L',
                                                        fields='ts_code,symbol,name,area,industry,market,list_date,enname,fullname,curr_type')
        except Exception as e:
            TuShareInterface.default_logger.error(f"Failed to get stock basic info: {e}")
            return output_dict
            
        for stock_code in stock_list:
            try:
                stock_info = input_df[input_df['ts_code'] == stock_code].reset_index(drop=True)
                if stock_info.empty:
                    TuShareInterface.default_logger.warning(f"No stock info found for {stock_code}")
                    continue
                    
                stock_price = TuShareInterface.get_stock_history(stock_code).tail(1).reset_index(drop=True)
                if stock_price.empty:
                    TuShareInterface.default_logger.warning(f"No price data found for {stock_code}")
                    continue
                
                output_dict[stock_code] = {
                    'Company Name': f"{stock_info.get('name', ['N/A'])[0]} ({stock_info.get('market', ['N/A'])[0]}) {stock_info.get('enname', ['N/A'])[0]}",
                    'Description':  f"{stock_info.get('area', ['N/A'])[0]} {stock_info.get('industry', ['N/A'])[0]}",
                    'Last Close':   f"{stock_info.get('curr_type', ['N/A'])[0]} {stock_price.get('pre_close', ['N/A'])[0]}",
                    'Open':         f"{stock_info.get('curr_type', ['N/A'])[0]} {stock_price.get('open', ['N/A'])[0]}",
                    'Close':        f"{stock_info.get('curr_type', ['N/A'])[0]} {stock_price.get('close', ['N/A'])[0]}",
                    '% Change':     f"{stock_price.get('pct_chg', ['N/A'])[0]}%",
                    'Volume':       f"{stock_info.get('curr_type', ['N/A'])[0]} {humanize.intword(stock_price.get('volume', [0])[0])}",
                    'Amount':       f"{stock_info.get('curr_type', ['N/A'])[0]} {humanize.intword(stock_price.get('amount', [0])[0])}"
                }
            except Exception as e:
                TuShareInterface.default_logger.error(f"Error processing stock {stock_code}: {e}")
                continue
                
        return output_dict


class YahooFinanceInterface:
    default_logger = logger.get_logger("yahoo_finance_interface")

    @staticmethod
    def __validate_stock_code(stock_list: list) -> list:
        """
            Check stock code format, and always return Yahoo Finance Stock Code format
            Use Internally
        :param stock_list: Either in Futu Format (Starts with HK/US) / Yahoo Finance Format (Starts with Number)
        :return: Stock code list in Yahoo Finance format
        """
        return [YahooFinanceInterface.futu_code_to_yfinance_code(stock_code) if stock_code[:1].isalpha() else stock_code
                for stock_code in stock_list]

    @staticmethod
    def get_top_30_hsi_constituents() -> list:
        r = requests.get('https://finance.yahoo.com/quote/%5EHSI/components/', headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'})
        payload = pd.read_html(r.text)[0]
        return [YahooFinanceInterface.yfinance_code_to_futu_code(stock_code) for stock_code in
                payload['Symbol'].tolist()]

    @staticmethod
    def futu_code_to_yfinance_code(futu_code: str) -> str:
        """
            Convert Futu Stock Code to Yahoo Finance Stock Code format
            E.g., HK.09988 -> 9988.HK; US.SOHO -> SOHO
        :param futu_code: Stock code used in Futu (e.g., HK.09988)
        """
        if futu_code.startswith("HK"):
            assert re.match(r'^[A-Z]{2}.\d{5}$', futu_code)
            return '.'.join(reversed(futu_code.split('.')))[1:]
        elif futu_code.startswith('US'):
            return futu_code.replace('US.', '')
        else:
            assert re.match(r'^[A-Z]{2}.\d{6}$', futu_code)
            return '.'.join(reversed(futu_code.split('.')))

    @staticmethod
    def yfinance_code_to_futu_code(yfinance_code: str) -> str:
        """
            Convert Yahoo Finance Stock Code to Futu Stock Code format
            E.g., 9988.HK -> HK.09988
        :param yfinance_code: Stock code used in Yahoo Finance (e.g., 9988.HK)
        """
        assert re.match(r'^\d{4}.[A-Z]{2}$', yfinance_code)
        if 'HK' in yfinance_code:
            return '.'.join(reversed(('0' + yfinance_code).split('.')))
        else:
            return '.'.join(reversed((yfinance_code).split('.')))

    @staticmethod
    def get_stocks_info(stock_list: list) -> dict:
        stock_list = YahooFinanceInterface.__validate_stock_code(stock_list)
        return {stock_code: yf.Ticker(stock_code).info for stock_code in stock_list}

    @staticmethod
    def get_stock_info(stock_code: str) -> dict:
        try:
            stock_code = YahooFinanceInterface.__validate_stock_code([stock_code])[0]
            return yf.Ticker(stock_code).info
        except Exception as e:
            YahooFinanceInterface.default_logger.error(f"Failed to get stock info for {stock_code}: {e}")
            return {}

    @staticmethod
    def get_stocks_name(stock_list: list) -> dict:
        stock_list = YahooFinanceInterface.__validate_stock_code(stock_list)
        return {stock_code: yf.Ticker(stock_code).info['longName'] for stock_code in stock_list}

    @staticmethod
    def get_stocks_email(stock_list: list) -> dict:
        stock_list = YahooFinanceInterface.__validate_stock_code(stock_list)
        output_dict = {}
        for stock_code in stock_list:
            try:
                # stock_ticker = yf.Ticker(stock_code)
                stock_ticker = yahooquery.Ticker(stock_code)
                
                # Check if data is valid
                if stock_code not in stock_ticker.price or stock_ticker.price[stock_code] is None:
                    continue
                    
                price_data = stock_ticker.price.get(stock_code, {})
                summary_data = stock_ticker.summary_detail.get(stock_code, {})
                profile_data = stock_ticker.asset_profile.get(stock_code, {})
                
                output_dict[stock_code] = {
                    'Company Name':         f"{price_data.get('shortName', 'N/A')} {price_data.get('longName', '')}",
                    'Sector':               profile_data.get('sector', 'N/A'),
                    'Last Close':           f"{summary_data.get('currency', 'N/A')} {summary_data.get('previousClose', 0):.3f}",
                    'Open':                 f"{summary_data.get('currency', 'N/A')} {price_data.get('regularMarketDayHigh', 0):.3f}",
                    'Close':                f"{summary_data.get('currency', 'N/A')} {price_data.get('regularMarketPrice', 0):.3f}",
                    '% Change':             f"{float(price_data.get('regularMarketChangePercent', 0))*100:.2f}%",
                    'Volume':               f"{summary_data.get('currency', 'N/A')} {humanize.intword(summary_data.get('volume', 'N/A'))}",
                    '52 Week Range':        f"{summary_data.get('currency', 'N/A')} {summary_data.get('fiftyTwoWeekLow', 'N/A')}-{summary_data.get('fiftyTwoWeekHigh', 'N/A')}",
                    'PE(Trailing/Forward)': f"{summary_data.get('trailingPE', 'N/A')} / {summary_data.get('forwardPE', 'N/A')}",
                }
            except Exception as e:
                YahooFinanceInterface.default_logger.error(f"Error processing stock {stock_code}: {e}")
                continue

        return output_dict

    @staticmethod
    def get_stocks_history(stock_list: list) -> pd.DataFrame:
        stock_list = YahooFinanceInterface.__validate_stock_code(stock_list)
        return yf.download(stock_list, group_by="ticker", auto_adjust=True, actions=True, progress=True)

    @staticmethod
    def get_stock_history(stock_code: str, period: str = "1y") -> pd.DataFrame:
        stock_code = YahooFinanceInterface.__validate_stock_code([stock_code])[0]
        # return yf.download(stock_code, auto_adjust=True, actions=True, progress=False, period="1y")
        return yf.Ticker(stock_code).history(period=period)

    @staticmethod
    def parse_stock_info(stock_code: str):
        return stock_code, YahooFinanceInterface.get_stock_info(stock_code)


class HKEXInterface:

    @staticmethod
    def update_security_list_full() -> None:
        """
            Get Full Security List from HKEX. Can Daily Update (Override)
            URL: https://www.hkex.com.hk/eng/services/trading/securities/securitieslists/ListOfSecurities.xlsx
        """
        full_stock_list = "https://www.hkex.com.hk/eng/services/trading/securities/securitieslists/ListOfSecurities.xlsx"
        resp = requests.get(full_stock_list)
        with open(PATH_DATA / 'Stocks' / 'ListOfSecurities.xlsx', 'wb') as fp:
            fp.write(resp.content)

        wb = openpyxl.load_workbook(PATH_DATA / 'Stocks' / 'ListOfSecurities.xlsx')
        sh = wb.active
        with open(PATH_DATA / 'Stocks' / 'ListOfSecurities.csv', 'w', newline="") as f:
            c = csv.writer(f)
            for r in sh.rows:
                c.writerow([cell.value for cell in r])

    @staticmethod
    def get_security_df_full() -> pd.DataFrame:
        csv_path = PATH_DATA / 'Stocks' / 'ListOfSecurities.csv'
        
        if not csv_path.exists():
            # 如果文件不存在，返回空的DataFrame
            return pd.DataFrame(columns=['Stock Code', 'Name of Securities', 'Category', 'Board Lot'])
            
        try:
            input_csv = pd.read_csv(csv_path, index_col=None, skiprows=2, dtype={'Stock Code': str})
            input_csv.dropna(subset=['Stock Code'], inplace=True)
            input_csv.drop(input_csv.columns[-1], axis=1, inplace=True)
            input_csv.set_index('Stock Code')
            return input_csv
        except Exception as e:
            # 如果读取失败，返回空的DataFrame
            return pd.DataFrame(columns=['Stock Code', 'Name of Securities', 'Category', 'Board Lot'])

    @staticmethod
    def get_equity_list_full() -> list:
        """
            Return Full List of Equity in FuTu Stock Code Format E.g. HK.00001
        :return:
        """
        input_csv = HKEXInterface.get_security_df_full()
        return [('HK.' + item) for item in input_csv[input_csv['Category'] == 'Equity']['Stock Code'].tolist()]

    @staticmethod
    def get_equity_info_full() -> list:
        """
            Return Full List of Equity dict in Futu Stock Code Format including Basic Info
            E.g., {"Stock Code": HK.00001, "Name of Securities": "CKH HOLDINGS", "Board Lot": 500}
        """
        input_csv = HKEXInterface.get_security_df_full()
        return [{"Stock Code": f'HK.{row["Stock Code"]}', "Name of Securities": row["Name of Securities"],
                 "Board Lot":  row["Board Lot"]} for index, row in
                input_csv[input_csv['Category'] == 'Equity'].iterrows()]

    @staticmethod
    def get_board_lot_full() -> dict:
        """
            Return Full Dict of the Board Lot Size (Minimum Trading Unit) for each stock E.g. {'HK.00001': 500}
        """
        input_csv = HKEXInterface.get_security_df_full()
        return {('HK.' + row['Stock Code']): int(row['Board Lot'].replace(',', '')) for index, row in
                input_csv[input_csv['Category'] == 'Equity'].iterrows()}
