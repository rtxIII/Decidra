
from abc import ABC, abstractmethod

import pandas as pd


class Strategies(ABC):
    def __init__(self, input_data: dict):
        self.input_data = input_data
        super().__init__()

    @abstractmethod
    def parse_data(self, stock_list: list, latest_data: pd.DataFrame, backtesting: bool):
        """
        Stock List for Retrieval Mode
        Latest Data for Subscription Mode
        Backtesting for Backtesting Mode
        :param stock_list:
        :param latest_data:
        :param backtesting:
        """
        pass

    @abstractmethod
    def buy(self, stock_code) -> bool:
        pass

    @abstractmethod
    def sell(self, stock_code) -> bool:
        pass

    def get_current_and_previous_record(self, stock_code: str) -> tuple:
        return self.input_data[stock_code].iloc[-2], self.input_data[stock_code].iloc[-3]

    def get_input_data(self) -> dict:
        return self.input_data.copy()

    def get_input_data_stock_code(self, stock_code: str) -> pd.DataFrame:
        return self.input_data[stock_code].copy()

    def set_input_data(self, input_data: dict) -> None:
        self.input_data = input_data.copy()

    def set_input_data_stock_code(self, stock_code: str, input_df: pd.DataFrame) -> None:
        self.input_data[stock_code] = input_df.copy()
