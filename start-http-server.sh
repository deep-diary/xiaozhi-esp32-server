#!/bin/zsh

# 获取脚本所在目录的绝对路径
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "正在切换到目录: main/xiaozhi-server/test"
cd main/xiaozhi-server/test

# 检查端口 8006 是否已被占用
if lsof -Pi :8006 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    echo "警告: 端口 8006 已被占用"
    echo "正在查找并终止占用端口 8006 的进程..."
    PID=$(lsof -ti :8006)
    if [ ! -z "$PID" ]; then
        kill -9 $PID 2>/dev/null
        echo "已终止进程 $PID"
        sleep 1
    fi
fi

# 启动 HTTP 服务器
echo "正在启动 HTTP 服务器，端口: 8006"
echo "访问地址: http://localhost:8006"
echo "按 Ctrl+C 停止服务器"
echo ""

python -m http.server 8006

