import sys
import logging
import requests
import signal
import time
from datetime import datetime
from environs import Env
from mysql import connector


env = Env()
env.read_env()


class Config:
    prometheus_api_url = env("PROMETHEUS_API_URL")
    scrape_interval = env.int("SCRAPE_INTERVAL", 60)
    log_level = env.log_level("LOG_LEVEL", logging.INFO)

    mysql_host = env("MYSQL_HOST")
    mysql_user = env("MYSQL_USER", "root")
    mysql_password = env("MYSQL_PASSWORD", "1234")
    mysql_db_name = env("MYSQL_DB_NAME", "sla")


def connect_to_db(config: Config, attempts: int = 3, delay: int = 5):
    attempt = 1

    while attempt < attempts + 1:
        try:
            return connector.connect(
                host=config.mysql_host,
                user=config.mysql_user,
                passwd=config.mysql_password,
                auth_plugin="mysql_native_password",
                db="mysql",
            )
        except (connector.Error, IOError) as err:
            if attempt == attempts:
                logging.info(f"Failed to connect, exiting without a connection: {err}")
                return None

            logging.info(f"Connection failed: {err}. Retrying {attempt}/{attempts-1}")
            time.sleep(delay)
            attempt += 1
    return None


class Mysql:
    def __init__(self, config: Config) -> None:
        logging.info("Connecting to db")

        self.connection = connect_to_db(config, 5, 10)
        self.table_name = "indicators"

        logging.info("Starting migration")

        self.cursor = self.connection.cursor()
        self.cursor.execute(f"CREATE DATABASE IF NOT EXISTS {config.mysql_db_name}")

        self.cursor.execute(f"USE {config.mysql_db_name}")

        self.cursor.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {self.table_name} (
                datetime datetime not null default NOW(),
                name varchar(255) not null,
                slo float(4) not null,
                value float(4) not null,
                is_bad bool not null default false
            ) 
            """
        )

        self.cursor.execute(f"ALTER TABLE {self.table_name} ADD INDEX (datetime)")
        self.cursor.execute(f"ALTER TABLE {self.table_name} ADD INDEX (name)")

    def save_indicator(self, name, slo, value, is_bad=False, time=None) -> None:
        query = f"INSERT INTO {self.table_name} (name, slo, value, is_bad, datetime) VALUES (%s, %s, %s, %s, %s)"
        values = (name, slo, value, int(is_bad), time)
        self.cursor.execute(query, values)
        self.connection.commit()


class PrometheusRequest:
    def __init__(self, config: Config) -> None:
        self.prometheus_api_url = config.prometheus_api_url

    def last_value(self, query, time, default):
        try:
            response = requests.get(
                f"{self.prometheus_api_url}/api/v1/query",
                params={"query": query, "time": time},
            )
            content = response.json()

            if not content or len(content["data"]["result"]) == 0:
                return default

            return content["data"]["result"][0]["value"][1]

        except Exception as err:
            logging.error(err)
            return default


def setup_logging(config: Config) -> None:
    logging.basicConfig(
        stream=sys.stdout,
        level=config.log_level,
        format="%(asctime)s %(levelname)s:%(message)s",
    )


def main():
    config = Config()
    setup_logging(config)
    db = Mysql(config)
    prom = PrometheusRequest(config)

    logging.info("Starting SLA checker")

    while True:
        logging.debug("Run prober")

        unix_timestamp = int(time.time())
        date_format = datetime.utcfromtimestamp(unix_timestamp).strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        value = prom.last_value(
            "increase(prober_create_user_scenario_success_total[1m])", unix_timestamp, 0
        )
        value = int(float(value))

        try:
            db.save_indicator(
                name="prober_create_user_scenario_success_total",
                slo=1,
                value=value,
                is_bad=value < 1,
                time=date_format,
            )
        except Exception as err:
            logging.error(err)

        value = prom.last_value(
            "increase(prober_create_user_scenario_fail_total[1m])", unix_timestamp, 100
        )
        value = int(float(value))
        try:
            db.save_indicator(
                name="prober_create_user_scenario_fail_total",
                slo=0,
                value=value,
                is_bad=value > 0,
                time=date_format,
            )
        except Exception as err:
            logging.error(err)

        value = prom.last_value(
            "prober_create_user_scenario_duration_seconds", unix_timestamp, 2
        )
        value = float(value)
        try:
            db.save_indicator(
                name="prober_create_user_scenario_duration_seconds",
                slo=0.1,
                value=value,
                is_bad=value > 0.1,
                time=date_format,
            )
        except Exception as err:
            logging.error(err)

        logging.debug(f"Waiting {config.scrape_interval} seconds for next loop")
        time.sleep(config.scrape_interval)


def terminate(signal, frame) -> None:
    print("Terminating")
    sys.exit(0)


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, terminate)
    main()
