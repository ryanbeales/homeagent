
import logging
import sys

def setup_logging():
    """Configures the application logger."""
    
    # Create logger
    logger = logging.getLogger("HomeAgent")
    logger.setLevel(logging.INFO)
    
    # Create console handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(funcName)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Add formatter to handler
    handler.setFormatter(formatter)
    
    # Add handler to logger
    logger.addHandler(handler)
    
    # Configure root logger to capture library logs if needed, 
    # but strictly we want our app logs to be formatted nicely.
    # We can also set uvicorn logging to follow our format if desired, 
    # but simpler to just configure our logger for now.
    
    return logger

# Singleton logger instance
logger = setup_logging()
