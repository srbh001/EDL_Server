from pydantic_settings import BaseSettings
import os
import environ

env = environ.Env()
environ.Env.read_env()


class Settings(BaseSettings):
    influxdb_url: str = os.getenv("INFLUXDB_URL")
    influxdb_token: str = os.getenv("INFLUXDB_TOKEN")
    influxdb_org: str = os.getenv("INFLUXDB_ORG")
    influxdb_bucket: str = os.getenv("INFLUXDB_BUCKET")
    secret_key: str = os.getenv("SECRET_KEY")


settings = Settings()
