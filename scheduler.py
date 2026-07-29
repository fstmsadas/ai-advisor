import logging
import sys
from datetime import datetime, timedelta
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from system_metrics import get_system_metrics, get_top_processes
from log_analyzer import analyze_log_file, save_stats_to_db
from db import insert_system_metrics, get_connection, insert_ai_advice
from ai_advisor import get_optimization_advice
from config import config
from utils import setup_logger, get_today_str

logger = setup_logger('scheduler')
logger.info("=" * 50)
logger.info("调度器启动，日志系统已初始化")

# 记录上次触发 AI 建议的时间（防止过于频繁）
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
        logger.info(f"✅ 指标已入库 (ID={inserted_id})")

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
                    logger.info(f"✅ AI 建议已存入数据库 (ID={advice_id})")
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

def cpu_monitor_task():
    """
    高频 CPU 监控任务：每 30 秒检查一次 CPU，
    若超阈值且距上次触发超过 60 秒，则立即执行一次完整采集。
    """
    global last_trigger_time
    try:
        cpu = get_system_metrics()['cpu_percent']
        threshold = config.CPU_THRESHOLD
        if cpu > threshold:
            now = datetime.now()
            if last_trigger_time is None or (now - last_trigger_time).total_seconds() > 60:
                logger.warning(f"🔴 高频监控检测到 CPU {cpu}% 超过阈值 {threshold}%，立即触发采集和建议")
                # 执行完整采集（会判断是否超阈值并生成 AI 建议）
                job_collect_metrics()
                last_trigger_time = now
            else:
                logger.debug(f"CPU {cpu}% 超阈值，但距上次触发不足 60 秒，跳过")
        else:
            logger.debug(f"CPU {cpu}% 正常")
    except Exception as e:
        logger.error(f"高频监控任务异常: {e}", exc_info=True)

def start_scheduler():
    try:
        test_db_connection()
    except Exception as e:
        logger.error(f"数据库连接失败，调度器无法启动: {e}")
        return

    scheduler = BlockingScheduler(timezone='Asia/Shanghai')

    # 1. 每小时整点后 5 分钟执行（长期趋势）
    scheduler.add_job(job_collect_metrics, 'cron', minute=5, id='metrics')
    logger.info("🕐 任务已添加: 每小时采集指标 (整点后5分) 北京时间")

    # 2. 每天 14:00 日志分析
    scheduler.add_job(job_analyze_log, CronTrigger(hour=14, minute=0), id='log_analysis')
    logger.info("🕐 任务已添加: 每天14:00分析日志 (北京时间)")

    # 3. 高频 CPU 监控（每 30 秒检查一次，超阈值时立即触发采集）
    scheduler.add_job(cpu_monitor_task, 'interval', seconds=30, id='cpu_monitor')
    logger.info("🕐 任务已添加: 高频CPU监控 (每30秒检查，超阈值立即采集)")

    # 4. 延迟 30 秒后执行一次采集（启动验证）
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
