from data_ingestion.mqtt_client import start
from data_ingestion.logger import logger

if __name__ == "__main__":
    logger.info("Serviço de ingestão iniciado")
    start()
