import time
import glob
from prometheus_client.core import GaugeMetricFamily, REGISTRY, CounterMetricFamily
from prometheus_client import start_http_server


class CustomCollector(object):
    def __init__(self):
        self.requests = 0
        pass

    def collect(self):
        g = GaugeMetricFamily("cpu_core_temp", 'Help text', labels=['instance'])
        for file in glob.glob('/sys/class/thermal/thermal_zone*/temp'):
            cpu_idx = file.split('/')[4][-1]
            with open(file, 'r') as f:
                temp = f.readline()[:-1]
                g.add_metric([f'CPU-{cpu_idx}'], float(temp) / 1000)
        yield g

        c = CounterMetricFamily("http_requests", 'Help text', labels=['app'])
        c.add_metric(['example'], self.requests)
        self.requests += 1
        yield c


if __name__ == '__main__':
    start_http_server(8000)
    REGISTRY.register(CustomCollector())
    while True:
        time.sleep(1)
