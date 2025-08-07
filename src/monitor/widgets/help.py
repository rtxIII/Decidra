import webbrowser
from importlib.metadata import version

from rich.text import Text

from textual import on
from textual.app import ComposeResult
from textual.containers import Center, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Static, Markdown, Footer

# 项目相关链接
TEXTUAL_LINK = "https://www.textualize.io/"
FUTU_API_LINK = "https://www.futunn.com/download/openAPI"
DECIDRA_REPOSITORY_LINK = "https://github.com/your-username/Decidra"  # 请替换为实际仓库地址

HELP_MD = """
Decidra 是一个基于 Python 的智能股票监控决策系统，使用富途 OpenAPI 提供实时行情数据。

基于 [Textual](https://www.textualize.io/) 框架构建的终端用户界面。

---

### 主要功能

- **实时股票监控**: 监控多只股票的实时价格、涨跌幅、成交量
- **技术指标分析**: 支持 MA、RSI、MACD 等技术指标计算
- **用户分组管理**: 支持股票分组，便于分类监控
- **智能分析**: 提供 AI 驱动的股票分析和建议
- **多标签界面**: 主监控界面和详细分析界面

---

### 键盘导航

#### 基本操作
- `h` 显示此帮助界面
- `q` 或 `ctrl+c` 退出应用程序
- `escape` 返回主界面/关闭对话框
- `tab` 在标签页之间切换

#### 股票管理
- `a` 添加股票到监控列表
- `d` 删除当前选中的股票
- `r` 手动刷新股票数据

#### 界面导航
- `↑` `↓` 或 `方向键` 在股票列表中上下选择
- `k` 分组列表向上移动
- `l` 分组列表向下移动
- `space` 智能操作：在股票列表时进入分析界面，在分组列表时选择分组

#### 分析界面导航
- `z` 返回主界面
- `x` 向左切换标签页
- `c` 向右切换标签页

---

### 使用方法

#### 启动应用

首先确保 FutuOpenD 网关程序正在运行：

```bash
# 配置富途API连接
python cli.py futu config --host 127.0.0.1 --port 11111

# 测试连接
python cli.py futu test-connection

# 启动监控界面
python monitor_app.py
```

#### 股票管理

**添加股票**:
1. 按 `a` 键打开添加股票对话框
2. 输入股票代码（如：HK.00700, US.AAPL）
3. 按 `Enter` 确认添加

**删除股票**:
1. 选择要删除的股票行
2. 按 `d` 键
3. 在确认对话框中确认删除

#### 分组功能

**选择分组**:
- 使用 `k` 和 `l` 键在分组列表中导航
- 按 `space` 键选择分组作为主监控列表
- 分组会显示包含的股票数量和股票列表预览

#### 分析界面

**进入分析模式**:
1. 选择一只股票
2. 按 `Enter` 键进入分析界面
3. 查看 K线图表和 AI 分析报告
4. 按 `Escape` 返回主界面

---

### 界面说明

#### 主界面标签页
- **股票列表**: 显示所有监控股票的实时数据
  - 股票代码、名称、当前价格
  - 涨跌幅（绿色上涨，红色下跌）
  - 成交量和更新时间
- **用户分组**: 显示用户自定义的股票分组
- **状态栏**: 显示连接状态、市场状态、刷新模式

#### 分析界面标签页
- **K线图表**: 显示股票的价格走势图
- **技术指标**: MA、RSI、MACD 等指标数值
- **AI分析**: 智能分析报告和交易建议

---

### 数据源

- **富途 OpenAPI**: 提供实时行情和历史数据
- **支持市场**: 港股(HK)、美股(US)、A股(SH/SZ)
- **数据频率**: 实时更新（5秒间隔）

---

### 技术架构

- **UI框架**: Textual - Python 终端用户界面
- **数据源**: 富途 OpenAPI 9.3+
- **异步处理**: asyncio + ThreadPoolExecutor
- **技术指标**: 自定义算法实现

---

### 故障排除

#### 连接问题
- 确保 FutuOpenD 程序正在运行
- 检查网络连接和防火墙设置
- 验证富途账户权限

#### 数据问题
- 按 `r` 键手动刷新数据
- 检查股票代码格式是否正确
- 确认市场交易时间

---

### 支持的股票代码格式

- **港股**: HK.00700 (腾讯控股)
- **美股**: US.AAPL (苹果公司)
- **A股**: SH.000001 (上证指数), SZ.000001 (平安银行)

---

### 许可证

MIT License

Copyright (c) 2024 Decidra Team

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""

TITLE = rf"""
 ____           _     _           
|  _ \  ___  __(_) __| |_ __ __ _ 
| | | |/ _ \/ _` |/ _` | '__/ _` |
| |_| |  __/ (_| | (_| | | | (_| |
|____/ \___|\__,_|\__,_|_|  \__,_|
                                  
    智能股票监控决策系统
    Built with Textual
"""


COLORS = [
    "#ff0066",  # 红色 - 代表股市的活力
    "#ff3366",  # 亮红
    "#ff6699",  # 粉红
    "#ff99cc",  # 浅粉
    "#00cc66",  # 绿色 - 代表上涨
    "#33dd77",  # 亮绿
    "#66ee88",  # 浅绿
    "#0066ff",  # 蓝色 - 代表稳定
    "#3377ff",  # 亮蓝
    "#6699ff",  # 浅蓝
    "#ffcc00",  # 黄色 - 代表警示
    "#ffdd33",  # 亮黄
]


def get_title() -> Text:
    """获取带有彩虹效果的标题"""
    lines = TITLE.splitlines(keepends=True)
    return Text.assemble(*zip(lines, COLORS))


class HelpScreen(ModalScreen):
    """Decidra股票监控系统帮助界面"""

    CSS = """
    HelpScreen VerticalScroll {
        background: $surface;
        margin: 4 8;        
        border: heavy $accent;        
        height: 1fr;        
        .title {
            width: auto;
        }
        scrollbar-gutter: stable;
        Markdown {
            margin:0 2;
        }        
        Markdown .code_inline {
            background: $primary-darken-1;
            text-style: bold;
        }
    }    
    """

    BINDINGS = [
        ("escape", "dismiss"),
        ("f", f"go({FUTU_API_LINK!r})", "富途API"),
        ("t", f"go({TEXTUAL_LINK!r})", "Textual"),
        ("r", f"go({DECIDRA_REPOSITORY_LINK!r})", "Repository"),
    ]

    def compose(self) -> ComposeResult:
        yield Footer()
        with VerticalScroll() as vertical_scroll:
            with Center():
                yield Static(get_title(), classes="title")
            yield Markdown(HELP_MD)
        vertical_scroll.border_title = "Decidra 帮助"
        vertical_scroll.border_subtitle = "ESCAPE 关闭帮助"

    @on(Markdown.LinkClicked)
    def on_markdown_link_clicked(self, event: Markdown.LinkClicked) -> None:
        self.action_go(event.href)

    def action_go(self, href: str) -> None:
        self.notify(f"正在打开 {href}", title="链接")
        webbrowser.open(href)