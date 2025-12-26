# Decidra 打包发布指南

本文档说明如何将 Decidra 打包并发布到 PyPI。

## 前置准备

### 1. 验证项目配置

运行验证脚本检查项目配置：

```bash
python verify_package.py
```

应该看到所有检查通过的输出。

### 2. 安装构建工具

```bash
# 使用 trade 环境
source activate trade  # 或 conda activate trade

# 安装构建工具
pip install build twine
```

## 构建步骤

### 1. 清理旧的构建文件

```bash
# 清理旧的构建产物
rm -rf build/ dist/ *.egg-info

# 清理 Python 缓存
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete
find . -type f -name "*.pyo" -delete
```

### 2. 构建项目

```bash
# 构建源代码分发包和 wheel 包
python -m build

# 构建完成后会在 dist/ 目录生成：
# - decidra-1.0.0.tar.gz       (源代码分发包)
# - decidra-1.0.0-py3-none-any.whl  (wheel 包)
```

### 3. 验证构建结果

```bash
# 使用 twine 检查包的元数据
twine check dist/*

# 应该看到：
# Checking dist/decidra-1.0.0-py3-none-any.whl: PASSED
# Checking dist/decidra-1.0.0.tar.gz: PASSED
```

### 4. 查看包内容

```bash
# 查看 wheel 包内容
unzip -l dist/decidra-1.0.0-py3-none-any.whl

# 查看源码包内容
tar -tzf dist/decidra-1.0.0.tar.gz
```

## 本地测试安装

### 1. 创建测试虚拟环境

```bash
# 创建新的虚拟环境用于测试
conda create -n test_decidra python=3.10
conda activate test_decidra
```

### 2. 安装构建的包

```bash
# 从 wheel 安装
pip install dist/decidra-1.0.0-py3-none-any.whl

# 或从源码包安装
pip install dist/decidra-1.0.0.tar.gz
```

### 3. 测试安装

```bash
# 测试命令行工具
decidra --help
decidra-monitor --help

# 测试 Python 导入
python -c "from api.futu import FutuClient; print('✓ API模块导入成功')"
python -c "from modules.futu_market import FutuMarket; print('✓ Modules导入成功')"
python -c "import cli; import monitor_app; print('✓ 入口点导入成功')"
```

### 4. 清理测试环境

```bash
conda deactivate
conda env remove -n test_decidra
```

## 发布到 PyPI

### 1. 准备 PyPI 账户

- 注册账户: https://pypi.org/account/register/
- 生成 API Token: https://pypi.org/manage/account/token/
- 配置 `.pypirc` 文件:

```bash
cat > ~/.pypirc << EOF
[pypi]
username = __token__
password = pypi-<your-token-here>

[testpypi]
username = __token__
password = pypi-<your-testpypi-token-here>
EOF

chmod 600 ~/.pypirc
```

### 2. 发布到 TestPyPI（推荐先测试）

```bash
# 上传到 TestPyPI
twine upload --repository testpypi dist/*

# 从 TestPyPI 安装测试
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ decidra
```

### 3. 发布到正式 PyPI

```bash
# 确认一切正常后，上传到正式 PyPI
twine upload dist/*

# 输入用户名和密码（或使用 token）
# 上传成功后，包会在几分钟内可用
```

### 4. 验证发布

```bash
# 从 PyPI 安装
pip install decidra

# 查看包信息
pip show decidra

# 访问 PyPI 项目页面
# https://pypi.org/project/decidra/
```

## 版本更新流程

### 1. 更新版本号

编辑 [pyproject.toml](pyproject.toml:7):
```toml
version = "1.0.1"  # 更新版本号
```

### 2. 更新 CHANGELOG.md

在 [CHANGELOG.md](CHANGELOG.md) 中添加新版本的变更记录：

```markdown
## [1.0.1] - 2024-12-27

### Fixed
- 修复了某个 bug

### Added
- 添加了新功能
```

### 3. 提交变更

```bash
git add pyproject.toml CHANGELOG.md
git commit -m "Bump version to 1.0.1"
git tag v1.0.1
git push origin main --tags
```

### 4. 重新构建和发布

重复上述构建和发布步骤。

## 常见问题

### Q: 构建失败怎么办？

A: 检查以下几点：
1. 运行 `python verify_package.py` 确保配置正确
2. 检查 `pyproject.toml` 语法是否有误
3. 确保所有依赖都已安装
4. 查看详细错误信息

### Q: 上传失败怎么办？

A: 可能的原因：
1. 包名已被占用（需要更改包名）
2. 版本号已存在（需要更新版本号）
3. Token 配置错误（检查 `.pypirc`）
4. 网络问题（使用代理或 VPN）

### Q: 如何删除已发布的版本？

A: PyPI 不允许删除已发布的版本，但可以：
1. Yank 版本（标记为不推荐）：在 PyPI 网页上操作
2. 发布新版本修复问题

### Q: 如何包含数据文件？

A: 已在 `MANIFEST.in` 和 `pyproject.toml` 中配置：
- `MANIFEST.in`: 控制源码分发包包含的文件
- `[tool.setuptools.package-data]`: 控制 wheel 包包含的文件

## 自动化发布（可选）

可以使用 GitHub Actions 实现自动发布：

创建 `.github/workflows/publish.yml`:

```yaml
name: Publish to PyPI

on:
  release:
    types: [created]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - uses: actions/setup-python@v4
      with:
        python-version: '3.10'
    - name: Install dependencies
      run: |
        pip install build twine
    - name: Build package
      run: python -m build
    - name: Publish to PyPI
      env:
        TWINE_USERNAME: __token__
        TWINE_PASSWORD: ${{ secrets.PYPI_API_TOKEN }}
      run: twine upload dist/*
```

## 维护清单

发布前检查清单：

- [ ] 所有测试通过
- [ ] 更新版本号
- [ ] 更新 CHANGELOG.md
- [ ] 更新文档
- [ ] 运行 `python verify_package.py`
- [ ] 清理旧的构建文件
- [ ] 构建新包
- [ ] 本地测试安装
- [ ] 发布到 TestPyPI 测试
- [ ] 发布到正式 PyPI
- [ ] 创建 Git tag
- [ ] 推送到 GitHub

## 参考资源

- [Python 打包指南](https://packaging.python.org/)
- [PyPI 官方文档](https://pypi.org/help/)
- [Setuptools 文档](https://setuptools.pypa.io/)
- [Twine 文档](https://twine.readthedocs.io/)

---

*最后更新: 2024-12-26*
