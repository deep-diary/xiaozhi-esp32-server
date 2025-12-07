#!/bin/zsh

# 获取脚本所在目录的绝对路径
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "正在查找并终止 app.py 进程..."

# 查找并杀掉 app.py 进程
APP_PIDS=$(ps aux | grep "[p]ython.*app.py" | awk '{print $2}')

if [ -z "$APP_PIDS" ]; then
    echo "未找到运行中的 app.py 进程"
else
    echo "找到以下 app.py 进程: $APP_PIDS"
    for PID in $APP_PIDS; do
        echo "正在终止进程 $PID..."
        kill -9 $PID 2>/dev/null
    done
    echo "已终止所有 app.py 进程"
    sleep 1
fi

# 初始化 conda
CONDA_BASE=$(conda info --base 2>/dev/null)
if [ -z "$CONDA_BASE" ]; then
    # 如果 conda info 不可用，尝试常见路径
    if [ -f "$HOME/anaconda3/etc/profile.d/conda.sh" ]; then
        CONDA_BASE="$HOME/anaconda3"
    elif [ -f "$HOME/miniconda3/etc/profile.d/conda.sh" ]; then
        CONDA_BASE="$HOME/miniconda3"
    elif [ -f "/opt/anaconda3/etc/profile.d/conda.sh" ]; then
        CONDA_BASE="/opt/anaconda3"
    elif [ -f "/opt/homebrew/Caskroom/miniconda/base/etc/profile.d/conda.sh" ]; then
        CONDA_BASE="/opt/homebrew/Caskroom/miniconda/base"
    fi
fi

if [ -n "$CONDA_BASE" ] && [ -f "$CONDA_BASE/etc/profile.d/conda.sh" ]; then
    echo "正在初始化 conda..."
    source "$CONDA_BASE/etc/profile.d/conda.sh"
fi

# 切换到应用目录
echo "正在切换到应用目录: main/xiaozhi-server"
cd main/xiaozhi-server

# 使用 conda run 启动应用（更可靠的方式）
echo "正在使用 conda 环境 xiaozhi-esp32-server 启动 app.py..."
conda activate xiaozhi-esp32-server
python app.py

