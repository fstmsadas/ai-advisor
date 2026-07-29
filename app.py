from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from db import execute_query
from config import config
import logging
import json
import time
from datetime import datetime
from cache import cache_get, cache_set
from ai import generate_response
from system_metrics import collect_all_sync

app = Flask(__name__)
CORS(app)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------- 首页 ----------
@app.route('/')
def index():
    return render_template('index.html')

# ---------- 健康检查 ----------
@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        "status": "ok",
        "db_host": config.DB_HOST,
        "redis_host": config.REDIS_HOST
    })

# ---------- 用户分页查询 ----------
@app.route('/api/users', methods=['GET'])
def get_users():
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 10))
        per_page = min(per_page, 100)

        conditions = []
        params = []
        if 'name_like' in request.args:
            conditions.append("name LIKE %s")
            params.append(f"%{request.args['name_like']}%")
        if 'city' in request.args:
            conditions.append("city = %s")
            params.append(request.args['city'])

        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

        offset = (page - 1) * per_page
        sql = f"""
            SELECT id, name, age, city, score, status, created_at
            FROM users
            {where_clause}
            ORDER BY score DESC, id ASC
            LIMIT %s OFFSET %s
        """
        query_params = params + [per_page, offset]
        rows = execute_query(sql, query_params)

        columns = ['id', 'name', 'age', 'city', 'score', 'status', 'created_at']
        data = [dict(zip(columns, row)) for row in rows]

        count_sql = f"SELECT COUNT(*) FROM users {where_clause}"
        total = execute_query(count_sql, params)[0][0]

        return jsonify({
            "code": 0,
            "data": data,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "pages": (total + per_page - 1) // per_page
            }
        })
    except Exception as e:
        logger.error(f"查询异常: {e}")
        return jsonify({"code": 500, "msg": str(e)}), 500

# ---------- AI 单轮生成 ----------
@app.route('/api/ai', methods=['GET'])
def ai_generate():
    prompt = request.args.get('prompt')
    if not prompt:
        return jsonify({"code": 400, "msg": "缺少 prompt 参数"}), 400
    try:
        temperature = float(request.args.get('temperature', 0.7))
        reply = generate_response(prompt, temperature)
        return jsonify({"code": 0, "data": reply})
    except Exception as e:
        return jsonify({"code": 500, "msg": str(e)}), 500

# ---------- 监控数据表格页面 ----------
@app.route('/monitor')
def monitor():
    try:
        sql = """
            SELECT id, cpu_percent, memory_percent, disk_usage, load_avg, timestamp
            FROM system_metrics
            ORDER BY id DESC
            LIMIT 50
        """
        rows = execute_query(sql)
        columns = ['id', 'cpu_percent', 'memory_percent', 'disk_usage', 'load_avg', 'timestamp']
        metrics = [dict(zip(columns, row)) for row in rows]
        return render_template('monitor.html', metrics=metrics)
    except Exception as e:
        return f"<h1>错误</h1><p>{e}</p>", 500

# ---------- AI 聊天页面 ----------
@app.route('/chat')
def chat_page():
    return render_template('chat.html')

# ---------- AI 多轮对话 API ----------
@app.route('/api/chat', methods=['POST'])
def api_chat():
    data = request.json
    prompt = data.get('prompt')
    session_id = data.get('session_id')
    if not prompt or not session_id:
        return jsonify({"code": 400, "msg": "缺少 prompt 或 session_id"}), 400

    from ai import generate_chat
    from cache import get_chat_history, save_chat_history

    try:
        history = get_chat_history(session_id)
        history.append({"role": "user", "content": prompt})
        reply = generate_chat(history, temperature=0.7)
        history.append({"role": "assistant", "content": reply})
        save_chat_history(session_id, history)
        return jsonify({"code": 0, "data": reply})
    except Exception as e:
        return jsonify({"code": 500, "msg": str(e)}), 500

# ---------- 清除会话历史 ----------
@app.route('/api/chat/clear', methods=['POST'])
def clear_chat():
    data = request.json
    session_id = data.get('session_id')
    if not session_id:
        return jsonify({"code": 400, "msg": "缺少 session_id"}), 400
    from cache import clear_chat_history
    clear_chat_history(session_id)
    return jsonify({"code": 0, "msg": "历史已清除"})

# ---------- AI 建议历史页面 ----------
@app.route('/advice')
def advice_list():
    try:
        sql = """
            SELECT id, advice_text, cpu_percent, created_at
            FROM ai_advice
            ORDER BY id DESC
            LIMIT 50
        """
        rows = execute_query(sql)
        columns = ['id', 'advice_text', 'cpu_percent', 'created_at']
        advices = [dict(zip(columns, row)) for row in rows]
        return render_template('advice.html', advices=advices)
    except Exception as e:
        return f"<h1>错误</h1><p>{e}</p>", 500

# ---------- AI 建议历史 API ----------
@app.route('/api/advice', methods=['GET'])
def api_advice():
    limit = request.args.get('limit', default=50, type=int)
    limit = min(limit, 200)
    try:
        sql = """
            SELECT id, advice_text, cpu_percent, created_at
            FROM ai_advice
            ORDER BY id DESC
            LIMIT %s
        """
        rows = execute_query(sql, (limit,))
        columns = ['id', 'advice_text', 'cpu_percent', 'created_at']
        data = [dict(zip(columns, row)) for row in rows]
        return jsonify({"code": 0, "data": data})
    except Exception as e:
        return jsonify({"code": 500, "msg": str(e)}), 500

# ==================== AI 诊断功能 ====================
@app.route('/api/diagnose', methods=['POST'])
def api_diagnose():
    try:
        sql = """
            SELECT cpu_percent, memory_percent, disk_usage, load_avg, timestamp
            FROM system_metrics
            ORDER BY id DESC LIMIT 1
        """
        row = execute_query(sql)
        if not row:
            return jsonify({"code": 1, "msg": "暂无监控数据，请先采集指标"}), 200

        cpu, mem, disk, load, ts = row[0]
        cpu_key = round(cpu)
        mem_key = round(mem)
        disk_key = round(disk)

        now = datetime.now()
        window = int(now.timestamp() // 300)
        cache_key = f"diagnose:{cpu_key}_{mem_key}_{disk_key}_{window}"

        cached = cache_get(cache_key)
        if cached:
            return jsonify({
                "code": 0,
                "data": {
                    "diagnosis": cached,
                    "cached": True,
                    "timestamp": now.isoformat()
                }
            })

        prompt = f"""
        根据以下系统指标，请进行专业诊断并提出优化建议：
        - CPU 使用率: {cpu}%
        - 内存使用率: {mem}%
        - 磁盘使用率: {disk}%
        - 系统负载: {load}
        请分析当前系统是否存在性能瓶颈，给出具体可行的优化措施。
        """
        diagnosis = generate_response(prompt, temperature=0.3)

        cache_set(cache_key, diagnosis, ttl=300)

        return jsonify({
            "code": 0,
            "data": {
                "diagnosis": diagnosis,
                "cached": False,
                "timestamp": now.isoformat()
            }
        })
    except Exception as e:
        logger.error(f"AI 诊断失败: {e}", exc_info=True)
        return jsonify({"code": 500, "msg": str(e)}), 500

# ==================== 日志分析页面与 API ====================
@app.route('/logs')
def logs():
    try:
        sql = """
            SELECT id, log_date, total_lines, error_count, warning_count, info_count, log_file, created_at
            FROM log_stats
            ORDER BY id DESC
            LIMIT 50
        """
        rows = execute_query(sql)
        columns = ['id', 'log_date', 'total_lines', 'error_count', 'warning_count', 'info_count', 'log_file', 'created_at']
        stats = [dict(zip(columns, row)) for row in rows]
        return render_template('logs.html', stats=stats)
    except Exception as e:
        return f"<h1>错误</h1><p>{e}</p>", 500

@app.route('/api/logs/analyze', methods=['POST'])
def api_analyze_log():
    try:
        from log_analyzer import analyze_log_file, save_stats_to_db
        from config import config
        log_path = config.LOG_FILE_PATH
        stats = analyze_log_file(log_path)
        save_stats_to_db(stats)
        return jsonify({"code": 0, "msg": "分析完成", "data": stats})
    except Exception as e:
        return jsonify({"code": 500, "msg": str(e)}), 500

# ==================== CPU 趋势 ====================
@app.route('/api/cpu_trend', methods=['GET'])
def api_cpu_trend():
    limit = request.args.get('limit', default=100, type=int)
    limit = min(limit, 500)
    try:
        sql = """
            SELECT timestamp, cpu_percent
            FROM system_metrics
            ORDER BY id DESC
            LIMIT %s
        """
        rows = execute_query(sql, (limit,))
        rows = rows[::-1]  # 时间升序
        data = {
            "timestamps": [row[0].strftime('%Y-%m-%d %H:%M:%S') for row in rows],
            "values": [float(row[1]) for row in rows]
        }
        return jsonify({"code": 0, "data": data})
    except Exception as e:
        return jsonify({"code": 500, "msg": str(e)}), 500

@app.route('/trend')
def trend():
    return render_template('trend.html')

# ==================== 聚合监控（新增） ====================
@app.route('/api/metrics', methods=['GET'])
def api_metrics():
    try:
        data = collect_all_sync()
        return jsonify({"code": 0, "data": data})
    except Exception as e:
        return jsonify({"code": 500, "msg": str(e)}), 500

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')
# ==================== 聚合监控图表（新增） ====================
@app.route('/api/trend_all', methods=['GET'])
def api_trend_all():
    """返回最近 N 条记录的 CPU 和内存历史数据（用于仪表盘趋势图）"""
    limit = request.args.get('limit', default=60, type=int)
    limit = min(limit, 200)
    try:
        sql = """
            SELECT timestamp, cpu_percent, memory_percent
            FROM system_metrics
            ORDER BY id DESC
            LIMIT %s
        """
        rows = execute_query(sql, (limit,))
        rows = rows[::-1]  # 时间升序
        data = {
            "timestamps": [row[0].strftime('%Y-%m-%d %H:%M:%S') for row in rows],
            "cpu_values": [float(row[1]) for row in rows],
            "memory_values": [float(row[2]) for row in rows]
        }
        return jsonify({"code": 0, "data": data})
    except Exception as e:
        return jsonify({"code": 500, "msg": str(e)}), 500

# ---------- 启动 ----------
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=config.DEBUG)
