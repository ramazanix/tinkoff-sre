import sys
from requests import Session
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import logging
import signal
import time
from environs import Env
from prometheus_client import start_http_server, Gauge, Counter


PROBER_CREATE_USER_SCENARIO_TOTAL = Counter(
    "prober_create_user_scenario_total",
    "Total counts of runs the create user scenario to oncall API",
)

PROBER_CREATE_USER_SCENARIO_SUCCESS_TOTAL = Counter(
    "prober_create_user_scenario_success_total",
    "Total counts of success runs the create user scenario to oncall API",
)

PROBER_CREATE_USER_SCENARIO_FAIL_TOTAL = Counter(
    "prober_create_user_scenario_fail_total",
    "Total counts of fail runs the create user scenario to oncall API",
)

PROBER_CREATE_USER_SCENARIO_DURATION_SECONDS = Gauge(
    "prober_create_user_scenario_durations_seconds",
    "Duration in seconds of runs the create user scenario to oncall API",
)

env = Env()
env.read_env()

session = Session()
retry = Retry(connect=3, backoff_factor=2)
adapter = HTTPAdapter(max_retries=retry)
session.mount("http://", adapter)


class Config:
    oncall_exporter_api_url = env("ONCALL_EXPORTER_API_URL")
    oncall_exporter_scrape_interval = env.int("ONCALL_EXPORTER_SCRAPE_INTERVAL", 30)
    oncall_exporter_log_level = env.log_level("ONCALL_EXPORTER_LOG_LEVEL", logging.INFO)
    oncall_exporter_metrics_port = env.int("ONCALL_EXPORTER_METRICS_PORT", 9081)


class OncallProberClient:
    def __init__(self, config: Config) -> None:
        self.oncall_api_url = config.oncall_exporter_api_url

    def probe(self) -> None:
        PROBER_CREATE_USER_SCENARIO_TOTAL.inc()
        logging.debug("trying create user")

        username = "test_prober_user"

        start = time.perf_counter()

        try:
            create_request = session.post(
                f"{self.oncall_api_url}/users", json={"name": username}
            )

        except Exception as err:
            logging.error(err)
            PROBER_CREATE_USER_SCENARIO_FAIL_TOTAL.inc()

        finally:
            try:
                delete_request = session.delete(
                    f"{self.oncall_api_url}/users/{username}"
                )

            except Exception as err:
                logging.error(err)

        try:
            if (
                create_request
                and create_request.status_code == 200
                and delete_request
                and delete_request.status_code == 200
            ):
                PROBER_CREATE_USER_SCENARIO_SUCCESS_TOTAL.inc()

            else:
                PROBER_CREATE_USER_SCENARIO_FAIL_TOTAL.inc()

        except Exception as err:
            logging.error(err)
            PROBER_CREATE_USER_SCENARIO_FAIL_TOTAL.inc()

        duration = time.perf_counter() - start

        PROBER_CREATE_USER_SCENARIO_DURATION_SECONDS.set(duration)

    @staticmethod
    def setup_logging(config: Config) -> None:
        logging.basicConfig(
            stream=sys.stdout,
            level=config.oncall_exporter_log_level,
            format="%(asctime)s %(levelname)s:%(message)s",
        )


def main() -> None:
    config = Config()
    client = OncallProberClient(config)

    client.setup_logging(config)

    logging.info(f"Starting prober on port: {config.oncall_exporter_metrics_port}")
    start_http_server(config.oncall_exporter_metrics_port)

    while True:
        logging.debug("Running prober")
        client.probe()

        logging.debug(
            f"Waiting {config.oncall_exporter_scrape_interval} seconds for next loop"
        )
        time.sleep(config.oncall_exporter_scrape_interval)


def terminate(signal, frame) -> None:
    print("Terminating")
    sys.exit(0)


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, terminate)
    main()
