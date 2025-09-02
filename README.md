# Decidra - 智能交易决策系统

[![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)](https://python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Build Status](https://img.shields.io/badge/build-passing-brightgreen.svg)](#)

**Intelligent Trading Decision System** - 基于富途OpenAPI的Python股票交易分析平台

## 项目简介

Decidra 是一个现代化的智能交易决策系统，集成了富途 OpenAPI、AI分析引擎和终端监控界面，提供完整的股票交易分析解决方案。

## ✨ 主要特性

- 🔌 **富途API集成**: 完整封装富途OpenAPI，支持港股、美股、A股实时数据
- 📊 **智能监控界面**: 基于Textual框架的现代化终端UI，实时股票监控
- 🤖 **AI分析引擎**: 集成Claude AI，提供智能股票分析和建议
- 💹 **技术指标计算**: 内置MA、RSI、MACD等多种技术指标
- 📈 **多数据源支持**: 支持Yahoo Finance、Tushare、Akshare等数据源
- 🧪 **完整测试覆盖**: 145+个Python文件，完善的测试体系
- 🖥️ **现代CLI工具**: 功能完备的命令行界面，支持配置管理和数据下载
- 🎯 **策略引擎**: 支持自定义交易策略和过滤器

## 🔧 环境要求

- **Python**: 3.8+ (推荐 3.10+)
- **FutuOpenD**: 富途网关程序 (用于实时数据)
- **富途证券账户**: 用于交易功能 (可选)

## 📦 安装方式

### 方式一：从源码安装（推荐）

```bash
# 1. 克隆项目
git clone https://github.com/rtxIII/decidra.git
cd decidra

# 2. 安装项目（包含所有依赖）
pip install -e .

# 3. 安装开发依赖（可选）
pip install -e ".[dev]"
```

### 方式二：传统方式

```bash
# 1. 克隆项目
git clone https://github.com/rtxIII/decidra.git
cd decidra

# 2. 安装依赖
pip install -r requirements.txt
```

### 验证安装

```bash
# 验证CLI工具
decidra --help

# 或使用传统方式
python src/cli.py --help
```

## 🚀 快速开始

### 1. 启动监控界面

```bash
# 启动股票监控界面
decidra monitor start

```

### 2. 配置富途API

```bash
# 配置富途API连接
decidra futu config --host 127.0.0.1 --port 11111

# 测试连接
decidra futu test-connection
```


## 🖥️ 监控界面

基于Textual框架的现代化终端界面：

```bash
# 启动完整监控界面
decidra monitor start

# 快捷键:
# - q: 退出程序
# - r: 手动刷新数据  
# - a: 添加股票
# - d: 删除股票
# - Enter/Space: 进入分析界面
# - Tab: 切换标签页
```


## 🏗️ 项目架构

```
Decidra/
├── 📁 src/                          # 源代码目录
│   ├── 📁 api/                      # API接口层
│   │   └── futu.py                  # 富途API封装
│   ├── 📁 monitor/                  # 监控界面模块
│   │   ├── 📁 analysis/             # 分析功能
│   │   ├── 📁 main/                 # 核心业务逻辑
│   │   ├── 📁 manager/              # 管理器组件
│   │   ├── 📁 widgets/              # UI组件库
│   │   └── ui.py                    # 主界面入口
│   ├── 📁 modules/                  # 功能模块
│   │   ├── 📁 ai/                   # AI分析模块
│   │   └── yahoo_data.py            # Yahoo Finance接口
│   ├── 📁 filters/                  # 交易过滤器
│   ├── 📁 strategies/               # 交易策略
│   ├── 📁 utils/                    # 工具函数
│   ├── 📁 tests/                    # 测试用例 (145+ 文件)
│   └── cli.py                       # 命令行入口
├── 📄 pyproject.toml                # 现代Python项目配置
├── 📄 requirements.txt              # 依赖清单
├── 📄 .pre-commit-config.yaml       # 代码质量控制
└── 📄 README.md                     # 项目文档
```

## 🔧 开发配置

### 开发环境设置

```bash
# 安装开发依赖
pip install -e ".[dev]"

# 安装pre-commit钩子
pre-commit install

# 运行代码格式化
black src/
isort src/

# 类型检查
mypy src/

# 运行所有测试
pytest src/tests/ -v
```

### 代码质量工具

项目使用现代化的Python开发工具链：

- **Black**: 代码格式化
- **isort**: 导入排序
- **MyPy**: 类型检查
- **Pytest**: 测试框架
- **Ruff**: 快速代码检查
- **Pre-commit**: 提交前代码检查

### 构建和发布

```bash
# 构建项目
python -m build

# 验证构建结果
twine check dist/*

# 本地安装测试
pip install dist/decidra-1.0.0-py3-none-any.whl
```

## 📊 使用示例

### API使用示例

```python
from src.api.futu import FutuClient

# 创建客户端
client = FutuClient()
client.connect()

# 获取实时报价
quotes = client.quote.get_stock_quote(["HK.00700", "US.AAPL"])

# 获取K线数据
klines = client.quote.get_current_kline("HK.00700", "K_DAY", 30)

# 订阅实时数据
def callback(data):
    print(f"价格更新: {data}")

client.quote.subscribe_quote(["HK.00700"], callback=callback)
client.disconnect()
```

### 监控界面编程

```python
from src.monitor_app import MonitorApp

# 创建监控应用
app = MonitorApp()
app.monitored_stocks = ["HK.00700", "HK.09988", "US.AAPL"]

# 运行界面
app.run()
```

## ⚙️ 配置管理

### 环境变量配置

```bash
# 富途API配置
export FUTU_HOST=127.0.0.1
export FUTU_PORT=11111
export FUTU_TRD_ENV=SIMULATE

# 监控界面配置  
export MONITOR_REFRESH_INTERVAL=10
export MONITOR_REFRESH_MODE=auto

# 启用测试模式
export FUTU_TEST_ENABLED=true
```

### 配置文件

支持多种配置文件格式：

- `src/.runtime/config/config.ini`: 主配置文件
- `src/stock_strategy_map.yml`: 策略映射配置
- `pyproject.toml`: 项目构建配置

## 🤝 参与贡献

我们欢迎所有形式的贡献！

1. **Fork** 项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 **Pull Request**

## 🐛 问题排查

### 常见问题

**1. 富途API连接失败**
```bash
# 检查FutuOpenD是否运行
decidra futu test-connection

# 检查配置
decidra futu info
```

**2. 监控界面启动失败**
```bash
# 检查依赖是否完整
pip install textual

# 使用调试模式启动
DEBUG=true decidra monitor start
```


### 日志和调试

```bash
# 启用详细输出
decidra --verbose monitor start

# 查看错误日志
tail -f src/.runtime/logs/decidra.log
```

## 📄 许可证

本项目基于 [MIT License](https://opensource.org/licenses/MIT) 开源。

## 🙏 致谢

- [富途证券](https://www.futunn.com/) - 提供强大的交易API
- [Textual](https://github.com/Textualize/textual) - 现代化终端UI框架
- [Claude AI](https://claude.ai/) - AI分析能力支持

## 📞 联系方式

- 作者: **rtx3**
- 邮箱: r@rtx3.com
- GitHub: https://github.com/rtxIII/decidra

---

⭐ 如果这个项目对您有帮助，请给我们一个 Star！