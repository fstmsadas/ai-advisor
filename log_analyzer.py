import re
from utils import get_today_str
from db import insert_log_stats
import logging

logger = logging.getLogger(__name__)

def analyze_log_file(filepath, log_date=None):
    if log_date is None:
        log_date = get_today_str()
    stats = {
        'log_date': log_date,
        'log_file': filepath,
        'total_lines': 0,
        'error_count': 0,
        'warning_count': 0,
        'info_count': 0,
        'error_lines': []
    }
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            pattern = re.compile(r'(ERROR|WARNING|INFO)')
            for line_num, line in enumerate(f, 1):
                stats['total_lines'] += 1
                match = pattern.search(line)
                if match:
                    level = match.group(1)
                    if level == 'ERROR':
                        stats['error_count'] += 1
                        stats['error_lines'].append(line_num)
                    elif level == 'WARNING':
                        stats['warning_count'] += 1
                    elif level == 'INFO':
                        stats['info_count'] += 1
    except FileNotFoundError:
        logger.error(f"日志文件 {filepath} 不存在")
    except Exception as e:
        logger.error(f"分析日志文件失败: {e}", exc_info=True)
    return stats

def save_stats_to_db(stats):
    try:
        insert_log_stats(stats)
    except Exception as e:
        logger.error(f"保存日志统计到数据库失败: {e}")
