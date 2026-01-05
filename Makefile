# Decidra Makefile
# 打包发布相关命令

.PHONY: help clean build check test-install upload upload-test verify init

# 默认目标
help:
	@echo "Decidra 打包发布命令"
	@echo ""
	@echo "使用方法: make <target>"
	@echo ""
	@echo "目标:"
	@echo "  verify       - 验证项目配置"
	@echo "  clean        - 清理构建文件"
	@echo "  build        - 构建包 (wheel + tar.gz)"
	@echo "  check        - 检查构建结果"
	@echo "  test-install - 在测试环境安装并验证"
	@echo "  upload-test  - 上传到 TestPyPI"
	@echo "  upload       - 上传到 PyPI"
	@echo "  init         - 运行初始化脚本"
	@echo "  all          - 完整流程: clean -> build -> check"
	@echo ""

# 验证项目配置
verify:
	@echo "验证项目配置..."
	python verify_package.py

# 清理构建文件
clean:
	@echo "清理构建文件..."
	rm -rf build/ dist/ *.egg-info decidra.egg-info
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	find . -type f -name ".DS_Store" -delete 2>/dev/null || true
	@echo "清理完成"

# 构建包
build: clean
	@echo "构建包..."
	python -m build
	@echo "构建完成"
	@ls -la dist/

# 检查构建结果
check:
	@echo "检查构建结果..."
	twine check dist/*

# 在测试环境安装并验证
test-install:
	@echo "测试安装..."
	@echo "1. 创建测试环境: conda create -n test python=3.10"
	@echo "2. 激活环境: conda activate test"
	@echo "3. 安装: pip install dist/decidra-*.whl"
	@echo "4. 验证: decidra --help && decidra-init"
	@echo ""
	@echo "快速验证命令:"
	pip install dist/decidra-*.whl --force-reinstall
	decidra --help
	python -c "import decidra; print(f'版本: {decidra.__version__}')"

# 上传到 TestPyPI
upload-test: check
	@echo "上传到 TestPyPI..."
	twine upload --repository testpypi dist/*
	@echo ""
	@echo "从 TestPyPI 安装测试:"
	@echo "pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ decidra"

# 上传到 PyPI
upload: check
	@echo "上传到 PyPI..."
	twine upload dist/*
	@echo ""
	@echo "发布完成! 安装命令: pip install decidra"

# 运行初始化脚本
init:
	python -m decidra.post_install

# 完整流程
all: verify clean build check
	@echo ""
	@echo "构建完成! 下一步:"
	@echo "  make test-install  - 本地测试安装"
	@echo "  make upload-test   - 上传到 TestPyPI"
	@echo "  make upload        - 上传到 PyPI"

# 查看包内容
show-wheel:
	@echo "Wheel 包内容:"
	unzip -l dist/decidra-*.whl | head -50

show-tar:
	@echo "源码包内容:"
	tar -tzf dist/decidra-*.tar.gz | head -50

# 版本信息
version:
	@grep "^version" pyproject.toml
	@python -c "import decidra; print(f'Python包版本: {decidra.__version__}')" 2>/dev/null || echo "包未安装"
