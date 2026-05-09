import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    """Application settings and configuration"""
    
    # OpenAI Configuration
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    
    # AWS Configuration
    AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
    AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
    S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
    
    # Application Configuration
    OUTPUT_DIR = os.getenv("OUTPUT_DIR", "output")
    WEBSITE_DOMAIN = os.getenv("WEBSITE_DOMAIN", "mywebsite.s3.amazonaws.com")

    # CORS — comma-separated allowed origins, e.g.:
    #   CORS_ORIGINS=https://app.yourdomain.com,https://admin.yourdomain.com
    # Leave blank (default) to allow localhost only in dev.
    # Set to * only if you explicitly need a public API.
    _cors_raw = os.getenv("CORS_ORIGINS", "")
    CORS_ORIGINS: list = (
        [o.strip() for o in _cors_raw.split(",") if o.strip()]
        if _cors_raw.strip()
        else ["http://localhost:8000", "http://localhost:3000", "http://127.0.0.1:8000"]
    )

    # CrewAI Configuration
    VERBOSE_MODE = os.getenv("VERBOSE_MODE", "true").lower() == "true"
    
    @classmethod
    def validate(cls):
        """Validate that required settings are configured"""
        if not cls.OPENAI_API_KEY:
            print("⚠️  OPENAI_API_KEY is not set. Please add it to your .env file before generating websites.")
        
        os.makedirs(cls.OUTPUT_DIR, exist_ok=True)

settings = Settings()