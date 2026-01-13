# -*- coding: utf-8 -*-
"""
===================================
A股自选股智能分析系统 - 存储层
===================================

职责：
1. 管理 SQLite 数据库连接（单例模式）
2. 定义数据模型
3. 提供数据存取接口
4. 实现智能更新逻辑（断点续传）
"""

import logging
import sqlite3
from dataclasses import dataclass
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from pathlib import Path

import pandas as pd

from config import get_config

logger = logging.getLogger(__name__)


@dataclass
class StockDaily:
    """
    股票日线数据模型

    存储每日行情数据和计算的技术指标
    """
    code: str
    date: date
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    close: Optional[float] = None
    volume: Optional[float] = None
    amount: Optional[float] = None
    pct_chg: Optional[float] = None
    ma5: Optional[float] = None
    ma10: Optional[float] = None
    ma20: Optional[float] = None
    volume_ratio: Optional[float] = None
    data_source: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    id: Optional[int] = None

    def __repr__(self):
        return f"<StockDaily(code={self.code}, date={self.date}, close={self.close})>"

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'code': self.code,
            'date': self.date,
            'open': self.open,
            'high': self.high,
            'low': self.low,
            'close': self.close,
            'volume': self.volume,
            'amount': self.amount,
            'pct_chg': self.pct_chg,
            'ma5': self.ma5,
            'ma10': self.ma10,
            'ma20': self.ma20,
            'volume_ratio': self.volume_ratio,
            'data_source': self.data_source,
        }


class DatabaseManager:
    """
    数据库管理器 - 单例模式

    职责：
    1. 管理数据库连接
    2. 封装数据存取操作
    """

    _instance: Optional['DatabaseManager'] = None

    _CREATE_TABLE_SQL = """
        CREATE TABLE IF NOT EXISTS stock_daily (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL,
            date DATE NOT NULL,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume REAL,
            amount REAL,
            pct_chg REAL,
            ma5 REAL,
            ma10 REAL,
            ma20 REAL,
            volume_ratio REAL,
            data_source TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(code, date)
        )
    """

    _CREATE_INDEX_SQL = """
        CREATE INDEX IF NOT EXISTS ix_code_date ON stock_daily(code, date)
    """

    def __new__(cls, *args, **kwargs):
        """单例模式实现"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, db_path: Optional[str] = None):
        """
        初始化数据库管理器

        Args:
            db_path: 数据库文件路径（可选，默认从配置读取）
        """
        if self._initialized:
            return

        if db_path is None:
            config = get_config()
            db_url = config.get_db_url()
            # 从 sqlite:///path 格式提取路径
            if db_url.startswith('sqlite:///'):
                db_path = db_url[10:]
            else:
                db_path = db_url

        self._db_path = db_path

        # 确保目录存在
        db_dir = Path(db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)

        # 初始化数据库表
        self._init_tables()

        self._initialized = True
        logger.info(f"数据库初始化完成: {db_path}")

    def _get_connection(self) -> sqlite3.Connection:
        """获取数据库连接"""
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_tables(self) -> None:
        """初始化数据库表"""
        with self._get_connection() as conn:
            conn.execute(self._CREATE_TABLE_SQL)
            conn.execute(self._CREATE_INDEX_SQL)
            conn.commit()

    @classmethod
    def get_instance(cls) -> 'DatabaseManager':
        """获取单例实例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """重置单例（用于测试）"""
        cls._instance = None

    def _row_to_stock_daily(self, row: sqlite3.Row) -> StockDaily:
        """将数据库行转换为 StockDaily 对象"""
        row_date = row['date']
        if isinstance(row_date, str):
            row_date = datetime.strptime(row_date, '%Y-%m-%d').date()

        return StockDaily(
            id=row['id'],
            code=row['code'],
            date=row_date,
            open=row['open'],
            high=row['high'],
            low=row['low'],
            close=row['close'],
            volume=row['volume'],
            amount=row['amount'],
            pct_chg=row['pct_chg'],
            ma5=row['ma5'],
            ma10=row['ma10'],
            ma20=row['ma20'],
            volume_ratio=row['volume_ratio'],
            data_source=row['data_source'],
            created_at=row['created_at'],
            updated_at=row['updated_at'],
        )

    def has_today_data(self, code: str, target_date: Optional[date] = None) -> bool:
        """
        检查是否已有指定日期的数据

        用于断点续传逻辑：如果已有数据则跳过网络请求

        Args:
            code: 股票代码
            target_date: 目标日期（默认今天）

        Returns:
            是否存在数据
        """
        if target_date is None:
            target_date = date.today()

        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT 1 FROM stock_daily WHERE code = ? AND date = ? LIMIT 1",
                (code, target_date.isoformat())
            )
            return cursor.fetchone() is not None

    def get_latest_data(self, code: str, days: int = 2) -> List[StockDaily]:
        """
        获取最近 N 天的数据

        用于计算"相比昨日"的变化

        Args:
            code: 股票代码
            days: 获取天数

        Returns:
            StockDaily 对象列表（按日期降序）
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                """SELECT * FROM stock_daily
                   WHERE code = ?
                   ORDER BY date DESC
                   LIMIT ?""",
                (code, days)
            )
            return [self._row_to_stock_daily(row) for row in cursor.fetchall()]

    def get_data_range(
        self,
        code: str,
        start_date: date,
        end_date: date
    ) -> List[StockDaily]:
        """
        获取指定日期范围的数据

        Args:
            code: 股票代码
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            StockDaily 对象列表
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                """SELECT * FROM stock_daily
                   WHERE code = ? AND date >= ? AND date <= ?
                   ORDER BY date""",
                (code, start_date.isoformat(), end_date.isoformat())
            )
            return [self._row_to_stock_daily(row) for row in cursor.fetchall()]

    def save_daily_data(
        self,
        df: pd.DataFrame,
        code: str,
        data_source: str = "Unknown"
    ) -> int:
        """
        保存日线数据到数据库

        策略：
        - 使用 UPSERT 逻辑（存在则更新，不存在则插入）

        Args:
            df: 包含日线数据的 DataFrame
            code: 股票代码
            data_source: 数据来源名称

        Returns:
            处理的记录数
        """
        if df is None or df.empty:
            logger.warning(f"保存数据为空，跳过 {code}")
            return 0

        saved_count = 0
        now = datetime.now().isoformat()

        with self._get_connection() as conn:
            for _, row in df.iterrows():
                # 解析日期
                row_date = row.get('date')
                if isinstance(row_date, str):
                    row_date = datetime.strptime(row_date, '%Y-%m-%d').date()
                elif isinstance(row_date, datetime):
                    row_date = row_date.date()
                elif isinstance(row_date, pd.Timestamp):
                    row_date = row_date.date()

                # 使用 UPSERT 语法
                conn.execute(
                    """INSERT INTO stock_daily
                       (code, date, open, high, low, close, volume, amount,
                        pct_chg, ma5, ma10, ma20, volume_ratio, data_source,
                        created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                       ON CONFLICT(code, date) DO UPDATE SET
                           open = excluded.open,
                           high = excluded.high,
                           low = excluded.low,
                           close = excluded.close,
                           volume = excluded.volume,
                           amount = excluded.amount,
                           pct_chg = excluded.pct_chg,
                           ma5 = excluded.ma5,
                           ma10 = excluded.ma10,
                           ma20 = excluded.ma20,
                           volume_ratio = excluded.volume_ratio,
                           data_source = excluded.data_source,
                           updated_at = excluded.updated_at""",
                    (
                        code,
                        row_date.isoformat(),
                        row.get('open'),
                        row.get('high'),
                        row.get('low'),
                        row.get('close'),
                        row.get('volume'),
                        row.get('amount'),
                        row.get('pct_chg'),
                        row.get('ma5'),
                        row.get('ma10'),
                        row.get('ma20'),
                        row.get('volume_ratio'),
                        data_source,
                        now,
                        now,
                    )
                )
                saved_count += 1

            conn.commit()
            logger.info(f"保存 {code} 数据成功，处理 {saved_count} 条")

        return saved_count

    def get_analysis_context(
        self,
        code: str,
        target_date: Optional[date] = None
    ) -> Optional[Dict[str, Any]]:
        """
        获取分析所需的上下文数据

        返回今日数据 + 昨日数据的对比信息

        Args:
            code: 股票代码
            target_date: 目标日期（默认今天）

        Returns:
            包含今日数据、昨日对比等信息的字典
        """
        if target_date is None:
            target_date = date.today()

        # 获取最近2天数据
        recent_data = self.get_latest_data(code, days=2)

        if not recent_data:
            logger.warning(f"未找到 {code} 的数据")
            return None

        today_data = recent_data[0]
        yesterday_data = recent_data[1] if len(recent_data) > 1 else None

        context = {
            'code': code,
            'date': today_data.date.isoformat(),
            'today': today_data.to_dict(),
        }

        if yesterday_data:
            context['yesterday'] = yesterday_data.to_dict()

            # 计算相比昨日的变化
            if yesterday_data.volume and yesterday_data.volume > 0:
                context['volume_change_ratio'] = round(
                    today_data.volume / yesterday_data.volume, 2
                )

            if yesterday_data.close and yesterday_data.close > 0:
                context['price_change_ratio'] = round(
                    (today_data.close - yesterday_data.close) / yesterday_data.close * 100, 2
                )

            # 均线形态判断
            context['ma_status'] = self._analyze_ma_status(today_data)

        return context

    def _analyze_ma_status(self, data: StockDaily) -> str:
        """
        分析均线形态

        判断条件：
        - 多头排列：close > ma5 > ma10 > ma20
        - 空头排列：close < ma5 < ma10 < ma20
        - 震荡整理：其他情况
        """
        close = data.close or 0
        ma5 = data.ma5 or 0
        ma10 = data.ma10 or 0
        ma20 = data.ma20 or 0

        if close > ma5 > ma10 > ma20 > 0:
            return "多头排列"
        elif close < ma5 < ma10 < ma20 and ma20 > 0:
            return "空头排列"
        elif close > ma5 and ma5 > ma10:
            return "短期向好"
        elif close < ma5 and ma5 < ma10:
            return "短期走弱"
        else:
            return "震荡整理"


# 便捷函数
def get_db() -> DatabaseManager:
    """获取数据库管理器实例的快捷方式"""
    return DatabaseManager.get_instance()


if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.DEBUG)

    db = get_db()

    print("=== 数据库测试 ===")
    print("数据库初始化成功")

    # 测试检查今日数据
    has_data = db.has_today_data('600519')
    print(f"茅台今日是否有数据: {has_data}")

    # 测试保存数据
    test_df = pd.DataFrame({
        'date': [date.today()],
        'open': [1800.0],
        'high': [1850.0],
        'low': [1780.0],
        'close': [1820.0],
        'volume': [10000000],
        'amount': [18200000000],
        'pct_chg': [1.5],
        'ma5': [1810.0],
        'ma10': [1800.0],
        'ma20': [1790.0],
        'volume_ratio': [1.2],
    })

    saved = db.save_daily_data(test_df, '600519', 'TestSource')
    print(f"保存测试数据: {saved} 条")

    # 测试获取上下文
    context = db.get_analysis_context('600519')
    print(f"分析上下文: {context}")
