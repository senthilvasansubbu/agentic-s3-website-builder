import os
import boto3
from typing import Optional
from config.settings import settings

class S3Uploader:
    """Handle S3 uploads for generated websites"""
    
    def __init__(self):
        self.s3_client = None
        self.bucket_name = settings.S3_BUCKET_NAME
        self._initialize_s3()
    
    def _initialize_s3(self):
        """Initialize S3 client if credentials are available"""
        if settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
            try:
                self.s3_client = boto3.client(
                    's3',
                    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                    region_name=settings.AWS_REGION
                )
                print("✅ S3 client initialized successfully")
            except Exception as e:
                print(f"⚠️  Failed to initialize S3 client: {e}")
        else:
            print("⚠️  AWS credentials not configured. S3 uploads will be skipped.")
    
    def upload_file(self, file_path: str, s3_key: Optional[str] = None) -> Optional[str]:
        """
        Upload a file to S3

        Args:
            file_path: Path to the file to upload
            s3_key: S3 object key (if None, uses filename)

        Returns:
            S3 URL if successful, None otherwise
        """
        if not self.s3_client or not self.bucket_name:
            print("⚠️  S3 upload skipped: credentials not configured")
            return None
        
        try:
            if not s3_key:
                s3_key = file_path.split('/')[-1]
            
            # Determine content type
            content_type = 'text/html' if s3_key.endswith('.html') else 'text/plain'
            
            self.s3_client.upload_file(
                file_path,
                self.bucket_name,
                s3_key,
                ExtraArgs={'ContentType': content_type}
            )
            
            s3_url = f"https://{self.bucket_name}.s3.amazonaws.com/{s3_key}"
            print(f"✅ File uploaded to S3: {s3_url}")
            return s3_url
        
        except Exception as e:
            print(f"❌ Failed to upload to S3: {e}")
            return None
    
    def upload_directory(self, directory_path: str, s3_prefix: str = "") -> list:
        """
        Upload all files in a directory to S3

        Args:
            directory_path: Path to the directory
            s3_prefix: Prefix for S3 keys

        Returns:
            List of uploaded S3 URLs
        """
        if not self.s3_client or not self.bucket_name:
            print("⚠️  S3 upload skipped: credentials not configured")
            return []
        
        uploaded_urls = []
        
        try:
            for file_name in os.listdir(directory_path):
                file_path = os.path.join(directory_path, file_name)
                
                if os.path.isfile(file_path):
                    s3_key = f"{s3_prefix}/{file_name}".lstrip('/')
                    url = self.upload_file(file_path, s3_key)
                    if url:
                        uploaded_urls.append(url)
        
        except Exception as e:
            print(f"❌ Failed to upload directory: {e}")
        
        return uploaded_urls

# Create a global uploader instance
uploader = S3Uploader()