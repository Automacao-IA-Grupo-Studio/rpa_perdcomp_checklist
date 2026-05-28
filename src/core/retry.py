import time
import random
import functools
from src.core.logger import logger

def retry_on_exception(retries=3, initial_delay=2, backoff=2, exceptions=(Exception,)):
    """
    Decorador profissional para retry com backoff exponencial e jitter.
    
    Args:
        retries: Número máximo de tentativas
        initial_delay: Atraso inicial em segundos
        backoff: Fator de multiplicação para o atraso
        exceptions: Tupla de exceções que disparam o retry
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            m_retries, m_delay = retries, initial_delay
            while m_retries > 1:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    # Adiciona jitter (variação aleatória) para evitar "thundering herd"
                    jitter = random.uniform(0, 0.5 * m_delay)
                    actual_delay = m_delay + jitter
                    
                    logger.warning(
                        f"Falha em '{func.__name__}': {str(e)[:100]}. "
                        f"Tentativa {retries - m_retries + 1}/{retries}. "
                        f"Reiniciando em {actual_delay:.1f}s..."
                    )
                    
                    time.sleep(actual_delay)
                    m_retries -= 1
                    m_delay *= backoff
            
            # Última tentativa sem capturar exceção (deixa subir)
            return func(*args, **kwargs)
        return wrapper
    return decorator
