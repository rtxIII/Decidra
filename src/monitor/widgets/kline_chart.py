"""
K线图和成交量图表组件
基于 textual_plotext 实现专业的股票K线图和成交量显示
"""

from typing import List, Optional
from dataclasses import dataclass

from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import Static
from textual.reactive import reactive
from textual.binding import Binding
from textual_plotext import PlotextPlot

from base.futu_class import KLineData
from utils.global_vars import get_logger

@dataclass
class ChartConfig:
    """图表配置"""
    show_volume: bool = True
    chart_height: int = 20
    volume_height: int = 12
    theme: str = "dark"
    title_color: str = "bright_blue"
    up_color: str = "green"
    down_color: str = "red"


class KLineChartWidget(Container):
    """K线图和成交量组合widget"""
    
    DEFAULT_CSS = """
    KLineChartWidget {
        height: 1fr;
        border: solid $accent;
        border-title-color: $text;
        border-title-background: $surface;
        layout: vertical;
    }
    
    KLineChartWidget .chart-container {
        height: 2fr;
    }
    
    KLineChartWidget .volume-container {
        height: 1fr;
        min-height: 8;
        margin-top: 1;
    }
    
    KLineChartWidget .info-bar {
        height: 3;
        background: $surface;
        border: solid $accent;
        padding: 0 1;
        content-align: center middle;
    }
    """
    
    BINDINGS = [
        Binding("left", "scroll_left", "向左滚动", show=False),
        Binding("right", "scroll_right", "向右滚动", show=False),
        Binding("up", "zoom_in", "放大", show=False),
        Binding("down", "zoom_out", "缩小", show=False),
        Binding("home", "jump_start", "跳转到开始", show=False),
        Binding("end", "jump_end", "跳转到结束", show=False),
        Binding("v", "toggle_volume", "切换成交量显示", show=False),
    ]
    
    # 响应式属性
    current_data = reactive(None)
    display_start = reactive(0)
    display_count = reactive(50)
    show_volume = reactive(True)
    
    def __init__(
        self,
        stock_code: str = "",
        time_period: str = "D",
        config: Optional[ChartConfig] = None,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.stock_code = stock_code
        self.time_period = time_period
        self.config = config or ChartConfig()
        
        # 数据缓存
        self.kline_data: List[KLineData] = []
        self.data_length = 0
        
        # 图表状态
        self.display_start = 0
        self.display_count = min(50, len(self.kline_data)) if self.kline_data else 50
        
        self.border_title = f"K线图 - {stock_code} ({time_period})"
        self.logger = get_logger(__name__)
    
    def compose(self) -> ComposeResult:
        """组合K线图表组件"""
        # 信息栏
        #with Container(classes="info-bar"):
        #    yield Static(
        #        f"股票: {self.stock_code} | 周期: {self.time_period} | "
        #        f"显示: {self.display_count}根K线 | "
        #        f"[dim]方向键:滚动 上下:缩放 V:成交量 Home/End:跳转[/dim]",
        #        id="chart_info"
        #    )
        
        # K线图容器
        with Container(classes="chart-container"):
            yield PlotextPlot(id="kline_plot")
        
        # 成交量图容器
        if self.config.show_volume:
            with Container(classes="volume-container"):
                yield PlotextPlot(id="volume_plot")
    
    def update_data(self, kline_data: List[KLineData]) -> None:
        """更新K线数据"""
        self.kline_data = kline_data
        self.data_length = len(kline_data)
        
        # 调整显示范围
        if self.data_length > 0:
            self.display_count = min(self.display_count, self.data_length)
            self.display_start = max(0, min(self.display_start, self.data_length - self.display_count))
        
        self._update_chart()
        self._update_info_bar()
    
    def _update_chart(self) -> None:
        """更新图表显示"""
        if not self.kline_data:
            return
        
        # 获取显示数据范围
        end_idx = min(self.display_start + self.display_count, self.data_length)
        display_data = self.kline_data[self.display_start:end_idx]
        
        if not display_data:
            return
        
        # 准备K线数据
        self._draw_kline_chart(display_data)
        
        # 绘制成交量图（如果启用）
        if self.config.show_volume:
            try:
                volume_plot = self.query_one("#volume_plot", PlotextPlot)
                if volume_plot:
                    self._draw_volume_chart(display_data)
                else:
                    self.logger.warning("[DEBUG] volume_plot 组件为None")
            except Exception as e:
                self.logger.error(f"[DEBUG] 成交量图组件查询或绘制失败: {e}")
                pass  # 成交量图组件不存在时忽略
    
    def _draw_kline_chart(self, data: List[KLineData]) -> None:
        """绘制K线图"""
        
        kline_plot = self.query_one("#kline_plot", PlotextPlot)
        if not kline_plot:
            self.logger.error("[DEBUG] kline_plot 组件未找到")
            return
        
        plt = kline_plot.plt
        
        # 清空图表
        plt.clf()
        
        # 设置主题
        plt.theme(self.config.theme)
        
        # 使用连续索引而不是真实日期，避免非交易日产生空隙
        x_indices = list(range(len(data)))
        dates = [item.time_key for item in data]
        ohlc_data = {
            'Open': [float(item.open) for item in data],
            'High': [float(item.high) for item in data],
            'Low': [float(item.low) for item in data],
            'Close': [float(item.close) for item in data]
        }
        
        #self.logger.debug(f"[DEBUG] 绘制{len(data)}根K线, 第一条OHLC: O={ohlc_data['Open'][0] if ohlc_data['Open'] else 'None'}, "
        #      f"H={ohlc_data['High'][0] if ohlc_data['High'] else 'None'}, "
        #      f"L={ohlc_data['Low'][0] if ohlc_data['Low'] else 'None'}, "
        #      f"C={ohlc_data['Close'][0] if ohlc_data['Close'] else 'None'}")
        
        try:
            # 绘制K线图 - 使用连续索引作为X轴
            plt.candlestick(x_indices, ohlc_data, colors = ['red', 'green'])
            
            # 设置X轴标签 - 选择性显示日期，避免过密
            if len(data) > 10:
                # 选择显示的日期标签索引，确保不会太密集
                step = max(1, len(data) // 8)  # 最多显示8个标签
                label_indices = list(range(0, len(data), step))
                if label_indices[-1] != len(data) - 1:
                    label_indices.append(len(data) - 1)  # 确保显示最后一个日期
                
                x_labels = [dates[i] for i in label_indices]
                # 简化日期显示格式
                x_labels_short = [date.split(' ')[0] for date in x_labels]  # 只显示日期部分
                plt.xticks(label_indices, x_labels_short)
            else:
                # 数据少时显示所有日期
                x_labels_short = [date.split(' ')[0] for date in dates]
                plt.xticks(x_indices, x_labels_short)
            
            # 设置图表标题和标签
            plt.title(f"{self.stock_code} K线图 ({self.time_period})")
            plt.xlabel("时间")
            plt.ylabel("价格")
            
            # 设置图表尺寸
            plt.plotsize(width=None, height=self.config.chart_height)
            
        except Exception as e:
            self.logger.error(f"[DEBUG] K线图绘制失败: {e}")
            # 如果candlestick失败，使用线图作为后备
            try:
                plt.plot(x_indices, ohlc_data['Close'], label="收盘价", color="blue")
                plt.title(f"{self.stock_code} 价格走势 ({self.time_period})")
                plt.xlabel("时间")
                plt.ylabel("价格")
                # 设置X轴标签
                if len(data) > 10:
                    step = max(1, len(data) // 8)
                    label_indices = list(range(0, len(data), step))
                    x_labels_short = [dates[i].split(' ')[0] for i in label_indices]
                    plt.xticks(label_indices, x_labels_short)
                else:
                    x_labels_short = [date.split(' ')[0] for date in dates]
                    plt.xticks(x_indices, x_labels_short)
            except Exception as fallback_error:
                self.logger.error(f"[DEBUG] 后备线图绘制也失败: {fallback_error}")
        
        # 强制刷新PlotextPlot组件以确保图表重新渲染
        try:
            kline_plot.refresh()
        except Exception as e:
            self.logger.error(f"[DEBUG] 强制刷新K线图失败: {e}")
            
    def _draw_volume_chart(self, data: List[KLineData]) -> None:
        """绘制成交量图"""
        
        volume_plot = self.query_one("#volume_plot", PlotextPlot)
        if not volume_plot:
            self.logger.error("[DEBUG] volume_plot 组件未找到")
            return
        
        plt = volume_plot.plt
        
        # 清空图表
        plt.clf()
        
        # 设置主题
        plt.theme(self.config.theme)
        
        # 使用连续索引而不是真实日期，与K线图保持一致
        x_indices = list(range(len(data)))
        dates = [item.time_key for item in data]
        volumes = [int(item.volume) for item in data]
        colors = []
        
        # 根据涨跌确定颜色
        for item in data:
            if item.close > item.open:  # 涨日
                colors.append("red")
            elif item.close < item.open:  # 跌日
                colors.append("green")
            else:  # 平盘
                colors.append("yellow")
        
        try:
            # 再分别绘制不同颜色的成交量条（使用连续索引）
            for color_type in ["red", "green", "yellow"]:
                filtered_indices = []
                filtered_volumes = []
                
                for i, color in enumerate(colors):
                    if color == color_type:
                        filtered_indices.append(x_indices[i])
                        filtered_volumes.append(volumes[i])
                
                if filtered_indices and filtered_volumes:
                    plt.bar(filtered_indices, filtered_volumes, color=color_type, width=0.2)
            
            # 设置X轴标签与K线图一致
            if len(data) > 10:
                step = max(1, len(data) // 8)  # 最多显示8个标签
                label_indices = list(range(0, len(data), step))
                if label_indices[-1] != len(data) - 1:
                    label_indices.append(len(data) - 1)
                
                x_labels_short = [dates[i].split(' ')[0] for i in label_indices]
                plt.xticks(label_indices, x_labels_short)
            else:
                x_labels_short = [date.split(' ')[0] for date in dates]
                plt.xticks(x_indices, x_labels_short)
            
        except Exception as e:
            self.logger.error(f"成交量图绘制失败: {e}")

            
        # 设置图表标题和标签
        plt.title("成交量")
        plt.xlabel("时间")
        plt.ylabel("成交量")
        
        # 设置图表尺寸
        plt.plotsize(width=None, height=self.config.volume_height)
        
        # 强制刷新PlotextPlot组件以确保图表重新渲染
        try:
            volume_plot.refresh()
        except Exception as e:
            self.logger.error(f"强制刷新成交量图失败: {e}")
            
    def _update_info_bar(self) -> None:
        """更新信息栏"""
        try:
            info_widget = self.query_one("#chart_info", Static)
        except:
            return
        if info_widget and self.kline_data:
            current_data = self.kline_data[min(self.display_start + self.display_count - 1, len(self.kline_data) - 1)]
            info_text = (
                f"股票: {self.stock_code} | 周期: {self.time_period} | "
                f"显示: {self.display_count}根K线 | "
                f"最新价: {current_data.close:.2f} | "
                f"时间: {current_data.time_key} | "
                f"[dim]方向键:滚动 上下:缩放 V:成交量 Home/End:跳转[/dim]"
            )
            info_widget.update(info_text)
    
    def action_scroll_left(self) -> None:
        """向左滚动"""
        if self.display_start > 0:
            self.display_start = max(0, self.display_start - 5)
            self._update_chart()
            self._update_info_bar()
    
    def action_scroll_right(self) -> None:
        """向右滚动"""
        max_start = max(0, self.data_length - self.display_count)
        if self.display_start < max_start:
            self.display_start = min(max_start, self.display_start + 5)
            self._update_chart()
            self._update_info_bar()
    
    def action_zoom_in(self) -> None:
        """放大（显示更少K线）"""
        if self.display_count > 10:
            old_center = self.display_start + self.display_count // 2
            self.display_count = max(10, self.display_count - 5)
            self.display_start = max(0, old_center - self.display_count // 2)
            self._update_chart()
            self._update_info_bar()
    
    def action_zoom_out(self) -> None:
        """缩小（显示更多K线）"""
        if self.display_count < self.data_length:
            old_center = self.display_start + self.display_count // 2
            self.display_count = min(self.data_length, self.display_count + 5)
            self.display_start = max(0, old_center - self.display_count // 2)
            if self.display_start + self.display_count > self.data_length:
                self.display_start = max(0, self.data_length - self.display_count)
            self._update_chart()
            self._update_info_bar()
    
    def action_jump_start(self) -> None:
        """跳转到开始"""
        self.display_start = 0
        self._update_chart()
        self._update_info_bar()
    
    def action_jump_end(self) -> None:
        """跳转到结束"""
        self.display_start = max(0, self.data_length - self.display_count)
        self._update_chart()
        self._update_info_bar()
    
    def action_toggle_volume(self) -> None:
        """切换成交量显示"""
        self.config.show_volume = not self.config.show_volume
        self.show_volume = self.config.show_volume
        # 需要重新compose来显示/隐藏成交量图
        # 这里可以通过发送消息给父组件来重新加载
        self._update_chart()
    
    def set_stock(self, stock_code: str, time_period: str = "D") -> None:
        """设置股票代码和时间周期"""
        self.stock_code = stock_code
        self.time_period = time_period
        self.border_title = f"K线图 - {stock_code} ({time_period})"
        self._update_info_bar()


class SimpleKLineWidget(PlotextPlot):
    """简化版K线图widget - 直接继承PlotextPlot"""
    
    def __init__(self, stock_code: str = "", **kwargs):
        super().__init__(**kwargs)
        self.stock_code = stock_code
        self.kline_data: List[KLineData] = []
    
    def update_kline_data(self, kline_data: List[KLineData]) -> None:
        """更新K线数据并重绘"""
        self.kline_data = kline_data
        self.draw_chart()
    
    def draw_chart(self, count: int = 200) -> None:
        """绘制K线图"""
        if not self.kline_data:
            return
        
        plt = self.plt
        plt.clf()
        plt.theme("dark")
        
        # 准备数据 - 使用连续索引避免空隙
        chart_data = self.kline_data[-count:]
        x_indices = list(range(len(chart_data)))
        dates = [item.time_key for item in chart_data]  
        ohlc_data = {
            'Open': [float(item.open) for item in chart_data],
            'High': [float(item.high) for item in chart_data],
            'Low': [float(item.low) for item in chart_data],
            'Close': [float(item.close) for item in chart_data]
        }
        
        try:
            # 绘制K线图 - 使用连续索引
            plt.candlestick(x_indices, ohlc_data)
            
            # 设置X轴标签
            if len(chart_data) > 10:
                step = max(1, len(chart_data) // 8)
                label_indices = list(range(0, len(chart_data), step))
                if label_indices[-1] != len(chart_data) - 1:
                    label_indices.append(len(chart_data) - 1)
                
                x_labels_short = [dates[i].split(' ')[0] for i in label_indices]
                plt.xticks(label_indices, x_labels_short)
            else:
                x_labels_short = [date.split(' ')[0] for date in dates]
                plt.xticks(x_indices, x_labels_short)
            
            plt.title(f"{self.stock_code} K线图")
            plt.xlabel("时间")
            plt.ylabel("价格")
        except Exception:
            # 后备方案：使用线图
            try:
                plt.plot(x_indices, ohlc_data['Close'], label="收盘价", color="blue")
                plt.title(f"{self.stock_code} 价格走势")
                plt.xlabel("时间")  
                plt.ylabel("价格")
                # 设置X轴标签
                if len(chart_data) > 10:
                    step = max(1, len(chart_data) // 8)
                    label_indices = list(range(0, len(chart_data), step))
                    x_labels_short = [dates[i].split(' ')[0] for i in label_indices]
                    plt.xticks(label_indices, x_labels_short)
                else:
                    x_labels_short = [date.split(' ')[0] for date in dates]
                    plt.xticks(x_indices, x_labels_short)
            except Exception:
                pass
        
        # 强制刷新PlotextPlot组件以确保图表重新渲染
        try:
            self.refresh()
        except Exception:
            pass