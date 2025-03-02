import socket
import logging
import argparse
from typing import Dict, List
import concurrent.futures
import subprocess

# 配置日志系统
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('proxy_check.log'),
        logging.StreamHandler()
    ]
)

def check_proxy(host: str, port: int, timeout: float, retries: int) -> bool:
    """检测代理端口连通性（支持重试机制）"""
    for attempt in range(retries):
        try:
            with socket.create_connection((host, port), timeout=timeout):
                logging.debug(f"{host}:{port} 第{attempt+1}次连接成功")
                return True
        except (socket.timeout, ConnectionRefusedError, OSError) as e:
            logging.debug(f"{host}:{port} 第{attempt+1}次连接失败: {str(e)}")
        except Exception as e:
            logging.error(f"检测 {host}:{port} 时发生未知错误: {str(e)}")
    return False

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

    failed_nodes: List[str] = []

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
                if future.result():
                    logging.info(f"✅ {host}:{args.port} 连接正常")
                else:
                    logging.error(f"❗ {host}:{args.port} 检测失败")
                    failed_nodes.append(code)
            except Exception as e:
                logging.error(f"检测 {host}:{args.port} 时发生异常: {e}")
                failed_nodes.append(code)

    # 处理失败节点并触发更新
    unique_codes = sorted({code for code in failed_nodes})  # 去重并排序

    if unique_codes:
        codes_str = ",".join(unique_codes)
        logging.info(f"触发更新: {codes_str}")
        try:
            result = subprocess.run(
                ['python', 'cfst.py', codes_str],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            logging.info(f"更新成功，输出：{result.stdout}")
        except subprocess.CalledProcessError as e:
            logging.error(f"更新失败，错误码：{e.returncode}\n错误信息：{e.stderr}")
        except FileNotFoundError:
            logging.error("更新脚本 'cfstfd.py' 未找到")
    else:
        logging.info(f"所有节点在端口 {args.port} 均正常，无需更新")

if __name__ == "__main__":
    main()
