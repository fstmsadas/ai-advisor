import logging
import sys
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

def test_db_connection():
    logger.info("测试数据库连接...")
    conn = get_connection()
    conn.close()
    logger.info("数据库连接测试成功")

def job_collect_metrics():
    logger.info(">>> job_collect_metrics 被调用")
    try:
        logger.info("开始获取系统指标...")
        metrics = get_system_metrics()
        logger.info(f"获取到指标: {metrics}")

        logger.info("开始插入数据库...")
        inserted_id = insert_system_metrics(metrics)
        logger.info(f"✅ 指标已入库 (ID={inserted_id})")

        # ========== CPU 超阈值触发 AI 建议 ==========
        cpu = metrics['cpu_percent']
        threshold = config.CPU_THRESHOLD
        if cpu > threshold:
            logger.warning(f"⚠️ CPU 使用率 {cpu}% 超过阈值 {threshold}%，正在获取 AI 优化建议...")
            try:
                # 获取当前高 CPU 进程（同一时刻）
                top_procs = get_top_processes(5)
                # 直接调用 get_optimization_advice，传入已采集的 metrics 和 top_procs
                advice = get_optimization_advice(metrics, top_procs)
                if advice:
                    logger.info(f"💡 AI 优化建议: {advice}")
                    # 入库
                    advice_id = insert_ai_advice(advice, metrics, top_procs)
                    logger.info(f"✅ AI 建议已存入数据库 (ID={advice_id})")
                else:
                    logger.info("AI 未返回具体建议")
            except Exception as e:
                logger.error(f"AI 建议生成或入库失败: {e}", exc_info=True)
        else:
            logger.info(f"CPU 使用率 {cpu}% 正常（阈值 {threshold}%），无需建议")
        # ============================================

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
    try:
        test_db_connection()
    except Exception as e:
        logger.error(f"数据库连接失败，调度器无法启动: {e}")
        return

    scheduler = BlockingScheduler(timezone='Asia/Shanghai')

    scheduler.add_job(job_collect_metrics, 'cron', minute=5, id='metrics')
    logger.info("🕐 任务已添加: 每小时采集指标 (整点后5分) 北京时间")

    scheduler.add_job(job_analyze_log, CronTrigger(hour=14, minute=0), id='log_analysis')
    logger.info("🕐 任务已添加: 每天凌晨2点分析日志 (北京时间)")

    logger.info("⏳ 立即执行一次采集（验证）...")
    job_collect_metrics()

    logger.info("✅ 调度器已配置，将按设定的北京时间定时执行任务")
    try:
        logger.info("🚀 调度器已启动，按 Ctrl+C 停止")
        scheduler.start()
    except KeyboardInterrupt:
        scheduler.shutdown()
        logger.info("🛑 调度器已停止")

if __name__ == '__main__':
    start_scheduler()
