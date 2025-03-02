import os
import socket
import logging
import argparse
from typing import Dict, List, Tuple
import concurrent.futures
import subprocess
import sys
import requests
from datetime import datetime
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# Telegram配置
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

# 自定义颜色过滤器
class ColorFilter(logging.Filter):
    def filter(self, record):
        color_map = {
            logging.DEBUG: "\033[37m",   # 灰色
            logging.INFO: "\033[92m",    # 绿色
            logging.WARNING: "\033[93m", # 黄色
            logging.ERROR: "\033[91m",   # 红色
            logging.CRITICAL: "\033[91m" # 红色
        }
        reset = "\033[0m"
        
        color = color_map.get(record.levelno, "")
        if color:
            record.msg = f"{color}{record.msg}{reset}"
        return True

# 配置日志系统
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

# 文件日志（无颜色）
file_handler = logging.FileHandler('proxy_check.log')
file_handler.setLevel(logging.INFO)
file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(file_formatter)

# 控制台日志（带颜色）
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.addFilter(ColorFilter())
console_formatter = logging.Formatter('%(message)s')
console_handler.setFormatter(console_formatter)

logger.addHandler(file_handler)
logger.addHandler(console_handler)

def send_telegram_notification(message: str, parse_mode: str = 'Markdown'):
    """发送Telegram通知"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logging.warning("未配置Telegram通知参数，跳过通知")
        return
    
    api_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": parse_mode
    }
    
    try:
        response = requests.post(api_url, json=payload, timeout=10)
        response.raise_for_status()
        logging.debug("Telegram通知发送成功")
    except Exception as e:
        logging.error(f"发送Telegram通知失败: {str(e)}")

def format_telegram_message(title: str, content: str) -> str:
    """格式化Telegram消息"""
    return f"*🔍 代理检测报告 - {title}*\n\n{content}\n\n`#自动运维`"

def get_ips(host: str) -> List[str]:
    """获取域名的所有IPv4地址（自动去重）"""
    try:
        addrinfos = socket.getaddrinfo(host, None, socket.AF_INET)
        # 使用有序字典去重，保留第一个出现的IP
        seen = set()
        ips = []
        for info in addrinfos:
            ip = info[4][0]
            if ip not in seen:
                seen.add(ip)
                ips.append(ip)
        return ips
    except socket.gaierror as e:
        logging.error(f"DNS解析失败 {host}: {str(e)}")
        return []
    except Exception as e:
        logging.error(f"获取{host} IP地址时发生未知错误: {str(e)}")
        return []

def check_proxy(host: str, port: int, timeout: float, retries: int) -> Tuple[bool, str]:
    """检测代理端口连通性（支持重试机制）"""
    last_error = ""
    for attempt in range(retries):
        try:
            with socket.create_connection((host, port), timeout=timeout):
                logging.debug(f"{host}:{port} 第{attempt+1}次连接成功")
                return (True, "")
        except (socket.timeout, ConnectionRefusedError, OSError) as e:
            last_error = f"{type(e).__name__}: {str(e)}"
            logging.debug(f"{host}:{port} 第{attempt+1}次连接失败: {last_error}")
        except Exception as e:
            last_error = f"未知错误: {str(e)}"
            logging.error(f"检测 {host}:{port} 时发生未知错误: {str(e)}")
    return (False, last_error)

def generate_table(data: List[Tuple[str, str, str]]) -> str:
    """生成解析结果表格"""
    if not data:
        return ""
    
    # 计算各列最大宽度（包含表头）
    headers = ("地区代码", "域名", "解析IP")
    code_width = max(max(len(item[0]) for item in data), len(headers[0]))
    host_width = max(max(len(item[1]) for item in data), len(headers[1]))
    ips_width = max(max(len(item[2]) for item in data), len(headers[2]))

    # 构建表格边框
    separator = f"+{'-'*(code_width+2)}+{'-'*(host_width+2)}+{'-'*(ips_width+2)}+"
    
    # 构建表头
    header = f"| {headers[0].ljust(code_width)} | {headers[1].ljust(host_width)} | {headers[2].ljust(ips_width)} |"
    
    # 构建数据行
    rows = []
    for code, host, ips in data:
        row = f"| {code.ljust(code_width)} | {host.ljust(host_width)} | {ips.ljust(ips_width)} |"
        rows.append(row)
    
    # 组合表格元素
    return "\n".join([separator, header, separator] + rows + [separator])

def main():
    # 解析命令行参数
    parser = argparse.ArgumentParser(
        description='代理服务器健康检测工具',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument('port', nargs='?', type=int, default=443,
                      help='检测端口号（默认443）')
    parser.add_argument('--timeout', type=float, default=1.0,
                       help='单次连接超时时间（秒）')
    parser.add_argument('--retries', type=int, default=3,
                       help='最大重试次数')
    args = parser.parse_args()

    # 代理服务器配置
    proxies: Dict[str, str] = {
        "hk.616049.xyz": "HKG",
        "us.616049.xyz": "LAX",
        "de.616049.xyz": "FRA",
        "sg.616049.xyz": "SIN",
        "jp.616049.xyz": "NRT"
    }

    # 预解析所有域名的IP地址
    ips_cache: Dict[str, List[str]] = {}
    table_data = []  # 新增：收集表格数据
    for host, code in proxies.items():
        ips = get_ips(host)
        ips_cache[host] = ips
        # 新增：收集表格数据
        ips_str = ', '.join(ips) if ips else '无IP地址'
        table_data.append((code, host, ips_str))

    # 新增：输出解析结果表格
    logging.info("\n🌐 域名解析结果:")
    logging.info(generate_table(table_data))

    failed_nodes: List[str] = []
    success_count = 0
    fail_count = 0

    # 使用线程池并发检测
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_to_host = {
            executor.submit(
                check_proxy,
                host=host,
                port=args.port,
                timeout=args.timeout,
                retries=args.retries
            ): (host, code)
            for host, code in proxies.items()
        }

        # 处理检测结果
        for future in concurrent.futures.as_completed(future_to_host):
            host, code = future_to_host[future]
            try:
                success, error_msg = future.result()
                ips = ips_cache.get(host, [])
                ips_str = ', '.join(ips) if ips else '无IP地址'
                
                if success:
                    success_count += 1
                    logging.info(f"[{code}] ✅ {host}:{args.port} 连接成功")
                else:
                    fail_count += 1
                    logging.error(
                        f"[{code}] ❌ {host}:{args.port} 检测失败\n"
                        f"  解析IP: {ips_str}\n"
                        f"  错误原因: {error_msg}"
                    )
                    failed_nodes.append(code)
            except Exception as e:
                fail_count += 1
                logging.error(f"[{code}] ❌ {host}:{args.port} 检测异常: {e}")
                failed_nodes.append(code)

    # 显示汇总信息
    logging.info("\n" + "="*40)
    logging.info(f"总检测节点: {len(proxies)}")
    logging.info(f"✅ 成功节点: {success_count}")
    if fail_count > 0:
        logging.error(f"❌ 失败节点: {fail_count}")
    else:
        logging.info("🎉 所有节点检测通过！")

    # 处理失败节点并触发更新
    unique_codes = sorted(set(failed_nodes))

    if unique_codes:
        codes_str = ",".join(unique_codes)
        # 发送更新通知
        update_msg = format_telegram_message(
            "触发节点更新", 
            f"• 失败地区: `{codes_str}`\n"
            f"• 检测端口: `{args.port}`\n"
            f"• 失败节点数: `{fail_count}/{len(proxies)}`\n"
            f"• 触发时间: `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`"
        )
        send_telegram_notification(update_msg)
        
        logging.info("\n" + "="*40)
        logging.info(f"触发更新: {codes_str}")
        try:
            result = subprocess.run(
                ['python', 'cfst.py', codes_str],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            # 发送成功通知
            success_msg = format_telegram_message(
                "更新成功",
                f"• 地区代码: `{codes_str}`\n"
                f"• 输出结果:\n```\n{result.stdout[:1000]}```"
            )
            send_telegram_notification(success_msg)
            logging.info(f"🔄 更新成功\n输出结果:\n{result.stdout}")
        except subprocess.CalledProcessError as e:
            # 发送失败通知
            error_msg = format_telegram_message(
                "更新失败",
                f"• 地区代码: `{codes_str}`\n"
                f"• 错误信息:\n```\n{e.stderr[:1000]}```"
            )
            send_telegram_notification(error_msg)
            logging.error(f"❌ 更新失败\n错误信息:\n{e.stderr}")
        except FileNotFoundError:
            error_msg = format_telegram_message(
                "脚本未找到",
                "更新脚本 'cfst.py' 未找到"
            )
            send_telegram_notification(error_msg)
            logging.error("❌ 更新脚本 'cfst.py' 未找到")

if __name__ == "__main__":
    main()
