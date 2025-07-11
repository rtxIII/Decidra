

import pandas as pd

from filters import Filters


class TripleCross(Filters):
    def __init__(self, ma_period1: int = 5, ma_period2: int = 10, ma_period3: int = 20):
        self.MA_PERIOD1 = ma_period1
        self.MA_PERIOD2 = ma_period2
        self.MA_PERIOD3 = ma_period3
        super().__init__()

    def validate(self, input_data: pd.DataFrame, info_data: dict) -> bool:
        """

        :param input_data: Yahoo Finance Quantitative Data (Price, Volume, etc.)
        :param info_data: Yahoo Finance Fundamental Data (Company Description. PE Ratio, Etc.)
        :return:
        """
        if input_data.empty or input_data.shape[0] < 20:
            return False

        input_data['MA_1'] = input_data['close'].rolling(window=self.MA_PERIOD1).mean()
        input_data['MA_2'] = input_data['close'].rolling(window=self.MA_PERIOD2).mean()
        input_data['MA_3'] = input_data['close'].rolling(window=self.MA_PERIOD3).mean()

        current_record = input_data.iloc[-1]
        previous_record = input_data.iloc[-2]
        criterion_1 = current_record['volume'] > input_data.iloc[-10:]['volume'].max()
        criterion_2 = max([current_record['MA_1'], current_record['MA_2'], current_record['MA_3']]) / \
                      min([current_record['MA_1'], current_record['MA_2'], current_record['MA_3']]) < 1.01
        criterion_3 = current_record['close'] > current_record['MA_1'] and \
                      current_record['close'] > current_record['MA_2'] and \
                      current_record['close'] > current_record['MA_3']
        criterion_4 = previous_record['close'] < previous_record['MA_1'] and \
                      previous_record['close'] < previous_record['MA_2'] and \
                      previous_record['close'] < previous_record['MA_3']

        criteria = [criterion_1, criterion_2, criterion_3, criterion_4]

        return all(criterion for criterion in criteria)
