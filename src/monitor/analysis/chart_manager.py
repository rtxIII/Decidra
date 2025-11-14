"""
ChartManager - 图表管理模块

负责分析页面的K线图表、成交量图表、技术指标图表的显示和交互管理
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass

from base.futu_class import KLineData
from utils.global_vars import get_logger

# 图表显示配置
CHART_DISPLAY_CONFIG = {
    'kline_height_ratio': 0.6,     # K线图表高度比例
    'volume_height_ratio': 0.4,    # 成交量图表高度比例
    'max_display_bars': 100,       # 最大显示K线数量
    'min_display_bars': 20,        # 最小显示K线数量
    'scroll_step': 5,              # 滚动步长
}

# 图表样式配置
CHART_STYLE_CONFIG = {
    'up_color': 'red',         # 上涨颜色
    'down_color': 'green',     # 下跌颜色
    'ma_colors': {             # 均线颜色
        'ma5': 'yellow',
        'ma10': 'purple',
        'ma20': 'blue',
        'ma60': 'orange'
    },
    'volume_color': 'cyan',    # 成交量颜色
    'grid_color': 'gray',      # 网格颜色
}


@dataclass
class ChartRange:
    """图表显示范围"""
    start_index: int
    end_index: int
    total_bars: int


@dataclass
class ChartData:
    """图表数据"""
    kline_data: List[KLineData]
    technical_indicators: Dict[str, Any]
    display_range: ChartRange
    time_period: str


class ChartManager:
    """
    图表管理器
    负责K线图表、成交量图表和技术指标的显示管理
    """
    
    def __init__(self, analysis_data_manager):
        """初始化图表管理器"""
        self.analysis_data_manager = analysis_data_manager
        self.logger = get_logger(__name__)
        
        # 图表显示状态
        self.current_chart_data: Optional[ChartData] = None
        self.display_range: ChartRange = ChartRange(0, 50, 0)
        
        # 图表交互状态
        self.is_dragging: bool = False
        self.zoom_level: float = 1.0
        self.scroll_position: int = 0
        
        # 技术指标显示配置
        self.show_ma_lines: Dict[str, bool] = {
            'ma5': True,
            'ma10': True,
            'ma20': True,
            'ma60': False
        }
        self.show_volume: bool = True
        self.show_macd: bool = False
        self.show_rsi: bool = False
        
        self.logger.info("ChartManager 初始化完成")
    
    async def update_chart_data(self, stock_code: str, time_period: str) -> bool:
        """更新图表数据"""
        try:
            # 从分析数据管理器获取数据
            analysis_data = self.analysis_data_manager.get_current_analysis_data()
            if not analysis_data or analysis_data.stock_code != stock_code:
                self.logger.warning(f"没有找到股票 {stock_code} 的分析数据")
                return False
            
            kline_data = analysis_data.kline_data
            technical_indicators = analysis_data.technical_indicators
            
            if not kline_data:
                self.logger.warning(f"股票 {stock_code} 没有K线数据")
                return False
            
            # 计算显示范围
            total_bars = len(kline_data)
            display_bars = min(CHART_DISPLAY_CONFIG['max_display_bars'], total_bars)
            
            # 默认显示最新的数据
            end_index = total_bars
            start_index = max(0, end_index - display_bars)
            
            self.display_range = ChartRange(start_index, end_index, total_bars)
            
            # 创建图表数据
            self.current_chart_data = ChartData(
                kline_data=kline_data,
                technical_indicators=technical_indicators,
                display_range=self.display_range,
                time_period=time_period
            )
            
            self.logger.info(f"图表数据更新完成: {stock_code}, 周期: {time_period}, "
                           f"数据量: {total_bars}, 显示范围: {start_index}-{end_index}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"更新图表数据失败: {e}")
            return False
    
    def get_display_kline_data(self) -> List[KLineData]:
        """获取当前显示范围的K线数据"""
        if not self.current_chart_data:
            return []
        
        start = self.display_range.start_index
        end = self.display_range.end_index
        
        return self.current_chart_data.kline_data[start:end]
    
    def get_chart_display_info(self) -> Dict[str, Any]:
        """获取图表显示信息"""
        if not self.current_chart_data:
            return {}
        
        display_data = self.get_display_kline_data()
        if not display_data:
            return {}
        
        # 计算价格范围
        high_prices = [k.high for k in display_data]
        low_prices = [k.low for k in display_data]
        
        price_high = max(high_prices) if high_prices else 0
        price_low = min(low_prices) if low_prices else 0
        price_range = price_high - price_low
        
        # 计算成交量范围
        volumes = [k.volume for k in display_data]
        volume_max = max(volumes) if volumes else 0
        
        # 获取最新数据
        latest_kline = display_data[-1] if display_data else None
        
        return {
            'data_count': len(display_data),
            'price_high': price_high,
            'price_low': price_low,
            'price_range': price_range,
            'volume_max': volume_max,
            'latest_price': latest_kline.close if latest_kline else 0,
            'latest_volume': latest_kline.volume if latest_kline else 0,
            'latest_time': latest_kline.time_key if latest_kline else '',
            'time_period': self.current_chart_data.time_period,
            'display_range': f"{self.display_range.start_index + 1}-{self.display_range.end_index}/{self.display_range.total_bars}"
        }
    
    def scroll_chart(self, direction: str, step: int = None) -> bool:
        """滚动图表"""
        try:
            if not self.current_chart_data:
                return False
            
            if step is None:
                step = CHART_DISPLAY_CONFIG['scroll_step']
            
            current_range = self.display_range
            display_bars = current_range.end_index - current_range.start_index
            
            if direction == 'left':  # 向左滚动，显示更早的数据
                new_start = max(0, current_range.start_index - step)
                new_end = new_start + display_bars
                
            elif direction == 'right':  # 向右滚动，显示更新的数据
                new_end = min(current_range.total_bars, current_range.end_index + step)
                new_start = new_end - display_bars
                
            else:
                self.logger.warning(f"不支持的滚动方向: {direction}")
                return False
            
            # 更新显示范围
            self.display_range = ChartRange(new_start, new_end, current_range.total_bars)
            
            self.logger.debug(f"图表滚动: {direction}, 新范围: {new_start}-{new_end}")
            return True
            
        except Exception as e:
            self.logger.error(f"图表滚动失败: {e}")
            return False
    
    def zoom_chart(self, zoom_in: bool, zoom_factor: float = 1.2) -> bool:
        """缩放图表"""
        try:
            if not self.current_chart_data:
                return False
            
            current_range = self.display_range
            current_bars = current_range.end_index - current_range.start_index
            
            if zoom_in:
                # 放大：显示更少的K线
                new_bars = max(CHART_DISPLAY_CONFIG['min_display_bars'], 
                              int(current_bars / zoom_factor))
            else:
                # 缩小：显示更多的K线
                new_bars = min(CHART_DISPLAY_CONFIG['max_display_bars'],
                              int(current_bars * zoom_factor))
                new_bars = min(new_bars, current_range.total_bars)
            
            # 保持中心位置不变
            center = (current_range.start_index + current_range.end_index) // 2
            new_start = max(0, center - new_bars // 2)
            new_end = min(current_range.total_bars, new_start + new_bars)
            
            # 调整起始位置以确保结束位置正确
            if new_end - new_start < new_bars:
                new_start = max(0, new_end - new_bars)
            
            self.display_range = ChartRange(new_start, new_end, current_range.total_bars)
            
            self.logger.debug(f"图表缩放: {'放大' if zoom_in else '缩小'}, "
                            f"显示K线数: {current_bars} -> {new_bars}")
            return True
            
        except Exception as e:
            self.logger.error(f"图表缩放失败: {e}")
            return False
    
    def jump_to_latest(self) -> bool:
        """跳转到最新数据"""
        try:
            if not self.current_chart_data:
                return False
            
            current_range = self.display_range
            display_bars = current_range.end_index - current_range.start_index
            
            new_end = current_range.total_bars
            new_start = max(0, new_end - display_bars)
            
            self.display_range = ChartRange(new_start, new_end, current_range.total_bars)
            
            self.logger.debug("图表跳转到最新数据")
            return True
            
        except Exception as e:
            self.logger.error(f"跳转到最新数据失败: {e}")
            return False
    
    def jump_to_earliest(self) -> bool:
        """跳转到最早数据"""
        try:
            if not self.current_chart_data:
                return False
            
            current_range = self.display_range
            display_bars = current_range.end_index - current_range.start_index
            
            new_start = 0
            new_end = min(display_bars, current_range.total_bars)
            
            self.display_range = ChartRange(new_start, new_end, current_range.total_bars)
            
            self.logger.debug("图表跳转到最早数据")
            return True
            
        except Exception as e:
            self.logger.error(f"跳转到最早数据失败: {e}")
            return False
    
    def toggle_ma_line(self, ma_type: str) -> bool:
        """切换均线显示状态"""
        try:
            if ma_type not in self.show_ma_lines:
                self.logger.warning(f"不支持的均线类型: {ma_type}")
                return False
            
            self.show_ma_lines[ma_type] = not self.show_ma_lines[ma_type]
            
            self.logger.debug(f"均线 {ma_type} 显示状态: {self.show_ma_lines[ma_type]}")
            return True
            
        except Exception as e:
            self.logger.error(f"切换均线显示失败: {e}")
            return False
    
    def toggle_volume_display(self) -> bool:
        """切换成交量显示状态"""
        try:
            self.show_volume = not self.show_volume
            self.logger.debug(f"成交量显示状态: {self.show_volume}")
            return True
            
        except Exception as e:
            self.logger.error(f"切换成交量显示失败: {e}")
            return False
    
    def toggle_indicator_display(self, indicator_type: str) -> bool:
        """切换技术指标显示状态"""
        try:
            if indicator_type == 'macd':
                self.show_macd = not self.show_macd
                self.logger.debug(f"MACD显示状态: {self.show_macd}")
            elif indicator_type == 'rsi':
                self.show_rsi = not self.show_rsi
                self.logger.debug(f"RSI显示状态: {self.show_rsi}")
            else:
                self.logger.warning(f"不支持的指标类型: {indicator_type}")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"切换指标显示失败: {e}")
            return False
    
    def get_ma_data(self, ma_type: str) -> List[float]:
        """获取均线数据"""
        try:
            if not self.current_chart_data or ma_type not in self.show_ma_lines:
                return []
            
            if not self.show_ma_lines[ma_type]:
                return []
            
            # 这里应该从技术指标数据中获取均线数据
            # 由于当前的technical_indicators只有最新值，这里返回空列表
            # 实际实现中需要扩展analysis_data_manager来计算历史均线数据
            return []
            
        except Exception as e:
            self.logger.error(f"获取均线数据失败: {e}")
            return []
    
    def get_volume_data(self) -> List[int]:
        """获取成交量数据"""
        try:
            if not self.current_chart_data or not self.show_volume:
                return []
            
            display_data = self.get_display_kline_data()
            return [k.volume for k in display_data]
            
        except Exception as e:
            self.logger.error(f"获取成交量数据失败: {e}")
            return []
    
    def get_chart_text_display(self) -> List[str]:
        """获取图表的文本显示内容"""
        try:
            if not self.current_chart_data:
                return ["没有图表数据"]
            
            display_info = self.get_chart_display_info()
            display_data = self.get_display_kline_data()
            
            if not display_data:
                return ["没有可显示的K线数据"]
            
            lines = []
            
            # 图表标题
            lines.append(f"K线图表 - 周期: {display_info['time_period']}")
            lines.append(f"显示范围: {display_info['display_range']}")
            lines.append("")
            
            # 价格信息
            lines.append(f"价格区间: {display_info['price_low']:.2f} - {display_info['price_high']:.2f}")
            lines.append(f"最新价格: {display_info['latest_price']:.2f}")
            lines.append(f"最大成交量: {display_info['volume_max']:,}")
            lines.append("")
            
            # 技术指标信息
            if self.current_chart_data.technical_indicators:
                indicators = self.current_chart_data.technical_indicators
                lines.append("技术指标:")
                
                for ma_type in ['ma5', 'ma10', 'ma20', 'ma60']:
                    if self.show_ma_lines.get(ma_type, False) and ma_type in indicators:
                        lines.append(f"  {ma_type.upper()}: {indicators[ma_type]:.2f}")
                
                if 'rsi' in indicators:
                    lines.append(f"  RSI: {indicators['rsi']:.2f}")
                
                if 'macd' in indicators:
                    macd = indicators['macd']
                    lines.append(f"  MACD: DIF={macd.get('dif', 0):.3f}, "
                               f"DEA={macd.get('dea', 0):.3f}")
            
            lines.append("")
            
            # 图表控制提示
            lines.append("图表控制:")
            lines.append("  ←→ 滚动图表")
            lines.append("  +/- 缩放图表")
            lines.append("  Home/End 跳转到最早/最新")
            lines.append("  M 切换均线显示")
            lines.append("  V 切换成交量显示")
            
            return lines
            
        except Exception as e:
            self.logger.error(f"生成图表文本显示失败: {e}")
            return [f"图表显示错误: {e}"]
    
    def handle_chart_key_event(self, key: str) -> bool:
        """处理图表相关的按键事件"""
        try:
            key = key.lower()
            
            if key == 'left':
                return self.scroll_chart('left')
            elif key == 'right':
                return self.scroll_chart('right')
            elif key == 'plus' or key == '=':
                return self.zoom_chart(True)
            elif key == 'minus' or key == '-':
                return self.zoom_chart(False)
            elif key == 'home':
                return self.jump_to_earliest()
            elif key == 'end':
                return self.jump_to_latest()
            elif key == 'v':
                return self.toggle_volume_display()
            elif key == 'm':
                # 循环切换均线显示
                ma_types = ['ma5', 'ma10', 'ma20', 'ma60']
                for ma_type in ma_types:
                    self.toggle_ma_line(ma_type)
                return True
            elif key == 'i':
                return self.toggle_indicator_display('macd')
            elif key == 'r':
                return self.toggle_indicator_display('rsi')
            else:
                return False
                
        except Exception as e:
            self.logger.error(f"处理图表按键事件失败: {e}")
            return False
    
    def get_chart_status(self) -> Dict[str, Any]:
        """获取图表状态信息"""
        return {
            'has_data': self.current_chart_data is not None,
            'display_range': self.display_range.__dict__ if self.display_range else None,
            'zoom_level': self.zoom_level,
            'show_volume': self.show_volume,
            'show_ma_lines': self.show_ma_lines.copy(),
            'show_macd': self.show_macd,
            'show_rsi': self.show_rsi,
        }
    
    async def cleanup(self):
        """清理图表管理器"""
        try:
            self.current_chart_data = None
            self.display_range = ChartRange(0, 50, 0)
            self.is_dragging = False
            self.zoom_level = 1.0
            self.scroll_position = 0
            
            self.logger.info("ChartManager 清理完成")
            
        except Exception as e:
            self.logger.error(f"ChartManager 清理失败: {e}")