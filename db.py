import pymysql
from config import config

def get_connection():
    """获取数据库连接，返回 pymysql.Connection 对象"""
    return pymysql.connect(
        host=config.DB_HOST,
        port=config.DB_PORT,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        database=config.DB_NAME,
        connect_timeout=config.DB_CONNECT_TIMEOUT,
        cursorclass=pymysql.cursors.Cursor
    )

def execute_query(sql, params=None):
    """
    执行查询 SQL，返回结果列表（元组形式）
    :param sql: SQL 语句，含 %s 占位符
    :param params: 参数元组或列表
    :return: 查询结果列表
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
            return cur.fetchall()
    finally:
        conn.close()

def execute_insert(sql, params=None):
    """
    执行插入/更新/删除语句，返回自增 ID 或影响行数
    :param sql: SQL 语句
    :param params: 参数
    :return: 自增 ID（如果是 INSERT）或影响行数
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
            conn.commit()
            return cur.lastrowid  # 若为 INSERT 且存在自增列则返回该值
    finally:
        conn.close()

def batch_insert(sql, params_list):
    """
    批量插入多条记录，返回影响行数
    :param sql: INSERT 语句
    :param params_list: 参数列表，每个元素为元组
    :return: 插入行数
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            affected = cur.executemany(sql, params_list)
            conn.commit()
            return affected
    finally:
        conn.close()

# 快捷业务方法
def insert_system_metrics(metrics_dict):
    """插入一条系统指标记录"""
    sql = """
        INSERT INTO system_metrics 
        (cpu_percent, memory_percent, disk_usage, load_avg, timestamp)
        VALUES (%s, %s, %s, %s, NOW())
    """
    return execute_insert(sql, (
        metrics_dict['cpu_percent'],
        metrics_dict['memory_percent'],
        metrics_dict['disk_usage'],
        metrics_dict['load_avg']
    ))

def insert_log_stats(stats_dict):
    """插入日志统计记录"""
    sql = """
        INSERT INTO log_stats 
        (log_date, total_lines, error_count, warning_count, info_count, log_file)
        VALUES (%s, %s, %s, %s, %s, %s)
    """
    return execute_insert(sql, (
        stats_dict['log_date'],
        stats_dict['total_lines'],
        stats_dict['error_count'],
        stats_dict['warning_count'],
        stats_dict['info_count'],
        stats_dict['log_file']
    ))
