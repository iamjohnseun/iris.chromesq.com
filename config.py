import os

class Config:
    DEBUG = os.getenv('DEBUG', False)
    MAX_QUESTION_LENGTH = 100 # Maximum length of a question
    MAX_INTENT_LENGTH = 30 # Maximum length for intent name
    MAX_UTTERANCE_LENGTH = 55 # Maximum length for utterances
    MAX_BATCH_SIZE = 1 # Maximum number of questions to process in a single batch
    FALLBACK_MODE = True  # Enable fallback processing
    MIN_SENTENCES = 10  # Minimum sentences to process
    MAX_SENTENCES = 200 # Maximum number of sentences to generate
    MAX_PAGES = 20 # Maximum number of pages to crawl
    SCRAPING_MAX_DEPTH = int(os.getenv('SCRAPING_MAX_DEPTH', 5))
    SCRAPING_DELAY = float(os.getenv('SCRAPING_DELAY', 1.0))
    SCRAPING_DELAY_MAX = float(os.getenv('SCRAPING_DELAY_MAX', 3.0))  # Maximum delay for random backoff
    REQUEST_TIMEOUT = (5, 15)  # (Connect timeout, Read timeout)
    CACHE_ENABLED = os.getenv('CACHE_ENABLED', True)
    CACHE_TIMEOUT = int(os.getenv('CACHE_TIMEOUT', 3600))  # 1 hour
    MIN_WORDS_PER_ELEMENT = 3  # Minimum words for a content element to be valid
    
    # Content extraction configuration
    CONTENT_TAGS = ['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'td', 'article', 'section']
    
    # Elements to exclude
    EXCLUDED_ELEMENTS = ['script', 'style', 'meta', 'noscript', 'header', 'footer', 
        'nav', 'aside', 'iframe', 'svg', 'path', 'form']
    EXCLUDED_CLASSES = ['nav', 'footer', 'header', 'sidebar', 'menu', 'cookie', 'popup', 'modal']
    EXCLUDED_IDS = ['nav', 'footer', 'header', 'sidebar', 'menu', 'cookie-banner', 'popup']
    EXCLUDED_PATTERNS = ['login', 'signup', 'cart', 'checkout', 'account']
    EXCLUDED_EXTENSIONS = ('.pdf', '.jpg', '.jpeg', '.png', '.gif', '.doc', '.docx', 
                         '.xls', '.xlsx', '.zip', '.rar', '.exe', '.mp3', '.mp4')
    
    # User agent for the bot
    USER_AGENT = 'Mozilla/5.0 (compatible; IrisBot/1.0; +https://iris.chromesq.com)'
    
    # Memory management
    TORCH_THREADS = 2 # Number of threads for PyTorch
    MEMORY_THRESHOLD = 0.8  # 80% memory usage threshold
    MAX_MEMORY_USAGE = 0.85  # 85% memory threshold for scraping
    MAX_CONTENT_LENGTH = 8 * 1024 * 1024  # 8 MB
