import socket
import os
import sys
from itertools import groupby

def check_proxy(host, port=443, timeout=1, retries=3):
    """
    检测代理端口连通性
    :param host: 代理域名
    :param port: 检测端口
    :param timeout: 超时时间（秒）
    :param retries: 重试次数
    :return: True=成功, False=失败
    """
    failed = 0
    for _ in range(retries):
        try:
            with socket.create_connection((host, port), timeout=timeout):
                pass
            return True  # 只要有一次成功立即返回
        except (socket.timeout, ConnectionRefusedError, OSError):
            failed += 1
        except Exception as e:
            print(f"检测 {host} 时发生未知错误: {str(e)}")
            failed += 1
    return failed == retries  # 全部重试失败返回False

def main():
    # 定义代理配置（与原始Shell脚本一致）
    proxies = {
        "proxy.hk.616049.xyz": "HKG",
        "proxy.us.616049.xyz": "LAX",
        "proxy.de.616049.xyz": "FRA",
        "proxy.sg.616049.xyz": "SIN",
        "proxy.jp.616049.xyz": "NRT"
    }

    # 执行检测
    failed_nodes = []
    for host, code in proxies.items():
        if check_proxy(host):
            print(f"✅ {host} 连接正常")
        else:
            print(f"❗ {host} 检测失败")
            failed_nodes.append(code)

    # 生成唯一地区代码
    unique_codes = list(set(failed_nodes))  # 去重
    unique_codes.sort()  # 排序

    # 触发更新逻辑
    if unique_codes:
        codes_str = ",".join(unique_codes)
        print(f"触发更新: {codes_str}")
        # 调用外部更新脚本（假设 cfstfd.py 在相同目录）
        os.system(f"python cfstfd.py {codes_str}")
    else:
        print("所有节点均正常")

if __name__ == "__main__":
    main()