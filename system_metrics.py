import psutil
import asyncio
import socket
import logging

logger = logging.getLogger(__name__)

# ==================== 原有同步函数 ====================

def get_system_metrics():
    """同步获取系统基础指标（CPU、内存、磁盘、负载）"""
    try:
        cpu = psutil.cpu_percent(interval=1)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        load = psutil.getloadavg()
    except Exception as e:
        logger.error(f"采集系统指标失败: {e}", exc_info=True)
        return {'cpu_percent': 0, 'memory_percent': 0, 'disk_usage': 0, 'load_avg': 0}
    return {
        'cpu_percent': cpu,
        'memory_percent': mem.percent,
        'disk_usage': disk.percent,
        'load_avg': load[0]
    }

def get_top_processes(n=5):
    """获取 CPU 占用最高的 n 个进程"""
    try:
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                cpu = proc.cpu_percent(interval=0.5)
                mem = proc.memory_percent()
                processes.append({
                    'pid': proc.pid,
                    'user': proc.username(),
                    'cpu': round(cpu, 1),
                    'mem': round(mem, 1),
                    'command': proc.name()
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        processes.sort(key=lambda x: x['cpu'], reverse=True)
        return processes[:n]
    except Exception as e:
        logger.error(f"获取进程列表失败: {e}", exc_info=True)
        return []

def is_cpu_high(threshold=80):
    return psutil.cpu_percent(interval=1) > threshold

# ==================== 异步采集函数 ====================

async def async_get_cpu():
    return psutil.cpu_percent(interval=1)

async def async_get_memory():
    mem = psutil.virtual_memory()
    return {
        'total': mem.total,
        'available': mem.available,
        'percent': mem.percent,
        'used': mem.used,
        'free': mem.free
    }

async def async_get_disk():
    usage = psutil.disk_usage('/')
    io = psutil.disk_io_counters()
    return {
        'usage_percent': usage.percent,
        'total': usage.total,
        'used': usage.used,
        'free': usage.free,
        'read_bytes': io.read_bytes if io else 0,
        'write_bytes': io.write_bytes if io else 0,
        'read_count': io.read_count if io else 0,
        'write_count': io.write_count if io else 0
    }

async def async_get_network():
    conns = psutil.net_connections(kind='inet')
    tcp_conns = sum(1 for c in conns if c.type == socket.SOCK_STREAM)
    udp_conns = sum(1 for c in conns if c.type == socket.SOCK_DGRAM)
    net_io = psutil.net_io_counters()
    return {
        'tcp_connections': tcp_conns,
        'udp_connections': udp_conns,
        'total_connections': len(conns),
        'bytes_sent': net_io.bytes_sent,
        'bytes_recv': net_io.bytes_recv,
        'packets_sent': net_io.packets_sent,
        'packets_recv': net_io.packets_recv
    }

async def async_collect_all():
    """并发采集所有指标，返回聚合字典"""
    logger.info("异步采集所有指标...")
    cpu_task = asyncio.create_task(async_get_cpu())
    mem_task = asyncio.create_task(async_get_memory())
    disk_task = asyncio.create_task(async_get_disk())
    net_task = asyncio.create_task(async_get_network())
    cpu, mem, disk, net = await asyncio.gather(cpu_task, mem_task, disk_task, net_task)
    return {
        'cpu_percent': cpu,
        'memory': mem,
        'disk': disk,
        'network': net
    }

def collect_all_sync():
    """同步包装器，用于非异步上下文（如 Flask 路由）"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    result = loop.run_until_complete(async_collect_all())
    loop.close()
    return result
def collect_all_sync_simple():
    """简单的同步采集（避免 asyncio 开销）"""
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    io = psutil.disk_io_counters()
    conns = psutil.net_connections(kind='inet')
    return {
        'cpu_percent': psutil.cpu_percent(interval=0.5),
        'memory': {
            'percent': mem.percent,
            'available': mem.available
        },
        'disk': {
            'usage_percent': disk.percent,
            'read_bytes': io.read_bytes if io else 0,
            'write_bytes': io.write_bytes if io else 0
        },
        'network': {
            'total_connections': len(conns),
            'tcp_connections': sum(1 for c in conns if c.type == socket.SOCK_STREAM),
            'udp_connections': sum(1 for c in conns if c.type == socket.SOCK_DGRAM)
        }
    }
