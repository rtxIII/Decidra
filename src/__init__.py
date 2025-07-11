import warnings

# 过滤富途API相关的警告
warnings.filterwarnings("ignore", category=ResourceWarning, message=".*socket.*")
warnings.filterwarnings("ignore", category=DeprecationWarning, message=".*setDaemon.*")
warnings.filterwarnings("ignore", category=ResourceWarning, message=".*unclosed.*")
warnings.filterwarnings("ignore", category=UserWarning, message=".*Pandas.*")