import os
import requests
import logging
import sys

# 新增常量定义
LOG_PATH = "logs/dns_update_ip.log"

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH),
        logging.StreamHandler()
    ]
)

# 从环境变量获取 Cloudflare API 配置信息
API_KEY = os.getenv("CLOUDFLARE_API_KEY")
EMAIL = os.getenv("CLOUDFLARE_EMAIL")
ZONE_ID = os.getenv("CLOUDFLARE_ZONE_ID")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# 确保从环境变量中获取到了这些信息
if not all([API_KEY, EMAIL, ZONE_ID, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID]):
    logging.error("缺少必要的配置信息，请确保在 GitHub Secrets 中设置了 CLOUDFLARE_API_KEY, CLOUDFLARE_EMAIL, CLOUDFLARE_ZONE_ID, TELEGRAM_BOT_TOKEN 和 TELEGRAM_CHAT_ID。")
    sys.exit(1)

# 发送消息到 Telegram
def send_to_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message
    }
    try:
        response = requests.post(url, json=payload)
        if response.status_code != 200:
            logging.error(f"发送消息到 Telegram 失败: {response.status_code}, {response.text}")
    except requests.exceptions.RequestException as e:
        logging.error(f"请求失败: {e}")

# 自定义日志处理器，将日志信息发送到 Telegram
class TelegramLogHandler(logging.Handler):
    def emit(self, record):
        log_entry = self.format(record)
        send_to_telegram(log_entry)

# 添加 Telegram 日志处理器
telegram_handler = TelegramLogHandler()
telegram_handler.setLevel(logging.INFO)
telegram_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
logging.getLogger().addHandler(telegram_handler)

# 域名与标记映射关系（扩展机场三字码）
LOCATION_TO_DOMAIN = {
    # 示例映射（可根据实际需求调整）
    # 美国
    "🇺🇸SJC": "us.616049.xyz",  # 圣何塞
    "🇺🇸LAX": "us.616049.xyz",  # 洛杉矶
    "🇺🇸SEA": "us.616049.xyz",  # 西雅图
    "🇺🇸JFK": "us.616049.xyz",  # 纽约 - 肯尼迪国际机场
    "🇺🇸ORD": "us.616049.xyz",  # 芝加哥 - 奥黑尔国际机场
    "🇺🇸IAD": "us.616049.xyz",  # 华盛顿杜勒斯国际机场
    "🇺🇸EWR": "us.616049.xyz",  # 纽瓦克自由国际机场
    "🇺🇸CMH": "us.616049.xyz",  # 哥伦布国际机场
    "🇺🇸PDX": "us.616049.xyz",  # 俄勒冈州 - 波特兰国际机场
    "🇺🇸US": "us.616049.xyz",  # 美国

    # 加拿大
    "🇨🇦YUL": "ca.616049.xyz",  # 蒙特利尔皮埃尔·埃利奥特·特鲁多国际机场
    "🇨🇦YYZ": "ca.616049.xyz",  # 多伦多皮尔逊国际机场
    "🇨🇦YVR": "ca.616049.xyz",  # 温哥华国际机场
    "🇨🇦CA": "ca.616049.xyz",  # 加拿大

    # 德国
    "🇩🇪FRA": "de.616049.xyz",  # 法兰克福机场
    "🇩🇪DE": "de.616049.xyz",  # 德国

    # 法国
    "🇫🇷CDG": "fr.616049.xyz",  # 巴黎戴高乐机场
    "🇫🇷FR": "fr.616049.xyz",  # 法国
    
    # 英国
    "🇬🇧LHR": "uk.616049.xyz",  # 伦敦
    "🇬🇧UK": "uk.616049.xyz",  # 英国

    # 荷兰
    "🇳🇱AMS": "nl.616049.xyz",  # 阿姆斯特丹史基浦机场
    "🇳🇱NL": "nl.616049.xyz",  # 荷兰
    
    # 日本
    "🇯🇵NRT": "jp.616049.xyz",  # 东京成田
    "🇯🇵HND": "jp.616049.xyz",  # 东京羽田
    "🇯🇵JP": "jp.616049.xyz",  # 日本

    # 香港
    "🇭🇰HKG": "hk.616049.xyz",  # 香港国际机场
    "🇭🇰HK": "hk.616049.xyz",  # 香港

    # 韩国
    "🇰🇷ICN": "kr.616049.xyz",  # 仁川国际机场
    "🇰🇷KR": "kr.616049.xyz",  # 韩国

    # 台湾
    "🇹🇼TPE": "tw.616049.xyz",  # 台北桃园机场
    "🇹🇼TW": "tw.616049.xyz",  # 台湾

    # 新加坡
    "🇸🇬SIN": "sg.616049.xyz",   # 樟宜机场
    "🇸🇬SG": "sg.616049.xyz",  # 新加坡

    # 印度
    "🇮🇳BOM": "in.616049.xyz",  # 孟买国际机场
    "🇮🇳IN": "in.616049.xyz",  # 印度

    # 瑞典
    "🇸🇪ARN": "se.616049.xyz",  # 斯德哥尔摩阿兰达机场
    "🇸🇪SE": "se.616049.xyz",  # 瑞典

    # 芬兰
    "🇫🇮HEL": "fi.616049.xyz",  # 赫尔辛基
    "🇫🇮FI": "fi.616049.xyz",  # 芬兰

    # 巴西
    "🇧🇷GRU": "br.616049.xyz",  # 圣保罗瓜鲁柳斯国际机场
    "🇧🇷BR": "br.616049.xyz",  # 巴西

    # 波兰
    "🇵🇱WAW": "pl.616049.xyz",  # 华沙
    "🇵🇱PL": "pl.616049.xyz",  # 波兰
    
    # 澳大利亚
    "🇦🇺SYD": "au.616049.xyz",  # 悉尼国际机场（澳大利亚）
    "🇦🇺AU": "au.616049.xyz",  # 澳大利亚
}

# 从 ip.txt 文件中读取前200个 IP 和标记
def get_ips_from_file(file_path, limit=200):
    ip_data = []
    try:
        with open(file_path, "r") as file:
            for line in file:
                if "#" in line:
                    ip, location = line.strip().split("#")
                    ip_data.append((ip.strip(), location.strip()))
                if len(ip_data) >= limit:
                    break
        return ip_data
    except FileNotFoundError:
        logging.error(f"文件未找到: {file_path}")
        return []

# 删除相同前缀的所有 DNS 记录（不保留任何记录）
def delete_dns_records_with_prefix(prefix):
    try:
        url = f"https://api.cloudflare.com/client/v4/zones/{ZONE_ID}/dns_records"
        headers = {
            "X-Auth-Email": EMAIL,
            "X-Auth-Key": API_KEY,
            "Content-Type": "application/json"
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        records = response.json().get("result", [])
        logging.info(f"找到 {len(records)} 条 DNS 记录，开始删除与 {prefix} 完全匹配的所有记录...")
        
        # 过滤出与给定前缀完全匹配的记录（例如 proxy.us）
        matching_records = [record for record in records if record["name"].startswith(prefix + ".")]
        
        # 删除所有匹配的记录
        if matching_records:
            for record in matching_records:  # 删除所有记录
                record_id = record["id"]
                delete_url = f"{url}/{record_id}"
                delete_response = requests.delete(delete_url, headers=headers)
                if delete_response.status_code == 200:
                    logging.info(f"已删除记录: {record['name']} -> {record['content']}")
                else:
                    logging.error(f"删除失败: {record['name']} -> {record['content']}, 错误信息: {delete_response.status_code}, {delete_response.text}")
        else:
            logging.info(f"没有需要删除的记录，{prefix} 前缀的记录数量为 0")
    except requests.exceptions.RequestException as e:
        logging.error(f"请求失败: {e}")
        sys.exit(1)
        
# 批量添加 DNS 记录
def add_dns_records_bulk(ip_data):
    url = f"https://api.cloudflare.com/client/v4/zones/{ZONE_ID}/dns_records"
    headers = {
        "X-Auth-Email": EMAIL,
        "X-Auth-Key": API_KEY,
        "Content-Type": "application/json"
    }
    # 记录已经删除过哪些前缀
    deleted_prefixes = set()
    # 记录每个前缀已经添加的记录数量
    prefix_counters = {}

    for ip, location in ip_data:
        domain = LOCATION_TO_DOMAIN.get(location)
        if domain:
            # 提取前缀（例如 "us.616049.xyz" 的前缀是 "us"）
            prefix = ".".join(domain.split(".")[:1])  # 提取第一部分（us）
            # 如果该前缀没有被删除过，则删除该前缀的所有 DNS 记录
            if prefix not in deleted_prefixes:
                delete_dns_records_with_prefix(prefix)
                deleted_prefixes.add(prefix)  # 标记该前缀已删除
                prefix_counters[prefix] = 0  # 初始化计数器

            # 如果该前缀的记录数量已经达到 5 条，则跳过
            if prefix_counters.get(prefix, 0) >= 5:
                logging.info(f"前缀 {prefix} 的记录数量已达到 5 条，跳过添加: {domain} -> {ip}")
                continue

            data = {
                "type": "A",
                "name": domain,
                "content": ip,
                "ttl": 1,
                "proxied": False
            }
            try:
                response = requests.post(url, headers=headers, json=data)
                if response.status_code == 200:
                    logging.info(f"添加成功: {domain} -> {ip}")
                    prefix_counters[prefix] = prefix_counters.get(prefix, 0) + 1  # 增加计数器
                elif response.status_code == 409:
                    logging.info(f"记录已存在: {domain} -> {ip}")
                else:
                    logging.error(f"添加失败: {domain} -> {ip}, 错误信息: {response.status_code}, {response.text}")
            except requests.exceptions.RequestException as e:
                logging.error(f"请求失败: {e}")
        else:
            logging.warning(f"未找到标记 {location} 对应的域名映射，跳过。")

# 新增清理函数
def clear_log_file():
    try:
        if os.path.exists(LOG_PATH):
            os.remove(LOG_PATH)
            logging.info(f"已清理旧日志文件: {LOG_PATH}")
    except OSError as e:
        logging.error(f"清理日志文件失败: {e.strerror}")

# 主程序
if __name__ == "__main__":
    clear_log_file()  # 执行前清理旧日志
    # 添加新的 DNS 记录
    ip_data = get_ips_from_file("cfip/ip.txt")
    if not ip_data:
        logging.error("未读取到 IP 数据，请检查 ip.txt 文件格式是否正确。")
    else:
        add_dns_records_bulk(ip_data)