

import pandas as pd

from strategies import Strategies
from utils import logger

pd.options.mode.chained_assignment = None  # default='warn'


class KDJCross(Strategies):
    def __init__(self, input_data: dict, fast_k=9, slow_k=3, slow_d=3, over_buy=80, over_sell=20, observation=100):
        """
        Initialize KDJ-Cross Strategy Instance
        :param input_data:
        :param fast_k: Fast K-Period (Default = 9)
        :param slow_k: Slow K-Period (Default = 3)
        :param slow_d: Slow D-Period (Default = 3)
        :param over_buy: Over-buy Threshold (Default = 80)
        :param over_sell: Over-sell Threshold (Default = 20)
        :param observation: Observation Period in Dataframe (Default = 100)
        """
        self.FAST_K = fast_k
        self.SLOW_K = slow_k
        self.SLOW_D = slow_d
        self.OVER_BUY = over_buy
        self.OVER_SELL = over_sell
        self.OBSERVATION = observation
        self.default_logger = logger.get_logger("kdj_cross")

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
            latest_data = pd.concat([latest_data, pd.DataFrame(columns=['%k', '%d', '%j'])])
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

            low = self.input_data[stock_code]['low'].rolling(self.FAST_K, min_periods=self.FAST_K).min()
            low.fillna(value=self.input_data[stock_code]['low'].expanding().min(), inplace=True)
            high = self.input_data[stock_code]['high'].rolling(self.FAST_K, min_periods=self.FAST_K).max()
            high.fillna(value=self.input_data[stock_code]['high'].expanding().max(), inplace=True)
            rsv = (self.input_data[stock_code]['close'] - low) / (high - low) * 100
            # Com = Specify decay in terms of center of mass, α=1/(1+com), for com≥0.
            # For common KDJ 9-3-3, the com option should be set as 3 - 1 = 2
            self.input_data[stock_code]['%k'] = pd.DataFrame(rsv).ewm(com=self.SLOW_K - 1).mean()
            self.input_data[stock_code]['%d'] = self.input_data[stock_code]['%k'].ewm(com=self.SLOW_D - 1).mean()
            self.input_data[stock_code]['%j'] = 3 * self.input_data[stock_code]['%k'] - \
                                                2 * self.input_data[stock_code]['%d']

            self.input_data[stock_code].reset_index(drop=True, inplace=True)

    def buy(self, stock_code) -> bool:

        current_record, previous_record = self.get_current_and_previous_record(stock_code)
        # Buy Decision based on 当D < 超卖线, K线和D线同时上升，且K线从下向上穿过D线时，买入
        buy_decision = self.OVER_SELL > current_record['%d'] > previous_record['%d'] > previous_record['%k'] and \
                       current_record['%k'] > previous_record['%k'] and \
                       current_record['%k'] > current_record['%d']

        if buy_decision:
            self.default_logger.info(
                f"Buy Decision: {current_record['time_key']} based on \n {pd.concat([previous_record.to_frame().transpose(), current_record.to_frame().transpose()], axis=0)}")

        return buy_decision

    def sell(self, stock_code) -> bool:

        current_record, previous_record = self.get_current_and_previous_record(stock_code)
        # Sell Decision based on 当D > 超买线, K线和D线同时下降，且K线从上向下穿过D线时，卖出
        sell_decision = self.OVER_BUY < current_record['%d'] < previous_record['%d'] < previous_record['%k'] and \
                        current_record['%k'] < previous_record['%k'] and \
                        current_record['%k'] < current_record['%d']

        if sell_decision:
            self.default_logger.info(
                f"Sell Decision: {current_record['time_key']} based on \n {pd.concat([previous_record.to_frame().transpose(), current_record.to_frame().transpose()], axis=0)}")
        return sell_decision
