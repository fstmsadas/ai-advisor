import logging
import sys
import json
import time
from datetime import datetime, timedelta
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from system_metrics import get_system_metrics, get_top_processes
from log_analyzer import analyze_log_file, save_stats_to_db
from db import (
    insert_system_metrics, insert_log_stats, insert_ai_advice,
    _insert_system_metrics, _insert_log_stats, _insert_ai_advice,
    get_connection
)
from ai_advisor import get_optimization_advice
from config import config
from utils import setup_logger, get_today_str
from buffer import read_from_buffer, get_buffer_length, redis_available

logger = setup_logger('scheduler')
logger.info("=" * 50)
logger.info("调度器启动，日志系统已初始化")

# 记录上次触发 AI 建议的时间
last_trigger_time = None

def test_db_connection():
    logger.info("测试数据库连接...")
    conn = get_connection()
    conn.close()
    logger.info("数据库连接测试成功")

def job_collect_metrics():
    """完整采集指标并入库，若 CPU 超阈值则生成 AI 建议"""
    logger.info(">>> job_collect_metrics 被调用")
    try:
        logger.info("开始获取系统指标...")
        metrics = get_system_metrics()
        logger.info(f"获取到指标: {metrics}")

        logger.info("开始插入数据库...")
        inserted_id = insert_system_metrics(metrics)
        if inserted_id:
            logger.info(f"✅ 指标已入库 (ID={inserted_id})")
        else:
            logger.warning("指标已写入缓冲（MySQL 不可用）")

        cpu = metrics['cpu_percent']
        threshold = config.CPU_THRESHOLD
        if cpu > threshold:
            logger.warning(f"⚠️ CPU 使用率 {cpu}% 超过阈值 {threshold}%，正在获取 AI 优化建议...")
            try:
                top_procs = get_top_processes(5)
                advice = get_optimization_advice(metrics, top_procs)
                if advice:
                    logger.info(f"💡 AI 优化建议: {advice}")
                    advice_id = insert_ai_advice(advice, metrics, top_procs)
                    if advice_id:
                        logger.info(f"✅ AI 建议已存入数据库 (ID={advice_id})")
                    else:
                        logger.warning("AI 建议已写入缓冲（MySQL 不可用）")
                else:
                    logger.info("AI 未返回具体建议")
            except Exception as e:
                logger.error(f"AI 建议生成或入库失败: {e}", exc_info=True)
        else:
            logger.info(f"CPU 使用率 {cpu}% 正常（阈值 {threshold}%），无需建议")
    except Exception as e:
        logger.error(f"❌ 采集入库失败: {e}", exc_info=True)
    finally:
        sys.stdout.flush()

def job_analyze_log():
    try:
        log_path = config.LOG_FILE_PATH
        stats = analyze_log_file(log_path)
        save_stats_to_db(stats)
        logger.info(f"日志统计已入库: {stats}")
    except FileNotFoundError:
        logger.error(f"日志文件 {config.LOG_FILE_PATH} 不存在，跳过分析")
    except Exception as e:
        logger.error(f"日志分析失败: {e}", exc_info=True)

def job_cleanup():
    logger.info(">>> 开始执行数据清理任务...")
    conn = None
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            sql_sys = "DELETE FROM system_metrics WHERE timestamp < NOW() - INTERVAL 30 DAY"
            rows_sys = cur.execute(sql_sys)
            sql_log = "DELETE FROM log_stats WHERE created_at < NOW() - INTERVAL 90 DAY"
            rows_log = cur.execute(sql_log)
            sql_adv = "DELETE FROM ai_advice WHERE created_at < NOW() - INTERVAL 180 DAY"
            rows_adv = cur.execute(sql_adv)
            conn.commit()
            logger.info(f"✅ 数据清理完成: system_metrics 删除 {rows_sys} 条, log_stats 删除 {rows_log} 条, ai_advice 删除 {rows_adv} 条")
    except Exception as e:
        logger.error(f"❌ 数据清理失败: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

def cpu_monitor_task():
    global last_trigger_time
    try:
        cpu = get_system_metrics()['cpu_percent']
        threshold = config.CPU_THRESHOLD
        if cpu > threshold:
            now = datetime.now()
            if last_trigger_time is None or (now - last_trigger_time).total_seconds() > 60:
                logger.warning(f"🔴 高频监控检测到 CPU {cpu}% 超过阈值 {threshold}%，立即触发采集和建议")
                job_collect_metrics()
                last_trigger_time = now
            else:
                logger.debug(f"CPU {cpu}% 超阈值，但距上次触发不足 60 秒，跳过")
        else:
            logger.debug(f"CPU {cpu}% 正常")
    except Exception as e:
        logger.error(f"高频监控任务异常: {e}", exc_info=True)

def sync_buffer_to_mysql():
    """从缓冲区读取数据并尝试写入 MySQL，详细记录每一条的处理结果"""
    logger.info(">>> 开始同步缓冲数据到 MySQL...")
    total_synced = 0
    total_errors = 0
    for data_type in ["system_metrics", "log_stats", "ai_advice"]:
        items = read_from_buffer(data_type, batch_size=50)
        if not items:
            continue
        logger.info(f"从缓冲读取到 {len(items)} 条 {data_type} 数据")
        for idx, item in enumerate(items):
            try:
                if data_type == "system_metrics":
                    inserted_id = _insert_system_metrics(item)
                    logger.info(f"✅ 同步 system_metrics 成功 (ID={inserted_id})")
                elif data_type == "log_stats":
                    inserted_id = _insert_log_stats(item)
                    logger.info(f"✅ 同步 log_stats 成功 (ID={inserted_id})")
                elif data_type == "ai_advice":
                    inserted_id = _insert_ai_advice(item['advice_text'], item['metrics'], item['top_procs'])
                    logger.info(f"✅ 同步 ai_advice 成功 (ID={inserted_id})")
                total_synced += 1
            except Exception as e:
                logger.error(f"❌ 同步 {data_type} 第 {idx+1} 条失败: {e}")
                total_errors += 1
                # 将该条数据重新放回队列（仅 Redis 支持）
                if redis_available:
                    import redis
                    r = redis.Redis(host=config.REDIS_HOST, port=config.REDIS_PORT, decode_responses=True)
                    r.rpush(f"buffer:{data_type}", json.dumps(item))
                else:
                    # 文件缓冲需要额外处理，此处简化（将失败数据写回文件末尾）
                    # 但由于文件缓冲实现简单，失败数据可能丢失，建议使用 Redis
                    logger.warning("文件缓冲不支持重放，失败数据可能丢失")
    logger.info(f"✅ 缓冲数据同步完成：成功 {total_synced} 条，失败 {total_errors} 条")

def start_scheduler():
    try:
        test_db_connection()
    except Exception as e:
        logger.error(f"数据库连接失败，调度器无法启动: {e}")
        return

    scheduler = BlockingScheduler(timezone='Asia/Shanghai')

    # 1. 每小时整点后 5 分钟采集指标
    scheduler.add_job(job_collect_metrics, 'cron', minute=5, id='metrics')
    logger.info("🕐 任务已添加: 每小时采集指标 (整点后5分) 北京时间")

    # 2. 每天 14:00 日志分析
    scheduler.add_job(job_analyze_log, CronTrigger(hour=14, minute=0), id='log_analysis')
    logger.info("🕐 任务已添加: 每天14:00分析日志 (北京时间)")

    # 3. 每天凌晨 3:00 数据清理
    scheduler.add_job(job_cleanup, CronTrigger(hour=3, minute=0), id='cleanup')
    logger.info("🕐 任务已添加: 每天凌晨3点清理过期数据")

    # 4. 高频 CPU 监控（每 30 秒）
    scheduler.add_job(cpu_monitor_task, 'interval', seconds=30, id='cpu_monitor')
    logger.info("🕐 任务已添加: 高频CPU监控 (每30秒检查，超阈值立即采集)")

    # 5. 缓冲数据同步（每 30 秒）
    scheduler.add_job(sync_buffer_to_mysql, 'interval', seconds=30, id='sync_buffer')
    logger.info("🕐 任务已添加: 每30秒同步缓冲数据到MySQL")

    # 6. 延迟 30 秒后执行一次采集（启动验证）
    first_run = datetime.now() + timedelta(seconds=30)
    scheduler.add_job(job_collect_metrics, 'date', run_date=first_run, id='first_collect')
    logger.info(f"⏳ 首次采集将在 {first_run.strftime('%H:%M:%S')} 执行（30秒后）")

    logger.info("✅ 调度器已配置，将按设定的北京时间定时执行任务")
    try:
        logger.info("🚀 调度器已启动，按 Ctrl+C 停止")
        scheduler.start()
    except KeyboardInterrupt:
        scheduler.shutdown()
        logger.info("🛑 调度器已停止")

if __name__ == '__main__':
    start_scheduler()
