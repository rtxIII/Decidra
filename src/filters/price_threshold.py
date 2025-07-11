


import pandas as pd

from filters import Filters


class PriceThreshold(Filters):
    def __init__(self, price_threshold: int = 3):
        self.PRICE_THRESHOLD = price_threshold
        super().__init__()

    def validate(self, input_data: pd.DataFrame, info_data: dict) -> bool:
        """
            Return True if the mean close price for the previous 30 days are larger than 1 HKD.
        :param input_data: Yahoo Finance Quantitative Data (Price, Volume, etc.)
        :param info_data: Yahoo Finance Fundamental Data (Company Description. PE Ratio, Etc.)
        :return:
        """
        if input_data.empty:
            return False
        last_30_records = input_data.iloc[-min(30, input_data.shape[0]):]
        return last_30_records['close'].mean() > self.PRICE_THRESHOLD
