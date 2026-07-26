import psutil
import logging

logger = logging.getLogger(__name__)

def get_system_metrics():
    """
    获取系统核心指标：CPU、内存、磁盘、负载
    :return: dict 包含 cpu_percent, memory_percent, disk_usage, load_avg
    """
    cpu = psutil.cpu_percent(interval=1)
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    load = psutil.getloadavg()
    return {
        'cpu_percent': cpu,
        'memory_percent': mem.percent,
        'disk_usage': disk.percent,
        'load_avg': load[0]
    }

def get_top_processes(n=5):
    """
    使用 psutil 获取 CPU 占用最高的 n 个进程（无外部依赖）
    :param n: 进程数量
    :return: 进程信息列表，每个为 dict，包含 pid, user, cpu, mem, command
    """
    processes = []
    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
        try:
            # 获取 CPU 使用率（需间隔采样）
            cpu = proc.cpu_percent(interval=0.1)
            mem = proc.memory_percent()
            processes.append({
                'pid': proc.pid,
                'user': proc.username(),
                'cpu': round(cpu, 1),
                'mem': round(mem, 1),
                'command': proc.name()
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    # 按 CPU 降序排序
    processes.sort(key=lambda x: x['cpu'], reverse=True)
    return processes[:n]

def is_cpu_high(threshold=80):
    """判断当前 CPU 是否超过阈值"""
    return psutil.cpu_percent(interval=0.5) > threshold
