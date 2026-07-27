import logging
import sys
from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from system_metrics import get_system_metrics
from log_analyzer import analyze_log_file, save_stats_to_db
from db import insert_system_metrics, get_connection
from config import config
from utils import setup_logger, get_today_str

# ---------- 初始化日志 ----------
logger = setup_logger('scheduler')
logger.info("=" * 50)
logger.info("调度器启动，日志系统已初始化")

def test_db_connection():
    """测试数据库连接"""
    logger.info("测试数据库连接...")
    conn = get_connection()
    conn.close()
    logger.info("数据库连接测试成功")

def job_collect_metrics():
    """采集指标并入库（含详细日志）"""
    logger.info(">>> job_collect_metrics 被调用")
    try:
        logger.info("开始获取系统指标...")
        metrics = get_system_metrics()
        logger.info(f"获取到指标: {metrics}")
        logger.info("开始插入数据库...")
        inserted_id = insert_system_metrics(metrics)
        logger.info(f"✅ 指标已入库 (ID={inserted_id})")
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

def start_scheduler():
    # ---------- 数据库连接测试 ----------
    try:
        test_db_connection()
    except Exception as e:
        logger.error(f"数据库连接失败，调度器无法启动: {e}")
        return

    # ---------- 创建调度器，明确指定北京时间时区 ----------
    scheduler = BlockingScheduler(timezone='Asia/Shanghai')  # ✅ 北京时间

    # ============================================================
    # 生产模式：每小时整点后 5 分钟执行一次
    # ============================================================
    scheduler.add_job(job_collect_metrics, 'cron', minute=5, id='metrics')
    logger.info("🕐 任务已添加: 每小时采集指标 (整点后5分) 北京时间")

    # ---- 如需测试，可取消注释以下两行，并注释掉上面的 cron 行 ----
    # scheduler.add_job(job_collect_metrics, 'interval', minutes=1, id='metrics')
    # logger.info("🕐 任务已添加: 每分钟采集指标 (测试模式) 北京时间")

    # ---- 日志分析任务（每天凌晨 2:00 北京时间） ----
    scheduler.add_job(job_analyze_log, CronTrigger(hour=2, minute=0), id='log_analysis')
    logger.info("🕐 任务已添加: 每天凌晨2点分析日志 (北京时间)")

    # ---------- 立即执行一次采集（验证） ----------
    logger.info("⏳ 立即执行一次采集（验证）...")
    job_collect_metrics()

    # ---------- 提示信息 ----------
    logger.info("✅ 调度器已配置，将按设定的北京时间定时执行任务")

    # ---------- 启动调度器 ----------
    try:
        logger.info("🚀 调度器已启动，按 Ctrl+C 停止")
        scheduler.start()
    except KeyboardInterrupt:
        scheduler.shutdown()
        logger.info("🛑 调度器已停止")

if __name__ == '__main__':
    start_scheduler()
