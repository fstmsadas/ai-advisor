import argparse
from utils import setup_logger
from log_analyzer import analyze_log_file, save_stats_to_db, save_stats_to_json
from system_metrics import get_system_metrics, get_top_processes
from ai_advisor import check_and_advise
from scheduler import start_scheduler
from config import config

logger = setup_logger('main')

def main():
    parser = argparse.ArgumentParser(description='MyApp 运维工具集')
    subparsers = parser.add_subparsers(dest='command', help='子命令')

    # 日志分析
    parser_log = subparsers.add_parser('log', help='分析日志文件')
    parser_log.add_argument('--file', default=config.LOG_FILE_PATH, help='日志文件路径')
    parser_log.add_argument('--save-json', help='保存结果到 JSON 文件')
    parser_log.add_argument('--save-db', action='store_true', help='保存到数据库')

    # 系统指标
    parser_metrics = subparsers.add_parser('metrics', help='查看系统指标')
    parser_metrics.add_argument('--top', type=int, default=5, help='显示前 n 个 CPU 进程')

    # AI 建议
    parser_advise = subparsers.add_parser('advise', help='检查 CPU 并生成建议')
    parser_advise.add_argument('--threshold', type=int, default=config.CPU_THRESHOLD, help='CPU 阈值')

    # 调度器
    parser_sched = subparsers.add_parser('scheduler', help='启动定时任务调度器')

    args = parser.parse_args()

    if args.command == 'log':
        stats = analyze_log_file(args.file)
        print(f"总计行数: {stats['total_lines']}")
        print(f"ERROR 数: {stats['error_count']}")
        print(f"WARNING 数: {stats['warning_count']}")
        print(f"INFO 数: {stats['info_count']}")
        print(f"ERROR 行号（前10）: {stats['error_lines'][:10]}")
        if args.save_json:
            save_stats_to_json(stats, args.save_json)
            print(f"已保存到 {args.save_json}")
        if args.save_db:
            save_stats_to_db(stats)
            print("已入库")

    elif args.command == 'metrics':
        metrics = get_system_metrics()
        print(f"CPU: {metrics['cpu_percent']}%")
        print(f"内存: {metrics['memory_percent']}%")
        print(f"磁盘: {metrics['disk_usage']}%")
        print(f"负载: {metrics['load_avg']}")
        if args.top:
            procs = get_top_processes(args.top)
            print("Top 进程:")
            for p in procs:
                print(f"  {p['pid']} {p['user']} {p['cpu']}% {p['command']}")

    elif args.command == 'advise':
        advice = check_and_advise(args.threshold)
        if advice:
            print("AI 建议:")
            print(advice)
        else:
            print("CPU 未超阈值，无需建议")

    elif args.command == 'scheduler':
        print("启动调度器（按 Ctrl+C 停止）...")
        start_scheduler()

    else:
        parser.print_help()

if __name__ == '__main__':
    main()
