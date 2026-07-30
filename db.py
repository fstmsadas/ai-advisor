import pymysql
import json
from config import config

def get_connection():
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
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
            return cur.fetchall()
    finally:
        conn.close()

def execute_insert(sql, params=None):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
            conn.commit()
            return cur.lastrowid
    finally:
        conn.close()

def insert_system_metrics(metrics_dict):
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

def insert_ai_advice(advice_text, metrics, top_procs):
    sql = """
        INSERT INTO ai_advice 
        (advice_text, cpu_percent, memory_percent, disk_usage, load_avg, top_processes)
        VALUES (%s, %s, %s, %s, %s, %s)
    """
    top_json = json.dumps(top_procs, ensure_ascii=False)
    return execute_insert(sql, (
        advice_text,
        metrics['cpu_percent'],
        metrics['memory_percent'],
        metrics['disk_usage'],
        metrics['load_avg'],
        top_json
    ))
