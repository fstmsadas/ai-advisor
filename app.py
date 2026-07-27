from flask import Flask, request, jsonify
from flask_cors import CORS
from db import execute_query
from config import config
import logging

# ---------- 初始化 ----------
app = Flask(__name__)
CORS(app)  # 允许跨域

# ---------- 日志 ----------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
    """
    查询参数：
        page: 页码（默认 1）
        per_page: 每页条数（默认 10，最大 100）
        name_like: 模糊匹配姓名（可选）
        city: 城市精确匹配（可选）
    """
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 10))
        per_page = min(per_page, 100)   # 限制最大值

        # 动态构建 WHERE
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

        # 统计总数
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

# ---------- AI 生成（复用 ai.py） ----------
@app.route('/api/ai', methods=['GET'])
def ai_generate():
    prompt = request.args.get('prompt')
    if not prompt:
        return jsonify({"code": 400, "msg": "缺少 prompt 参数"}), 400
    try:
        temperature = float(request.args.get('temperature', 0.7))
        from ai import generate_response
        reply = generate_response(prompt, temperature)
        return jsonify({"code": 0, "data": reply})
    except Exception as e:
        return jsonify({"code": 500, "msg": str(e)}), 500

# ---------- 启动 ----------
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=config.DEBUG)
