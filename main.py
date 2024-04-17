import logging
import os
import socket
import sys
from subprocess import Popen, PIPE

import yaml
import requests
from enum import Enum


# 根据相对该文件位置读取当前目录下config.yml做为配置文件
def getConfigLocation():
    if getattr(sys, 'frozen', False):  # 判断程序是否被打包
        return os.path.join(os.path.dirname(sys.executable), 'config.yml')  # 获取打包后的目录
    else:
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.yml')


def getEffectiveIp():
    interfaces = socket.getaddrinfo(socket.gethostname(), None)
    for interface in interfaces:
        if interface[0] == socket.AF_INET:  # 检查地址族是否为 IPv4
            ip = str(interface[4][0])
            if ip.startswith("10."):
                return ip
    return ""


def get_ip():
    p = Popen("hostname -I", shell=True, stdout=PIPE)
    data = p.stdout.read()  # 获取命令输出内容
    data = str(data, encoding='UTF-8')  # 将输出内容编码成字符串
    ip_list = data.split(' ')  # 用空格分隔输出内容得到包含所有IP的列表
    if "\n" in ip_list:  # 发现有的系统版本输出结果最后会带一个换行符
        ip_list.remove("\n")
    ip = ""
    for i in ip_list:
        if i.startswith("10."):
            ip = i
    return ip


# 关于config文件中读取的内容
class ConfigKey(Enum):
    PASSWORD = "password"
    ACCOUNT = "account"
    CONNECT_TYPE = "connect"


class LinkTask:
    def initLogger(self):
        logger = logging.getLogger("school-link-log")
        # 创建一个formatter对象，指定日志的输出格式
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        # 创建一个handler对象，用来输出日志到文件，文件名为mylog.log，模式为追加
        file_handler = logging.FileHandler("LinkScript.log", mode="a")
        # 将formatter对象添加到file_handler对象中
        file_handler.setFormatter(formatter)
        # 创建一个handler对象，用来输出日志到控制台
        console_handler = logging.StreamHandler()
        # 将formatter对象添加到console_handler对象中
        console_handler.setFormatter(formatter)
        # 将file_handler对象和console_handler对象添加到logger对象中
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        # 设置logger对象的日志级别为DEBUG
        logger.setLevel(logging.DEBUG)
        self.__logger = logger

    def checkNetwork(self):
        for i in range(1, 100):
            try:
                sock = socket.create_connection(("10.110.6.251", "801"), timeout=10)
                self.__logger.info("网络连通 - 10.110.6.251:801")
                sock.close()
                return
            except socket.error as e:
                self.__logger.info("网络不通 - 10.110.6.251:801")

    def getLinkInfo(self):
        file = open(getConfigLocation(), "r", encoding="utf-8")
        config = yaml.load(file, Loader=yaml.FullLoader)
        self.__connectType = str(config[ConfigKey.CONNECT_TYPE.value]).strip()
        self.__logger.info("connectType: " + self.__connectType)
        self.__account = str(config[ConfigKey.ACCOUNT.value]).strip()
        self.__logger.info("account: " + self.__account)
        self.__password = str(config[ConfigKey.PASSWORD.value]).strip()
        self.__logger.info("password: " + self.__password)
        self.__ip = getEffectiveIp()
        if self.__ip == "":
            self.__logger.info("未能检测到10开始的有效ip")
            self.__ip = get_ip()
        self.__logger.info("connectIp: " + self.__ip)

    def wrapConnectRequest(self):
        cookie = str(requests.get("http://10.110.6.251:801/eportal/?c=Portal").cookies.get("PHPSESSID"))
        self.__cookie = {
            "PHPSESSID": f"{cookie}"
        }
        self.__logger.info("cookie: " + cookie)

        self.__params = {
            "c": "Portal",
            "a": "login",
            "login_method": "1",
            "user_account": f",0,{self.__account}{self.__connectType}",
            "user_password": f"{self.__password}",
            "wlan_user_ip": f"{self.__ip}",
        }
        self.__logger.info("params: " + str(self.__params.items()))
        self.__url = "http://10.110.6.251:801/eportal"
        self.__logger.info("url: " + self.__url)

    def tryConnect(self):
        result = requests.get(url=self.__url, params=self.__params, cookies=self.__params)
        msg = bytes(result.text, 'utf-8').decode('unicode_escape')
        self.__logger.info(msg)

    def __init__(self):
        self.__url = None
        self.__params = None
        self.__cookie = None
        self.__ip = None
        self.__logger = None
        self.__password = None
        self.__account = None
        self.__connectType = None

    def start(self):
        self.initLogger()
        self.checkNetwork()
        self.getLinkInfo()
        self.wrapConnectRequest()
        self.tryConnect()


def check_network(host, port):
    try:
        sock = socket.create_connection((host, port), timeout=4)
        print(f"网络连通 - {host}:{port}")
        sock.close()
    except socket.error as e:
        print(f"网络不通 - {host}:{port} - 错误: {e}")


if __name__ == '__main__':
    linkTask = LinkTask()
    linkTask.start()
