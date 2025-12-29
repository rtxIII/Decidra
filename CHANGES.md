# Decidra 配置系统变更记录

## 2025-12-29 - 包配置重构

### 🎯 解决的问题

1. **`import decidra` 失败** - 包配置不正确导致无法导入
2. **scripts 目录未被打包** - `post_install.py` 不在安装包中

### ✅ 实施的解决方案

#### 1. 修复包配置 (pyproject.toml)

**之前:**
```toml
[tool.setuptools.package-dir]
"" = "src"  # 所有包都是顶级包,无法 import decidra
```

**现在:**
```toml
[tool.setuptools]
packages = ["decidra"]

[tool.setuptools.package-dir]
decidra = "src"  # src/ 映射为 decidra 包
```

**效果:**
- ✅ `import decidra` 现在可以正常工作
- ✅ `src/__init__.py` 成为 `decidra.__init__`
- ✅ 所有子模块通过 `decidra.*` 导入

#### 2. 重组 post_install.py 位置

**之前:**
```
scripts/
└── post_install.py  # ❌ scripts 目录不会被打包
```

**现在:**
```
src/
└── post_install.py  # ✅ 在 decidra 包内,会被打包
```

**相应更新:**
- 入口点: `scripts.post_install:main` → `decidra.post_install:main`
- 删除: `scripts/` 目录及 `scripts/__init__.py`

#### 3. 更新 CLI 入口点

```toml
[project.scripts]
decidra = "decidra.cli:cli"
decidra-monitor = "decidra.monitor_app:main"
decidra-init = "decidra.post_install:main"  # ✅ 新增并修正
```

### 📝 修改的文件

#### 核心配置
- [x] `pyproject.toml` - 修复包配置和入口点
- [x] `src/__init__.py` - 添加版本信息
- [x] `src/post_install.py` - 从 scripts/ 移动,修复导入

#### 工具和文档
- [x] `src/utils/init_dirs.py` - 新建目录初始化工具
- [x] `verify_package.py` - 更新配置检查方法
- [x] `docs/package-config-summary.md` - 新建总结文档
- [x] `docs/installation-guide.md` - 更新安装指南
- [x] `docs/quick-start-config.md` - 更新快速指南
- [x] `docs/config-flow-summary.md` - 新建流程文档

#### 清理
- [x] 删除 `scripts/` 目录
- [x] 删除 `src/decidra_init.py` (临时文件)
- [x] 移除 `rich_interactive==0.6.0` 依赖

### 🚀 用户使用流程

#### 安装后首次配置

```bash
# 1. 安装包
pip install decidra

# 2. 运行初始化(创建配置目录和文件)
decidra-init

# 3. 编辑配置
nano ~/.decidra/config.ini

# 4. 验证
decidra config validate

# 5. 开始使用
decidra monitor start
```

#### 验证安装

```bash
# 测试包导入
python -c "import decidra; print(decidra.__version__)"
# 输出: 1.0.2

# 查看包文件
python -c "import decidra; print(decidra.__file__)"
# 输出: /path/to/site-packages/decidra/__init__.py

# 运行验证脚本
python verify_package.py
```

### 📦 包结构对比

#### 之前的结构
```
site-packages/
├── api/              # ❌ 顶级包,无 decidra
├── cli.py            # ❌ 顶级模块
├── monitor/          # ❌ 顶级包
└── utils/            # ❌ 顶级包
```

#### 现在的结构
```
site-packages/
└── decidra/          # ✅ 正确的包结构
    ├── __init__.py   # 包入口
    ├── api/
    ├── cli.py
    ├── monitor/
    ├── post_install.py  # ✅ 在包内
    └── utils/
        └── init_dirs.py
```

### 🔍 技术细节

#### src-layout 包映射原理

**包映射语法:**
```toml
[tool.setuptools.package-dir]
<包名> = "<源目录>"
```

**我们的配置:**
```toml
decidra = "src"
```

**含义:**
- 将 `src/` 目录映射为 `decidra` 包
- `src/__init__.py` → `decidra.__init__`
- `src/api/` → `decidra.api`
- `src/cli.py` → `decidra.cli`

#### 相对导入支持机制 ✅

**问题:** 现有代码使用相对导入 (如 `from modules.X import Y`),但打包后模块路径变为 `decidra.modules.X`

**解决方案:** 在 `src/__init__.py` 中添加模块别名映射:

```python
# 创建模块别名,使相对导入能够正常工作
import decidra.modules as modules
import decidra.utils as utils
import decidra.api as api
import decidra.base as base
import decidra.monitor as monitor
import decidra.strategies as strategies

sys.modules['modules'] = modules
sys.modules['utils'] = utils
# ... 其他模块
```

**效果:**
- ✅ 现有代码无需修改即可正常工作
- ✅ `from modules.X` 自动解析为 `from decidra.modules.X`
- ✅ 所有相对导入保持兼容性

### ⚠️ 破坏性变更

#### 1. CLI 命令调用

**之前:**
```bash
python -m scripts.post_install
```

**现在:**
```bash
decidra-init
# 或
python -m decidra.post_install
```

#### 2. 导入路径

如果有外部代码直接导入,需要更新:

**之前:**
```python
from scripts.post_install import main
```

**现在:**
```python
from decidra.post_install import main
```

### ✨ 新增功能

1. **版本信息导出**
   ```python
   import decidra
   print(decidra.__version__)  # "1.0.2"
   print(decidra.__author__)   # "rtx3"
   ```

2. **CLI 初始化命令**
   ```bash
   decidra-init  # 一键配置
   ```

3. **目录初始化工具**
   ```python
   from decidra.utils.init_dirs import initialize_decidra_dirs
   initialize_decidra_dirs(verbose=True)
   ```

4. **包验证工具**
   ```bash
   python verify_package.py  # 验证包配置
   ```

### 📖 相关文档

- [包配置完整总结](docs/package-config-summary.md)
- [完整安装指南](docs/installation-guide.md)
- [快速配置指南](docs/quick-start-config.md)
- [配置流程总结](docs/config-flow-summary.md)

### 🐛 已知问题

无

### 📅 下一步计划

- [ ] 添加自动化测试验证包配置
- [ ] 创建 PyPI 发布检查清单
- [ ] 编写安装后自动运行脚本的机制

---

**变更作者:** rtx3
**变更日期:** 2025-12-29
**版本:** 1.0.2
