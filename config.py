from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load environment variables from a .env file
load_dotenv()


class Settings(BaseSettings):
    influxdb_url: str
    influxdb_token: str
    influxdb_org: str
    influxdb_bucket: str
    secret_key: str

    class Config:
        env_file = ".env"  # Specifies the .env file to load variables from
        env_file_encoding = "utf-8"


# Example usage
settings = Settings()
print(settings.influxdb_url)
