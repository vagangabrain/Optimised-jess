import onnxruntime as ort
import numpy as np
import aiohttp
from PIL import Image
import io
import os
import json
import time
import hashlib
import asyncio
from typing import Optional, Tuple

# GitHub raw content URLs for models
# For private repos, you need a GitHub Personal Access Token
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")  # Optional: for private repos
MODEL_REPO_BASE = "https://raw.githubusercontent.com/teamrocket43434/jessmodel/main"

# Primary model (original)
PRIMARY_ONNX_URL = f"{MODEL_REPO_BASE}/pokemon_cnn_v2.onnx"
PRIMARY_LABELS_URL = f"{MODEL_REPO_BASE}/labels_v2.json"

# Secondary model (new)
SECONDARY_ONNX_URL = f"{MODEL_REPO_BASE}/poketwo_pokemon_model.onnx"
SECONDARY_ONNX_DATA_URL = f"{MODEL_REPO_BASE}/poketwo_pokemon_model.onnx.data"
SECONDARY_METADATA_URL = f"{MODEL_REPO_BASE}/model_metadata.json"

# Local cache paths
CACHE_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), "model_cache")
PRIMARY_ONNX_PATH = os.path.join(CACHE_DIR, "pokemon_cnn_v2.onnx")
PRIMARY_LABELS_PATH = os.path.join(CACHE_DIR, "labels_v2.json")
SECONDARY_ONNX_PATH = os.path.join(CACHE_DIR, "poketwo_pokemon_model.onnx")
SECONDARY_ONNX_DATA_PATH = os.path.join(CACHE_DIR, "poketwo_pokemon_model.onnx.data")
SECONDARY_METADATA_PATH = os.path.join(CACHE_DIR, "model_metadata.json")


class PredictionCache:
    """Simple in-memory cache for predictions"""
    def __init__(self, max_size=1000, ttl_seconds=3600):  # 1 hour TTL
        self.cache = {}
        self.timestamps = {}
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds

    def _cleanup_expired(self):
        """Remove expired entries"""
        current_time = time.time()
        expired_keys = [
            key for key, timestamp in self.timestamps.items()
            if current_time - timestamp > self.ttl_seconds
        ]
        for key in expired_keys:
            self.cache.pop(key, None)
            self.timestamps.pop(key, None)

    def get(self, key: str) -> Optional[Tuple[str, str, str]]:
        """Get cached prediction if valid - returns (name, confidence, model_used)"""
        self._cleanup_expired()
        if key in self.cache:
            current_time = time.time()
            if current_time - self.timestamps[key] <= self.ttl_seconds:
                return self.cache[key]
            else:
                self.cache.pop(key, None)
                self.timestamps.pop(key, None)
        return None

    def set(self, key: str, value: Tuple[str, str, str]):
        """Cache a prediction - value is (name, confidence, model_used)"""
        self._cleanup_expired()

        if len(self.cache) >= self.max_size:
            oldest_key = min(self.timestamps.keys(), key=lambda k: self.timestamps[k])
            self.cache.pop(oldest_key, None)
            self.timestamps.pop(oldest_key, None)

        self.cache[key] = value
        self.timestamps[key] = time.time()


class ModelDownloader:
    """Handle downloading and caching models from GitHub"""
    
    @staticmethod
    async def download_file(url: str, dest_path: str, session: aiohttp.ClientSession):
        """Download a file from URL to destination path"""
        try:
            timeout = aiohttp.ClientTimeout(total=60, connect=10)
            
            # Add authentication header if GitHub token is provided (for private repos)
            headers = {}
            if GITHUB_TOKEN:
                headers['Authorization'] = f'token {GITHUB_TOKEN}'
            
            async with session.get(url, timeout=timeout, headers=headers) as response:
                if response.status == 401:
                    raise ValueError(f"Authentication failed. Check your GITHUB_TOKEN environment variable.")
                if response.status == 404:
                    raise ValueError(f"File not found: {url}. Check repository name and file path.")
                if response.status != 200:
                    raise ValueError(f"HTTP {response.status} error downloading {url}")
                
                content = await response.read()
                
                # Ensure directory exists
                os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                
                with open(dest_path, 'wb') as f:
                    f.write(content)
                
                print(f"✅ Downloaded: {os.path.basename(dest_path)}")
                return True
        except Exception as e:
            print(f"❌ Failed to download {url}: {e}")
            return False
    
    @staticmethod
    async def ensure_models_cached(session: aiohttp.ClientSession):
        """Download all required models if not cached"""
        os.makedirs(CACHE_DIR, exist_ok=True)
        
        downloads = [
            (PRIMARY_ONNX_URL, PRIMARY_ONNX_PATH),
            (PRIMARY_LABELS_URL, PRIMARY_LABELS_PATH),
            (SECONDARY_ONNX_URL, SECONDARY_ONNX_PATH),
            (SECONDARY_ONNX_DATA_URL, SECONDARY_ONNX_DATA_PATH),
            (SECONDARY_METADATA_URL, SECONDARY_METADATA_PATH),
        ]
        
        download_tasks = []
        for url, path in downloads:
            if not os.path.exists(path):
                print(f"Downloading {os.path.basename(path)}...")
                download_tasks.append(ModelDownloader.download_file(url, path, session))
            else:
                print(f"✓ Cached: {os.path.basename(path)}")
        
        if download_tasks:
            results = await asyncio.gather(*download_tasks)
            if not all(results):
                raise Exception("Failed to download some model files")


class Prediction:
    def __init__(self):
        self.cache = PredictionCache()
        self.primary_session = None
        self.secondary_session = None
        self.primary_class_names = None
        self.secondary_class_names = None
        self.secondary_metadata = None
        self.models_initialized = False
        # Rate limiting for Discord CDN
        self._cdn_semaphore = asyncio.Semaphore(3)  # Max 3 concurrent Discord CDN requests
        self._last_cdn_request = 0
        self._cdn_min_interval = 0.1  # Minimum 100ms between requests

    async def initialize_models(self, session: aiohttp.ClientSession):
        """Download and initialize both models"""
        if self.models_initialized:
            return
        
        print("Initializing prediction models...")
        
        # Download models if needed
        await ModelDownloader.ensure_models_cached(session)
        
        # Load primary model class names
        with open(PRIMARY_LABELS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                sorted_keys = sorted(data.keys(), key=lambda x: int(x))
                self.primary_class_names = [data[k].strip('"') for k in sorted_keys]
            elif isinstance(data, list):
                self.primary_class_names = [name.strip('"') for name in data]
            else:
                raise ValueError("labels_v2.json must be a list or dict")
        
        # Load secondary model metadata
        with open(SECONDARY_METADATA_PATH, "r", encoding="utf-8") as f:
            self.secondary_metadata = json.load(f)
            self.secondary_class_names = self.secondary_metadata["class_names"]
        
        # ONNX session options
        sess_opts = ort.SessionOptions()
        sess_opts.intra_op_num_threads = min(4, os.cpu_count())
        sess_opts.inter_op_num_threads = 1
        sess_opts.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
        sess_opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        providers = ["CPUExecutionProvider"]
        
        # Initialize primary model
        self.primary_session = ort.InferenceSession(
            PRIMARY_ONNX_PATH,
            sess_options=sess_opts,
            providers=providers
        )
        print(f"✅ Primary model initialized: {len(self.primary_class_names)} classes")
        
        # Initialize secondary model
        self.secondary_session = ort.InferenceSession(
            SECONDARY_ONNX_PATH,
            sess_options=sess_opts,
            providers=providers
        )
        print(f"✅ Secondary model initialized: {len(self.secondary_class_names)} classes")
        
        self.models_initialized = True

    def _generate_cache_key(self, url: str) -> str:
        """Generate cache key from URL"""
        return hashlib.md5(url.encode()).hexdigest()

    async def _rate_limit_cdn_request(self):
        """Apply rate limiting for Discord CDN requests"""
        async with self._cdn_semaphore:
            # Ensure minimum time between requests
            now = time.time()
            time_since_last = now - self._last_cdn_request
            if time_since_last < self._cdn_min_interval:
                await asyncio.sleep(self._cdn_min_interval - time_since_last)
            self._last_cdn_request = time.time()

    async def preprocess_image(self, url: str, session: aiohttp.ClientSession, 
                               width=224, height=224, max_retries=4):
        """Async image preprocessing with improved retry logic for Discord CDN
        
        Args:
            url: Image URL
            session: aiohttp session
            width: Target width (PIL uses width, height order)
            height: Target height
            max_retries: Number of retry attempts (increased to 4)
        """
        is_discord_cdn = 'cdn.discordapp.com' in url or 'media.discordapp.net' in url
        
        for attempt in range(max_retries):
            try:
                # Apply rate limiting for Discord CDN
                if is_discord_cdn:
                    await self._rate_limit_cdn_request()
                
                # Progressive timeout - longer for Discord CDN and later attempts
                if is_discord_cdn:
                    timeout_total = 15 + (attempt * 5)  # 15s, 20s, 25s, 30s
                    timeout_connect = 5 + (attempt * 2)  # 5s, 7s, 9s, 11s
                else:
                    timeout_total = 10 + (attempt * 3)
                    timeout_connect = 3 + attempt
                
                timeout = aiohttp.ClientTimeout(total=timeout_total, connect=timeout_connect)
                
                # Headers to avoid being blocked by Discord CDN
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Cache-Control': 'no-cache',
                    'Pragma': 'no-cache',
                }
                
                async with session.get(url, timeout=timeout, headers=headers) as response:
                    # Handle different error cases
                    if response.status == 429:  # Rate limited
                        retry_after = int(response.headers.get('Retry-After', 2))
                        if attempt < max_retries - 1:
                            print(f"[RATE-LIMIT] Waiting {retry_after}s before retry {attempt + 1}/{max_retries}")
                            await asyncio.sleep(retry_after)
                            continue
                        raise ValueError(f"Rate limited by Discord CDN after {max_retries} attempts")
                    
                    if response.status == 404:
                        # For Discord CDN, retry a few times as URLs can be temporarily unavailable
                        if is_discord_cdn and attempt < max_retries - 1:
                            delay = 1.0 * (2 ** attempt)  # Exponential backoff: 1s, 2s, 4s
                            print(f"[404] Retry {attempt + 1}/{max_retries} after {delay}s delay")
                            await asyncio.sleep(delay)
                            continue
                        raise ValueError(f"Image not found (404) - URL may be expired or deleted")
                    
                    if response.status in [502, 503, 504]:  # Server errors - retry
                        if attempt < max_retries - 1:
                            delay = 2.0 * (2 ** attempt)  # 2s, 4s, 8s
                            print(f"[{response.status}] Server error, retry {attempt + 1}/{max_retries} after {delay}s")
                            await asyncio.sleep(delay)
                            continue
                        raise ValueError(f"Server error {response.status} after {max_retries} attempts")
                    
                    if response.status != 200:
                        raise ValueError(f"HTTP {response.status} error fetching image")
                    
                    image_data = await response.read()
                
                # Validate we got actual image data
                if len(image_data) < 100:  # Too small to be a valid image
                    raise ValueError("Received invalid/empty image data")
                
                # Try to process the image
                try:
                    image = Image.open(io.BytesIO(image_data)).convert("RGB")
                except Exception as e:
                    raise ValueError(f"Failed to process image data: {e}")

                # Resize with high quality resampling
                image = image.resize((width, height), Image.LANCZOS)

                # Convert to numpy array and normalize
                image = np.array(image, dtype=np.float32) / 255.0

                # ImageNet normalization
                mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
                std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
                image = (image - mean) / std

                # Convert to CHW format and add batch dimension
                image = np.transpose(image, (2, 0, 1))  # CHW
                image = np.expand_dims(image, axis=0).astype(np.float32)  # NCHW

                # Success - log if we had to retry
                if attempt > 0:
                    print(f"[SUCCESS] Image loaded after {attempt + 1} attempts")
                
                return image
            
            except asyncio.TimeoutError:
                if attempt < max_retries - 1:
                    delay = 1.5 * (2 ** attempt)  # Exponential backoff
                    print(f"[TIMEOUT] Retry {attempt + 1}/{max_retries} after {delay}s")
                    await asyncio.sleep(delay)
                    continue
                raise ValueError(f"Timeout fetching image after {max_retries} attempts")
            
            except aiohttp.ClientError as e:
                if attempt < max_retries - 1:
                    delay = 1.5 * (2 ** attempt)
                    print(f"[CLIENT-ERROR] {str(e)[:50]}, retry {attempt + 1}/{max_retries} after {delay}s")
                    await asyncio.sleep(delay)
                    continue
                raise ValueError(f"Network error after {max_retries} attempts: {e}")
            
            except ValueError:
                # Re-raise ValueError as-is (already formatted)
                raise
            
            except Exception as e:
                if attempt < max_retries - 1:
                    delay = 1.0 * (2 ** attempt)
                    print(f"[ERROR] {str(e)[:50]}, retry {attempt + 1}/{max_retries} after {delay}s")
                    await asyncio.sleep(delay)
                    continue
                raise ValueError(f"Failed to load image: {e}")
        
        # Should never reach here
        raise ValueError(f"Failed to load image after {max_retries} attempts")

    def softmax(self, x):
        """Vectorized softmax computation"""
        exp_x = np.exp(x - np.max(x))
        return exp_x / np.sum(exp_x)

    async def predict_with_model(self, image: np.ndarray, session: ort.InferenceSession,
                                class_names: list) -> Tuple[str, float]:
        """Run prediction with a specific model"""
        inputs = {session.get_inputs()[0].name: image}
        outputs = session.run(None, inputs)
        logits = outputs[0][0]

        pred_idx = int(np.argmax(logits))
        probabilities = self.softmax(logits)
        prob = float(probabilities[pred_idx])

        name = class_names[pred_idx] if pred_idx < len(class_names) else f"unknown_{pred_idx}"
        
        return name, prob

    async def predict(self, url: str, session: aiohttp.ClientSession = None) -> Tuple[str, str]:
        """
        Async prediction with dual model fallback system
        
        Logic:
        1. Always use primary model first
        2. If primary confidence < 80%, use secondary model
        3. If secondary confidence < 90%, fallback to primary result
        4. Otherwise use secondary result
        """
        # Check cache first
        cache_key = self._generate_cache_key(url)
        cached_result = self.cache.get(cache_key)
        if cached_result:
            # Return name and confidence (ignore model_used for external API)
            return cached_result[0], cached_result[1]

        # Get HTTP session
        if session is None:
            import __main__
            session = getattr(__main__, 'http_session', None)
            if session is None:
                raise ValueError("HTTP session not available")

        # Initialize models if needed
        if not self.models_initialized:
            await self.initialize_models(session)

        # Preprocess image for primary model (224x224)
        primary_image = await self.preprocess_image(url, session, width=224, height=224)
        
        # Run primary model prediction
        primary_name, primary_prob = await self.predict_with_model(
            primary_image, 
            self.primary_session, 
            self.primary_class_names
        )
        
        primary_confidence_pct = primary_prob * 100
        
        # If primary confidence >= 80%, use it
        if primary_confidence_pct >= 85.0:
            confidence = f"{primary_confidence_pct:.2f}%"
            result = (primary_name, confidence, "primary")
            self.cache.set(cache_key, result)
            return primary_name, confidence
        
        # Primary confidence < 85%, try secondary model
        # Preprocess image for secondary model (336x224 - WIDTH x HEIGHT)
        secondary_width = self.secondary_metadata["image_width"]  # 336
        secondary_height = self.secondary_metadata["image_height"]  # 224
        secondary_image = await self.preprocess_image(
            url, 
            session, 
            width=secondary_width,  # 336
            height=secondary_height  # 224
        )
        
        # Run secondary model prediction
        secondary_name, secondary_prob = await self.predict_with_model(
            secondary_image,
            self.secondary_session,
            self.secondary_class_names
        )
        
        secondary_confidence_pct = secondary_prob * 100
        
        # If secondary confidence >= 90%, use it
        if secondary_confidence_pct >= 90.0:
            confidence = f"{secondary_confidence_pct:.2f}%"
            result = (secondary_name, confidence, "secondary")
            self.cache.set(cache_key, result)
            return secondary_name, confidence
        
        # Secondary confidence < 90%, fallback to primary
        confidence = f"{primary_confidence_pct:.2f}%"
        result = (primary_name, confidence, "primary_fallback")
        self.cache.set(cache_key, result)
        return primary_name, confidence


def main():
    """Test function for development"""
    
    async def test_predict():
        predictor = Prediction()

        async with aiohttp.ClientSession() as session:
            # Initialize models first
            await predictor.initialize_models(session)
            
            while True:
                url = input("Enter Pokémon image URL (or 'q' to quit): ").strip()
                if url.lower() == 'q':
                    break

                try:
                    name, confidence = await predictor.predict(url, session)
                    print(f"Predicted Pokémon: {name} (confidence: {confidence})")
                except Exception as e:
                    print(f"Error: {e}")

    asyncio.run(test_predict())


if __name__ == "__main__":
    main()
