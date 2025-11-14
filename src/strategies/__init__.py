
from abc import ABC, abstractmethod
from typing import Dict, List
from datetime import datetime, timedelta

import pandas as pd

from utils import logger
from modules.futu_market import FutuMarket
from utils.global_vars import get_logger

class Strategies(ABC):
    """
    策略基础类 - 基于FutuMarket模块

    特性:
    - 集成FutuMarket模块，支持实时数据获取
    - 支持历史K线数据缓存和增量更新
    - 支持市场状态检测
    - 统一数据格式处理
    - 向后兼容旧的input_data初始化方式
    """

    def __init__(self,
                 input_data: Dict[str, pd.DataFrame] = None,
                 futu_market: FutuMarket = None,
                 stock_codes: List[str] = None,
                 ktype: str = "K_DAY",
                 autype: str = "qfq",
                 observation: int = 100):
        """
        初始化策略 - 支持两种初始化方式

        方式1 (旧方式，向后兼容):
            strategy = MACDCross(input_data=data_dict, fast_period=12, ...)

        方式2 (新方式，推荐):
            strategy = MACDCross(
                futu_market=fm,
                stock_codes=['HK.00700'],
                ktype="K_DAY",
                fast_period=12,
                ...
            )

        Args:
            input_data: 预处理的数据字典 (旧方式)
            futu_market: FutuMarket实例 (新方式)
            stock_codes: 股票代码列表 (新方式)
            ktype: K线类型 (K_1M, K_5M, K_15M, K_30M, K_60M, K_DAY, K_WEEK, K_MON)
            autype: 复权类型 (qfq-前复权, hfq-后复权, none-不复权)
            observation: 观察周期长度
        """
        super().__init__()

        # 日志
        self.logger = get_logger(self.__class__.__name__)

        # 判断初始化方式
        if input_data is not None:
            # 旧方式：使用预处理的数据
            self._init_legacy_mode(input_data, observation)
        elif futu_market is not None and stock_codes is not None:
            # 新方式：使用FutuMarket获取数据
            self._init_futu_mode(futu_market, stock_codes, ktype, autype, observation)
        else:
            raise ValueError(
                "请提供初始化参数：\n"
                "1. 旧方式: input_data (dict)\n"
                "2. 新方式: futu_market (FutuMarket) 和 stock_codes (list)"
            )

    def _init_legacy_mode(self, input_data: Dict[str, pd.DataFrame], observation: int):
        """
        旧模式初始化 - 兼容现有子类

        Args:
            input_data: 预处理的数据字典
            observation: 观察周期
        """
        self.input_data = input_data
        self.futu_market = None
        self.stock_codes = list(input_data.keys())
        self.ktype = "K_DAY"  # 默认值
        self.autype = "qfq"   # 默认值
        self.observation = observation
        self.logger.debug(f"使用旧模式初始化，共 {len(self.stock_codes)} 只股票")

    def _init_futu_mode(self,
                       futu_market: FutuMarket,
                       stock_codes: List[str],
                       ktype: str,
                       autype: str,
                       observation: int):
        """
        新模式初始化 - 基于FutuMarket

        Args:
            futu_market: FutuMarket实例
            stock_codes: 股票代码列表
            ktype: K线类型
            autype: 复权类型
            observation: 观察周期
        """
        self.futu_market = futu_market
        self.stock_codes = stock_codes
        self.ktype = ktype
        self.autype = autype
        self.observation = observation

        # 数据缓存: {stock_code: DataFrame}
        self.input_data: Dict[str, pd.DataFrame] = {}

        # 初始化数据
        self._initialize_data()
        self.logger.info(f"使用新模式初始化，共 {len(self.stock_codes)} 只股票")

    def _initialize_data(self):
        """初始化策略数据 - 加载历史K线"""
        for stock_code in self.stock_codes:
            try:
                # 计算历史数据起止日期
                end_date = datetime.now().strftime("%Y-%m-%d")

                # 根据K线类型计算起始日期
                days_map = {
                    "K_1M": self.observation * 1,     # 1分钟K线需要约observation天
                    "K_5M": self.observation * 1,     # 5分钟K线
                    "K_15M": self.observation * 1,    # 15分钟K线
                    "K_30M": self.observation * 2,    # 30分钟K线
                    "K_60M": self.observation * 2,    # 60分钟K线
                    "K_DAY": self.observation * 1.5,  # 日K线需要考虑非交易日
                    "K_WEEK": self.observation * 7,   # 周K线
                    "K_MON": self.observation * 30    # 月K线
                }

                days_needed = int(days_map.get(self.ktype, self.observation * 1.5))
                start_date = (datetime.now() - timedelta(days=days_needed)).strftime("%Y-%m-%d")

                # 请求历史K线数据
                df = self.futu_market.request_history_kline(
                    code=stock_code,
                    start=start_date,
                    end=end_date,
                    ktype=self.ktype,
                    autype=self.autype,
                    max_count=self.observation
                )

                if not df.empty:
                    # 确保只保留最近observation条数据
                    self.input_data[stock_code] = df.iloc[-self.observation:].reset_index(drop=True)
                    self.logger.info(f"初始化 {stock_code} 数据成功，共 {len(self.input_data[stock_code])} 条记录")
                else:
                    self.logger.warning(f"初始化 {stock_code} 数据为空")
                    self.input_data[stock_code] = pd.DataFrame()

            except Exception as e:
                self.logger.error(f"初始化 {stock_code} 数据失败: {e}")
                self.input_data[stock_code] = pd.DataFrame()

    def update_realtime_data(self, stock_code: str = None):
        """
        更新实时数据 (仅新模式支持)

        Args:
            stock_code: 指定更新的股票代码，None则更新所有股票
        """
        if self.futu_market is None:
            self.logger.warning("旧模式不支持实时数据更新")
            return

        codes_to_update = [stock_code] if stock_code else self.stock_codes

        for code in codes_to_update:
            try:
                # 获取最新K线数据（只获取1条）
                kline_list = self.futu_market.get_cur_kline(
                    codes=[code],
                    num=1,
                    ktype=self.ktype,
                    autype=self.autype
                )

                if kline_list and len(kline_list) > 0:
                    # 转换为DataFrame格式
                    latest_kline = kline_list[0]
                    latest_data = pd.DataFrame([{
                        'time_key': latest_kline.time_key,
                        'open': latest_kline.open,
                        'high': latest_kline.high,
                        'low': latest_kline.low,
                        'close': latest_kline.close,
                        'volume': latest_kline.volume,
                        'turnover': latest_kline.turnover
                    }])

                    # 更新到缓存数据
                    if code in self.input_data and not self.input_data[code].empty:
                        # 移除重复的time_key数据
                        time_key = latest_data['time_key'].iloc[0]
                        self.input_data[code] = self.input_data[code][
                            self.input_data[code]['time_key'] != time_key
                        ]

                        # 追加新数据并保持observation长度
                        self.input_data[code] = pd.concat([self.input_data[code], latest_data])
                        self.input_data[code] = self.input_data[code].iloc[-self.observation:].reset_index(drop=True)

                        # 调用子类的parse_data方法处理新数据
                        self.parse_data(stock_list=[code], latest_data=latest_data, backtesting=False)

                        self.logger.debug(f"更新 {code} 实时数据成功")
                    else:
                        self.logger.warning(f"{code} 缓存数据为空，无法更新")
                else:
                    self.logger.warning(f"获取 {code} 实时K线数据为空")

            except Exception as e:
                self.logger.error(f"更新 {code} 实时数据失败: {e}")

    def get_market_state(self, stock_code: str) -> str:
        """
        获取股票市场状态

        Args:
            stock_code: 股票代码

        Returns:
            str: ���场状态字符串
        """
        try:
            states = self.futu_market.get_market_state([stock_code])
            if states and len(states) > 0:
                return states[0].market_state
            return "UNKNOWN"
        except Exception as e:
            self.logger.error(f"获取 {stock_code} 市场状态失败: {e}")
            return "UNKNOWN"

    def is_market_open(self, stock_code: str) -> bool:
        """
        检查市场是否开盘

        Args:
            stock_code: 股票代码

        Returns:
            bool: 市场是否开盘
        """
        state = self.get_market_state(stock_code)
        return state in ["TRADING", "REST"]  # TRADING-交易中, REST-休市中但在交易时段

    @abstractmethod
    def parse_data(self, stock_list: list = None, latest_data: pd.DataFrame = None, backtesting: bool = False):
        """
        解析和处理数据

        Args:
            stock_list: 需要处理的股票列表
            latest_data: 最新数据（实时模式）
            backtesting: 是否回测模式
        """
        pass

    @abstractmethod
    def buy(self, stock_code: str) -> bool:
        """
        买入信号判断

        Args:
            stock_code: 股票代码

        Returns:
            bool: 是否产生买入信号
        """
        pass

    @abstractmethod
    def sell(self, stock_code: str) -> bool:
        """
        卖出信号判断

        Args:
            stock_code: 股票代码

        Returns:
            bool: 是否产生卖出信号
        """
        pass

    def get_current_and_previous_record(self, stock_code: str) -> tuple:
        """
        获取当前和上一条记录

        Args:
            stock_code: 股票代码

        Returns:
            tuple: (当前记录, 上一条记录)
        """
        assert stock_code in self.input_data, f"股票 {stock_code} 不在数据缓存中"
        assert len(self.input_data[stock_code]) >= 2, f"股票 {stock_code} 数据不足2条"

        return self.input_data[stock_code].iloc[-1], self.input_data[stock_code].iloc[-2]

    def get_input_data(self) -> dict:
        """
        获取所有数据副本

        Returns:
            dict: 数据字典副本
        """
        return {code: df.copy() for code, df in self.input_data.items()}

    def get_input_data_stock_code(self, stock_code: str) -> pd.DataFrame:
        """
        获取指定股票数据副本

        Args:
            stock_code: 股票代码

        Returns:
            pd.DataFrame: 数据副本
        """
        assert stock_code in self.input_data, f"股票 {stock_code} 不在数据缓存中"
        return self.input_data[stock_code].copy()

    def set_input_data(self, input_data: dict) -> None:
        """
        设置所有数据

        Args:
            input_data: 数据字典
        """
        self.input_data = {code: df.copy() for code, df in input_data.items()}

    def set_input_data_stock_code(self, stock_code: str, input_df: pd.DataFrame) -> None:
        """
        设置指定股票数据

        Args:
            stock_code: 股票代码
            input_df: 数据DataFrame
        """
        self.input_data[stock_code] = input_df.copy()

    def add_stock(self, stock_code: str):
        """
        添加新股票到策略监控列表 (仅新模式支持)

        Args:
            stock_code: 股票代码
        """
        if self.futu_market is None:
            self.logger.warning("旧模式不支持添加股票")
            return

        if stock_code not in self.stock_codes:
            self.stock_codes.append(stock_code)
            # 初始化新股票数据
            try:
                end_date = datetime.now().strftime("%Y-%m-%d")
                days_map = {
                    "K_1M": self.observation * 1,
                    "K_5M": self.observation * 1,
                    "K_15M": self.observation * 1,
                    "K_30M": self.observation * 2,
                    "K_60M": self.observation * 2,
                    "K_DAY": self.observation * 1.5,
                    "K_WEEK": self.observation * 7,
                    "K_MON": self.observation * 30
                }
                days_needed = int(days_map.get(self.ktype, self.observation * 1.5))
                start_date = (datetime.now() - timedelta(days=days_needed)).strftime("%Y-%m-%d")

                df = self.futu_market.request_history_kline(
                    code=stock_code,
                    start=start_date,
                    end=end_date,
                    ktype=self.ktype,
                    autype=self.autype,
                    max_count=self.observation
                )

                if not df.empty:
                    self.input_data[stock_code] = df.iloc[-self.observation:].reset_index(drop=True)
                    self.parse_data(stock_list=[stock_code], latest_data=None, backtesting=False)
                    self.logger.info(f"添加股票 {stock_code} 成功")
                else:
                    self.input_data[stock_code] = pd.DataFrame()
                    self.logger.warning(f"添加股票 {stock_code} 数据为空")
            except Exception as e:
                self.logger.error(f"添加股票 {stock_code} 失败: {e}")
                self.input_data[stock_code] = pd.DataFrame()

    def remove_stock(self, stock_code: str):
        """
        从策略监控列表移除股票

        Args:
            stock_code: 股票代码
        """
        if stock_code in self.stock_codes:
            self.stock_codes.remove(stock_code)
            if stock_code in self.input_data:
                del self.input_data[stock_code]
            self.logger.info(f"移除股票 {stock_code} 成功")

    # ================== 富途自选股管理方法 ==================

    def get_user_security_groups(self, group_type: str = "CUSTOM") -> List:
        """
        获取富途自选股分组列表 (仅新模式支持)

        Args:
            group_type: 分组类型
                - CUSTOM: 自定义分组
                - SYSTEM: 系统分组
                - ALL: 所有分组

        Returns:
            List: 分组列表，每个元素包含 group_name, group_type 等信息
        """
        if self.futu_market is None:
            self.logger.warning("旧模式不支持获取自选股分组")
            return []

        try:
            groups = self.futu_market.get_user_security_group(group_type)
            self.logger.info(f"获取自选股分组成功，共 {len(groups) if groups else 0} 个分组")
            return groups
        except Exception as e:
            self.logger.error(f"获取自选股分组失败: {e}")
            return []

    def get_user_security(self, group_name: str = "自选股") -> List:
        """
        获取指定分组的自选股列表 (仅新模式支持)

        Args:
            group_name: 分组名称，默认为"自选股"

        Returns:
            List: 股票代码列表
        """
        if self.futu_market is None:
            self.logger.warning("旧模式不支持获取自选股")
            return []

        try:
            stocks = self.futu_market.get_user_security(group_name)
            self.logger.info(f"获取分组 {group_name} 自选股成功，共 {len(stocks) if stocks else 0} 只")
            return stocks
        except Exception as e:
            self.logger.error(f"获取分组 {group_name} 自选股失败: {e}")
            return []

    def add_to_user_security(self, group_name: str, stock_codes: List[str]) -> bool:
        """
        添加股票到富途自选股分组 (仅新模式支持)

        Args:
            group_name: 分组名称
            stock_codes: 要添加的股票代码列表

        Returns:
            bool: 是否添加成功
        """
        if self.futu_market is None:
            self.logger.warning("旧模式不支持修改自选股")
            return False

        try:
            success = self.futu_market.modify_user_security(
                group_name=group_name,
                codes=stock_codes,
                op_type="ADD"
            )
            if success:
                self.logger.info(f"成功添加 {len(stock_codes)} 只股票到分组 {group_name}")
            else:
                self.logger.warning(f"添加股票到分组 {group_name} 失败")
            return success
        except Exception as e:
            self.logger.error(f"添加股票到分组 {group_name} 异常: {e}")
            return False

    def remove_from_user_security(self, group_name: str, stock_codes: List[str]) -> bool:
        """
        从富途自选股分组移除股票 (仅新模式支持)

        Args:
            group_name: 分组名称
            stock_codes: 要移除的股票代码列表

        Returns:
            bool: 是否移除成功
        """
        if self.futu_market is None:
            self.logger.warning("旧模式不支持修改自选股")
            return False

        try:
            success = self.futu_market.modify_user_security(
                group_name=group_name,
                codes=stock_codes,
                op_type="DEL"
            )
            if success:
                self.logger.info(f"成功从分组 {group_name} 移除 {len(stock_codes)} 只股票")
            else:
                self.logger.warning(f"从分组 {group_name} 移除股票失败")
            return success
        except Exception as e:
            self.logger.error(f"从分组 {group_name} 移除股票异常: {e}")
            return False

    def sync_strategy_to_user_security(self, group_name: str) -> bool:
        """
        将当前策略监控的股票同步到富途自选股分组 (仅新模式支持)

        功能：
        1. 获取分组当前的股票列表
        2. 比较差异
        3. 添加策略中有但分组中没有的股票
        4. 移除分组中有但策略中没有的股票

        Args:
            group_name: 目标分组名称

        Returns:
            bool: 是否同步成功
        """
        if self.futu_market is None:
            self.logger.warning("旧模式不支持同步自选股")
            return False

        try:
            # 获取分组当前股票
            current_stocks = self.get_user_security(group_name)
            if current_stocks is None:
                current_stocks = []

            # 提取股票代码（假设返回格式可能是对象或字典）
            if current_stocks and isinstance(current_stocks[0], dict):
                current_codes = [s.get('code', s.get('stock_code', '')) for s in current_stocks]
            else:
                current_codes = current_stocks

            # 计算差异
            strategy_codes = set(self.stock_codes)
            current_codes_set = set(current_codes)

            to_add = list(strategy_codes - current_codes_set)
            to_remove = list(current_codes_set - strategy_codes)

            # 执行同步
            success = True
            if to_add:
                self.logger.info(f"准备添加 {len(to_add)} 只股票到分组 {group_name}")
                success = success and self.add_to_user_security(group_name, to_add)

            if to_remove:
                self.logger.info(f"准备从分组 {group_name} 移除 {len(to_remove)} 只股票")
                success = success and self.remove_from_user_security(group_name, to_remove)

            if not to_add and not to_remove:
                self.logger.info(f"分组 {group_name} 已与策略同步，无需更新")

            return success

        except Exception as e:
            self.logger.error(f"同步策略到分组 {group_name} 异常: {e}")
            return False

    def load_stocks_from_user_security(self, group_name: str, replace: bool = False) -> bool:
        """
        从富途自选股分组加载股票到策略 (仅新模式支持)

        Args:
            group_name: 分组名称
            replace: 是否替换当前监控列表（True）还是追加（False）

        Returns:
            bool: 是否加载成功
        """
        if self.futu_market is None:
            self.logger.warning("旧模式不支持加载自选股")
            return False

        try:
            # 获取分组股票
            stocks = self.get_user_security(group_name)
            if not stocks:
                self.logger.warning(f"分组 {group_name} 为空或不存在")
                return False

            # 提取股票代码
            if isinstance(stocks[0], dict):
                codes = [s.get('code', s.get('stock_code', '')) for s in stocks]
            else:
                codes = stocks

            # 过滤空代码
            codes = [c for c in codes if c]

            if not codes:
                self.logger.warning(f"分组 {group_name} 没有有效股票代码")
                return False

            # 替换或追加
            if replace:
                # 清除现有股票
                for old_code in list(self.stock_codes):
                    self.remove_stock(old_code)
                self.logger.info(f"清除现有监控列表，准备加载分组 {group_name}")

            # 添加新股票
            added_count = 0
            for code in codes:
                if code not in self.stock_codes:
                    self.add_stock(code)
                    added_count += 1

            self.logger.info(
                f"从分组 {group_name} 加载股票完成，"
                f"共 {len(codes)} 只，新增 {added_count} 只"
            )
            return True

        except Exception as e:
            self.logger.error(f"从分组 {group_name} 加载股票异常: {e}")
            return False
