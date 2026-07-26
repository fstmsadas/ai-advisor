import re
from utils import get_today_str
from db import insert_log_stats

def analyze_log_file(filepath, log_date=None):
    """
    分析日志文件，统计各级别数量及 ERROR 行号
    :param filepath: 日志文件路径
    :param log_date: 日期字符串，默认为今天
    :return: dict 包含统计信息
    """
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

    # 匹配日志级别（假设格式：2024-01-01 10:00:00 ERROR ...）
    pattern = re.compile(r'(ERROR|WARNING|INFO)')

    with open(filepath, 'r', encoding='utf-8') as f:
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

    return stats

def save_stats_to_db(stats):
    """将统计结果写入数据库"""
    insert_log_stats(stats)

def save_stats_to_json(stats, output_path):
    """将统计结果保存为 JSON 文件"""
    import json
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)
