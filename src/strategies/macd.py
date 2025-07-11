


import pandas as pd

from strategies import Strategies
from utils import logger

pd.options.mode.chained_assignment = None  # default='warn'


class MACDCross(Strategies):
    def __init__(self, input_data: dict, fast_period=12, slow_period=26, signal_period=9, observation=100):
        self.MACD_FAST = fast_period
        self.MACD_SLOW = slow_period
        self.MACD_SIGNAL = signal_period
        self.OBSERVATION = observation
        self.default_logger = logger.get_logger("macd_cross")

        super().__init__(input_data)
        self.parse_data()

    def parse_data(self, stock_list: list = None, latest_data: pd.DataFrame = None, backtesting: bool = False):
        # Received New Data => Parse it Now to input_data
        if latest_data is not None:
            # Only need to update MACD for the stock_code with new data
            stock_list = [latest_data['code'][0]]

            # Remove records with duplicate time_key. Always use the latest data to override
            time_key = latest_data['time_key'][0]
            self.input_data[stock_list[0]].drop(
                self.input_data[stock_list[0]][self.input_data[stock_list[0]].time_key == time_key].index,
                inplace=True)
            # Append empty columns and concat at the bottom
            latest_data = pd.concat([latest_data, pd.DataFrame(columns=['MACD', 'MACD_signal', 'MACD_hist'])])
            self.input_data[stock_list[0]] = pd.concat([self.input_data[stock_list[0]], latest_data])
        elif stock_list is not None:
            # Override Updated Stock List
            stock_list = stock_list
        else:
            stock_list = self.input_data.keys()

        # Calculate MACD for the stock_list
        for stock_code in stock_list:
            # Need to truncate to a maximum length for low-latency
            if not backtesting:
                self.input_data[stock_code] = self.input_data[stock_code].iloc[
                                              -min(self.OBSERVATION, self.input_data[stock_code].shape[0]):]
            self.input_data[stock_code][['open', 'close', 'high', 'low']] = self.input_data[stock_code][
                ['open', 'close', 'high', 'low']].apply(pd.to_numeric)

            # MACD = EMA-Fast - EMA-Slow. Signal = EMA(MACD, Smooth-period)
            ema_fast = self.input_data[stock_code]['close'].ewm(span=self.MACD_FAST, adjust=False).mean()
            ema_slow = self.input_data[stock_code]['close'].ewm(span=self.MACD_SLOW, adjust=False).mean()
            self.input_data[stock_code]['MACD'] = ema_fast - ema_slow
            self.input_data[stock_code]['MACD_signal'] = self.input_data[stock_code]['MACD'].ewm(span=self.MACD_SIGNAL,
                                                                                                 adjust=False).mean()
            # MACD_hist = (MACD - MACD_signal) * 2
            self.input_data[stock_code]['MACD_hist'] = (self.input_data[stock_code]['MACD'] -
                                                        self.input_data[stock_code]['MACD_signal']) * 2

            self.input_data[stock_code].reset_index(drop=True, inplace=True)

    # @timeit
    def buy(self, stock_code) -> bool:
        # Crossover between MACD and Signal (Single Point Determined)
        current_record, previous_record = self.get_current_and_previous_record(stock_code)
        buy_decision = float(current_record['MACD']) > float(current_record['MACD_signal']) and float(
            previous_record['MACD']) <= float(previous_record['MACD_signal'])
        if buy_decision:
            self.default_logger.info(
                f"Buy Decision: {current_record['time_key']} based on \n {pd.concat([previous_record.to_frame().transpose(), current_record.to_frame().transpose()], axis=0)}")

        return buy_decision

    # @timeit
    def sell(self, stock_code) -> bool:
        # Crossover between Signal and MACD (Single Point Determined)
        current_record, previous_record = self.get_current_and_previous_record(stock_code)
        sell_decision = float(current_record['MACD']) < float(current_record['MACD_signal']) and float(
            previous_record['MACD']) >= float(previous_record['MACD_signal'])
        if sell_decision:
            self.default_logger.info(
                f"Sell Decision: {current_record['time_key']} based on \n {pd.concat([previous_record.to_frame().transpose(), current_record.to_frame().transpose()], axis=0)}")

        return sell_decision
