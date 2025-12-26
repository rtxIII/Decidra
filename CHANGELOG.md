# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2024-12-26

### Added
- 初始版本发布
- 富途 OpenAPI 完整集成，支持港股、美股、A股实时数据
- 基于 Textual 框架的现代化终端监控界面
- AI 分析引擎集成（Claude AI）
- 技术指标计算器（MA、RSI、MACD等）
- 多数据源支持（Yahoo Finance、Tushare、Akshare）
- 完整的 CLI 工具和命令行界面
- 自定义交易策略引擎
- 完善的测试体系（145+ Python 文件）

### Features
- 实时股票监控和数据刷新
- 智能刷新机制（根据市场状态自动切换刷新模式）
- 用户分组管理和持仓监控
- 分析界面（K线图表、技术指标、AI建议）
- 五档买卖盘、逐笔交易、经纪队列数据展示
- 资金流向分析和活跃度评级
- 多市场支持和时区处理

### Technical
- Python 3.8+ 支持
- 采用 src-layout 项目结构
- 完整的 pyproject.toml 配置
- Black、isort、MyPy、Ruff 代码质量工具
- Pre-commit hooks 集成
- 完整的类型提示支持

---

## Version History

### Upcoming Features
- [ ] PyPI 包发布
- [ ] 更多技术指标支持
- [ ] 策略回测功能
- [ ] Web UI 界面
- [ ] Docker 容器化支持

---

*For detailed changes, see [commit history](https://github.com/rtxIII/decidra/commits/main)*
