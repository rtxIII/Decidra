


import pandas as pd

from strategies import Strategies
from utils import logger

pd.options.mode.chained_assignment = None  # default='warn'


class EMARibbon(Strategies):
    def __init__(self, input_data: dict, ema_fast=5, ema_slow=8, ema_supp=13, observation=100):
        self.EMA_FAST = ema_fast
        self.EMA_SLOW = ema_slow
        self.EMA_SUPP = ema_supp
        self.OBSERVATION = observation
        self.default_logger = logger.get_logger("ema_ribbon")

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
            latest_data = pd.concat([latest_data, pd.DataFrame(columns=['EMA_fast', 'EMA_slow', 'EMA_supp'])])
            self.input_data[stock_list[0]] = pd.concat([self.input_data[stock_list[0]], latest_data])
        elif stock_list is not None:
            # Override Updated Stock List
            stock_list = stock_list
        else:
            stock_list = self.input_data.keys()

        # Calculate EMA for the stock_list
        for stock_code in stock_list:
            # Need to truncate to a maximum length for low-latency
            if not backtesting:
                self.input_data[stock_code] = self.input_data[stock_code].iloc[
                                              -min(self.OBSERVATION, self.input_data[stock_code].shape[0]):]
            self.input_data[stock_code][['open', 'close', 'high', 'low']] = self.input_data[stock_code][
                ['open', 'close', 'high', 'low']].apply(pd.to_numeric)

            self.input_data[stock_code]['EMA_fast'] = self.input_data[stock_code]['close'].ewm(span=self.EMA_FAST,
                                                                                               adjust=False).mean()
            self.input_data[stock_code]['EMA_slow'] = self.input_data[stock_code]['close'].ewm(span=self.EMA_SLOW,
                                                                                               adjust=False).mean()
            self.input_data[stock_code]['EMA_supp'] = self.input_data[stock_code]['close'].ewm(span=self.EMA_SUPP,
                                                                                               adjust=False).mean()

            self.input_data[stock_code].reset_index(drop=True, inplace=True)

    def buy(self, stock_code) -> bool:
        # Crossover of EMA Fast with other two EMAs
        current_record = self.input_data[stock_code].iloc[-1]
        previous_record = self.input_data[stock_code].iloc[-2]
        # Buy Decision based on EMA-Fast exceeds both other two EMAs (e.g., 5-bar > 8-bar and 13-bar)
        buy_decision = (
                               float(current_record['EMA_fast']) > float(current_record['EMA_slow']) and
                               float(current_record['EMA_fast']) > float(current_record['EMA_supp'])
                       ) and (
                               float(current_record['EMA_fast']) <= float(current_record['EMA_slow']) or
                               float(current_record['EMA_fast']) <= float(current_record['EMA_supp'])
                       )

        if buy_decision:
            self.default_logger.info(
                f"Buy Decision: {current_record['time_key']} based on \n {pd.concat([previous_record.to_frame().transpose(), current_record.to_frame().transpose()], axis=0)}")

        return buy_decision

    def sell(self, stock_code) -> bool:
        # Crossover of EMA Fast with other two EMAs
        current_record = self.input_data[stock_code].iloc[-1]
        previous_record = self.input_data[stock_code].iloc[-2]
        # Sell Decision based on EMA-Fast drops below either of the two other EMAs(e.g., 5-bar < 8-bar or 13-bar)
        sell_decision = (
                                float(current_record['EMA_fast']) < float(current_record['EMA_slow']) or
                                float(current_record['EMA_fast']) < float(current_record['EMA_supp'])
                        ) and (
                                float(current_record['EMA_fast']) >= float(current_record['EMA_slow']) and
                                float(current_record['EMA_fast']) >= float(current_record['EMA_supp'])
                        )
        if sell_decision:
            self.default_logger.info(
                f"Sell Decision: {current_record['time_key']} based on \n {pd.concat([previous_record.to_frame().transpose(), current_record.to_frame().transpose()], axis=0)}")
        return sell_decision
