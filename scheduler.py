from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
from system_metrics import get_system_metrics, get_top_processes
from log_analyzer import analyze_log_file, save_stats_to_db
from ai_advisor import get_optimization_advice
from db import insert_system_metrics
from utils import setup_logger, get_today_str
from config import config

logger = setup_logger('scheduler')

def job_collect_metrics():
    """每小时采集指标，若超阈值则触发 AI 建议"""
    metrics = get_system_metrics()
    insert_system_metrics(metrics)
    logger.info(f"指标已入库: {metrics}")

    if metrics['cpu_percent'] > config.CPU_THRESHOLD:
        top = get_top_processes(5)
        advice = get_optimization_advice(metrics, top)
        logger.info(f"AI 建议: {advice}")
        # 可将建议写入数据库或文件，此处仅记录日志

def job_analyze_log():
    """每天凌晨分析日志文件"""
    log_path = config.LOG_FILE_PATH
    try:
        stats = analyze_log_file(log_path)
        save_stats_to_db(stats)
        logger.info(f"日志统计已入库: {stats}")
    except FileNotFoundError:
        logger.error(f"日志文件 {log_path} 不存在，跳过分析")

def start_scheduler():
    """启动调度器"""
    scheduler = BlockingScheduler()
    # 每小时执行指标采集
    scheduler.add_job(job_collect_metrics, 'interval', hours=1, id='metrics')
    # 每天凌晨 2:00 执行日志分析
    scheduler.add_job(job_analyze_log, CronTrigger(hour=2, minute=0), id='log_analysis')
    try:
        logger.info("调度器已启动，按 Ctrl+C 停止")
        scheduler.start()
    except KeyboardInterrupt:
        scheduler.shutdown()
        logger.info("调度器已停止")
