# -*- coding: utf-8 -*-
"""
代理:https://jahttp.zhimaruanjian.com/getapi/

@desc: adata 请求工具类
@author: 1nchaos
@time:2023/3/30
@log: 封装请求次数
"""

import threading
import time
from collections import deque
from urllib.parse import urlparse

import requests


class RateLimiter:
    """频率限制器，用于限制同一域名的请求频率"""
    _lock = threading.Lock()
    _domain_requests = {}
    _default_limit = 30
    _domain_limits = {}

    def __new__(cls, *args, **kwargs):
        if not hasattr(cls, '_instance'):
            cls._instance = super(RateLimiter, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def set_default_limit(self, limit):
        """设置默认频率限制（每分钟请求数）"""
        with self._lock:
            self._default_limit = limit

    def set_domain_limit(self, domain, limit):
        """设置特定域名的频率限制（每分钟请求数）"""
        with self._lock:
            self._domain_limits[domain] = limit

    def _get_limit(self, domain):
        """获取域名的频率限制"""
        return self._domain_limits.get(domain, self._default_limit)

    def acquire(self, url):
        """获取请求许可，需要等待时自动等待"""
        domain = urlparse(url).netloc
        now = time.time()
        one_minute_ago = now - 60

        with self._lock:
            if domain not in self._domain_requests:
                self._domain_requests[domain] = deque()

            requests_queue = self._domain_requests[domain]
            
            while requests_queue and requests_queue[0] < one_minute_ago:
                requests_queue.popleft()

            limit = self._get_limit(domain)
            
            if len(requests_queue) >= limit:
                wait_time = requests_queue[0] - one_minute_ago
                time.sleep(wait_time)
                requests_queue.popleft()

            requests_queue.append(time.time())


class SunProxy(object):
    _data = {}
    _instance_lock = threading.Lock()
    _instance = None

    def __init__(self):
        pass

    def __new__(cls, *args, **kwargs):
        if not hasattr(SunProxy, "_instance") or SunProxy._instance is None:
            with SunProxy._instance_lock:
                if not hasattr(SunProxy, "_instance") or SunProxy._instance is None:
                    SunProxy._instance = super(SunProxy, cls).__new__(cls, *args, **kwargs)
        return SunProxy._instance

    @classmethod
    def set(cls, key, value):
        cls._data[key] = value

    @classmethod
    def get(cls, key):
        return cls._data.get(key)

    @classmethod
    def delete(cls, key):
        if key in cls._data:
            del cls._data[key]


class SunRequests(object):
    def __init__(self, sun_proxy: SunProxy = None, enable_rate_limit=True) -> None:
        super().__init__()
        self.sun_proxy = sun_proxy
        self.enable_rate_limit = enable_rate_limit
        self._rate_limiter = RateLimiter() if enable_rate_limit else None

    def set_default_limit(self, limit):
        """设置默认频率限制（每分钟请求数）"""
        if self._rate_limiter:
            self._rate_limiter.set_default_limit(limit)

    def set_domain_limit(self, domain, limit):
        """设置特定域名的频率限制（每分钟请求数）"""
        if self._rate_limiter:
            self._rate_limiter.set_domain_limit(domain, limit)

    def request(self, method='get', url=None, times=3, retry_wait_time=1588, proxies=None, wait_time=None, **kwargs):
        """
        简单封装的请求，参考requests，增加循环次数和次数之间的等待时间
        :param proxies: 代理配置
        :param method: 请求方法： get；post
        :param url: url
        :param times: 次数，int
        :param retry_wait_time: 重试等待时间，毫秒
        :param wait_time: 等待时间：毫秒；表示每个请求的间隔时间，在请求之前等待sleep，主要用于防止请求太频繁的限制。
        :param kwargs: 其它 requests 参数，用法相同
        :return: res
        """
        if self.enable_rate_limit and url and self._rate_limiter:
            self._rate_limiter.acquire(url)
        # 1. 获取设置代理
        proxies = self.__get_proxies(proxies)
        # 2. 请求数据结果
        res = None
        for i in range(times):
            if wait_time:
                time.sleep(wait_time / 1000)
            res = requests.request(method=method, url=url, proxies=proxies, **kwargs)
            if res.status_code in (200, 404):
                return res
            time.sleep(retry_wait_time / 1000)
            if i == times - 1:
                return res
        return res

    def __get_proxies(self, proxies):
        """
        获取代理配置
        """
        if proxies is None:
            proxies = {}
        is_proxy = SunProxy.get('is_proxy')
        ip = SunProxy.get('ip')
        proxy_url = SunProxy.get('proxy_url')
        if not ip and is_proxy and proxy_url:
            ip = requests.get(url=proxy_url).text.replace('\r\n', '') \
                .replace('\r', '').replace('\n', '').replace('\t', '')
        if is_proxy and ip:
            proxies = {'https': f"http://{ip}", 'http': f"http://{ip}"}
        return proxies


sun_requests = SunRequests()
rate_limiter = RateLimiter()
