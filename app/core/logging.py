import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

# logger principal do projeto
logger = logging.getLogger("countlight")

# reduzir logs do uvicorn
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

# manter erros importantes
logging.getLogger("uvicorn.error").setLevel(logging.INFO)

# reduzir logs de requests (opcional)
logging.getLogger("urllib3").setLevel(logging.WARNING)