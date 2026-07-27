#!/bin/bash
# myapp-v2 一键启动脚本（开发环境）
# 用法：./start.sh [start|stop|restart|status]

set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

# 激活虚拟环境（如果存在）
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi

# 定义日志文件
APP_LOG="logs/app.log"
SCHEDULER_LOG="logs/scheduler.log"
PID_DIR="run"
mkdir -p logs run

start_app() {
    echo "🔹 启动 Flask 应用 (端口 8000)..."
    nohup python app.py > "$APP_LOG" 2>&1 &
    echo $! > "$PID_DIR/app.pid"
    echo "   PID: $(cat $PID_DIR/app.pid)，日志: $APP_LOG"
}

start_scheduler() {
    echo "🔹 启动调度器 (每小时采集)..."
    nohup python scheduler.py > "$SCHEDULER_LOG" 2>&1 &
    echo $! > "$PID_DIR/scheduler.pid"
    echo "   PID: $(cat $PID_DIR/scheduler.pid)，日志: $SCHEDULER_LOG"
}

stop_process() {
    if [ -f "$1" ]; then
        PID=$(cat "$1")
        if kill -0 "$PID" 2>/dev/null; then
            kill "$PID"
            echo "✅ 已停止进程 PID=$PID"
        else
            echo "⚠️  进程 $PID 已不存在"
        fi
        rm -f "$1"
    fi
}

case "$1" in
    start)
        stop_process "$PID_DIR/app.pid" 2>/dev/null || true
        stop_process "$PID_DIR/scheduler.pid" 2>/dev/null || true
        start_app
        start_scheduler
        echo "✅ 全部服务已启动"
        ;;
    stop)
        stop_process "$PID_DIR/app.pid"
        stop_process "$PID_DIR/scheduler.pid"
        echo "✅ 全部服务已停止"
        ;;
    restart)
        $0 stop
        sleep 2
        $0 start
        ;;
    status)
        echo "--- 服务状态 ---"
        for p in app scheduler; do
            if [ -f "$PID_DIR/$p.pid" ]; then
                PID=$(cat "$PID_DIR/$p.pid")
                if kill -0 "$PID" 2>/dev/null; then
                    echo "✅ $p 运行中 (PID=$PID)"
                else
                    echo "❌ $p 已停止 (PID 文件残留)"
                fi
            else
                echo "❌ $p 未启动"
            fi
        done
        ;;
    *)
        echo "用法: $0 {start|stop|restart|status}"
        exit 1
        ;;
esac
