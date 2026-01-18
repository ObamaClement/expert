import logging
import os
import sys

def setup_logging():
    """
    Configure le logging pour écrire dans un fichier et sur la console.
    """
    # Créer le dossier de logs s'il n'existe pas
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    log_file = os.path.join(log_dir, "simulation.log")

    # Créer un logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # Empêcher les double logs si la fonction est appelée plusieurs fois
    if logger.hasHandlers():
        logger.handlers.clear()

    # Formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - [%(levelname)s] - %(message)s'
    )

    # Handler pour écrire dans le fichier
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Handler pour afficher aussi dans la console (utile pour Render)
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    logging.info("=" * 50)
    logging.info("Logging configuré. Les logs seront écrits ici et dans le fichier.")
    logging.info("=" * 50)