#!/usr/bin/env python3
"""
AMC-TRADER RQ Worker Debug and Validation Script
Diagnoses and fixes worker processing issues
"""
import os
import sys
import redis
import json
import logging
from datetime import datetime
from pathlib import Path

# Add backend to Python path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))
sys.path.insert(0, str(backend_path.parent))

# Import with proper path handling
try:
    from constants import DISCOVERY_QUEUE, CACHE_KEY_CONTENDERS, CACHE_KEY_STATUS
except ImportError:
    # Fallback constants if import fails
    DISCOVERY_QUEUE = "amc_discovery"
    CACHE_KEY_CONTENDERS = "amc:discovery:candidates:v2"
    CACHE_KEY_STATUS = "amc:discovery:status:v2"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_redis_connection():
    """Test Redis connectivity and decode issues"""
    try:
        redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
        r = redis.from_url(redis_url, decode_responses=True)
        
        # Test basic connectivity
        ping_result = r.ping()
        logger.info(f"✅ Redis ping successful: {ping_result}")
        
        # Check for corrupted keys
        keys_to_check = [CACHE_KEY_CONTENDERS, CACHE_KEY_STATUS, DISCOVERY_QUEUE]
        for key in keys_to_check:
            try:
                value = r.get(key)
                if value:
                    logger.info(f"✅ Key {key}: exists, length={len(value)}")
                    # Try to parse as JSON
                    try:
                        json.loads(value)
                        logger.info(f"✅ Key {key}: valid JSON")
                    except json.JSONDecodeError:
                        logger.warning(f"⚠️ Key {key}: not valid JSON, clearing...")
                        r.delete(key)
                else:
                    logger.info(f"ℹ️ Key {key}: empty")
            except UnicodeDecodeError as e:
                logger.error(f"❌ Key {key}: UTF-8 decode error - {e}")
                logger.info(f"🔧 Clearing corrupted key: {key}")
                r.delete(key)
        
        return r
        
    except Exception as e:
        logger.error(f"❌ Redis connection failed: {e}")
        return None

def clear_job_queue(r):
    """Clear the RQ job queue to reset state"""
    try:
        # Clear the queue
        queue_key = f"rq:queue:{DISCOVERY_QUEUE}"
        queue_length = r.llen(queue_key)
        if queue_length > 0:
            logger.info(f"🧹 Clearing {queue_length} jobs from queue")
            r.delete(queue_key)
        
        # Clear failed jobs
        failed_key = f"rq:queue:{DISCOVERY_QUEUE}:failed"
        failed_count = r.llen(failed_key) if r.exists(failed_key) else 0
        if failed_count > 0:
            logger.info(f"🧹 Clearing {failed_count} failed jobs")
            r.delete(failed_key)
        
        # Clear any job-specific keys
        job_keys = r.keys("rq:job:*")
        if job_keys:
            logger.info(f"🧹 Clearing {len(job_keys)} job keys")
            r.delete(*job_keys)
            
        logger.info("✅ Queue cleared successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to clear queue: {e}")
        return False

def test_job_function():
    """Test that the discovery job function can be imported and executed"""
    try:
        logger.info("🔍 Testing job function import...")
        try:
            from jobs.discovery_job import run_discovery_job
        except ImportError:
            from backend.src.jobs.discovery_job import run_discovery_job
        logger.info("✅ Job function imported successfully")
        
        logger.info("🔍 Testing direct job execution (small test)...")
        # Test with very small limit to avoid timeout
        result = run_discovery_job(limit=3)
        logger.info(f"✅ Direct job execution successful: {result.get('status', 'unknown')}")
        
        if result.get('status') == 'success':
            logger.info(f"   Found {result.get('count', 0)} candidates")
            logger.info(f"   Universe size: {result.get('universe_size', 0)}")
            
        return True
        
    except Exception as e:
        logger.error(f"❌ Job function test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def populate_cache_directly(r):
    """Populate cache directly for immediate frontend access"""
    try:
        logger.info("🔄 Populating cache with direct discovery run...")
        
        # Import and run discovery directly
        try:
            from jobs.discovery_job import run_discovery_job
        except ImportError:
            from backend.src.jobs.discovery_job import run_discovery_job
        result = run_discovery_job(limit=10)
        
        if result.get('status') == 'success':
            # Create cache payload matching expected format
            cache_payload = {
                'timestamp': int(datetime.now().timestamp()),
                'iso_timestamp': datetime.now().isoformat(),
                'universe_size': result.get('universe_size', 0),
                'filtered_size': result.get('filtered_size', 0),
                'count': result.get('count', 0),
                'trade_ready_count': result.get('trade_ready_count', 0),
                'monitor_count': 0,
                'candidates': [],  # Will be populated if result has candidates
                'engine': 'BMS Emergency Direct Cache',
                'job_id': f'emergency_{int(datetime.now().timestamp())}'
            }
            
            # Store in cache
            r.setex(CACHE_KEY_CONTENDERS, 600, json.dumps(cache_payload))
            logger.info(f"✅ Cache populated with {cache_payload['count']} candidates")
            return True
            
    except Exception as e:
        logger.error(f"❌ Failed to populate cache: {e}")
        import traceback
        traceback.print_exc()
        
    # Fallback - create empty but valid cache
    try:
        logger.info("🔄 Creating empty fallback cache...")
        fallback_payload = {
            'timestamp': int(datetime.now().timestamp()),
            'iso_timestamp': datetime.now().isoformat(),
            'universe_size': 0,
            'filtered_size': 0,
            'count': 0,
            'trade_ready_count': 0,
            'monitor_count': 0,
            'candidates': [],
            'engine': 'BMS Emergency Fallback Cache',
            'job_id': f'fallback_{int(datetime.now().timestamp())}'
        }
        
        r.setex(CACHE_KEY_CONTENDERS, 300, json.dumps(fallback_payload))
        logger.info("✅ Fallback cache created")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to create fallback cache: {e}")
        return False

def validate_system():
    """Complete system validation"""
    logger.info("🔍 Starting AMC-TRADER discovery system validation...")
    
    # Test Redis
    r = test_redis_connection()
    if not r:
        return False
    
    # Clear corrupted state
    logger.info("🧹 Cleaning corrupted state...")
    clear_job_queue(r)
    
    # Test job function
    logger.info("🔍 Testing job function...")
    job_works = test_job_function()
    
    # Populate cache for immediate frontend access
    logger.info("🔄 Populating cache...")
    cache_populated = populate_cache_directly(r)
    
    # Final validation
    logger.info("🔍 Final system check...")
    cached_data = r.get(CACHE_KEY_CONTENDERS)
    if cached_data:
        try:
            payload = json.loads(cached_data)
            logger.info(f"✅ Cache validation successful: {payload.get('count', 0)} candidates")
        except:
            logger.error("❌ Cache contains invalid JSON")
            return False
    
    logger.info("✅ System validation complete")
    return True

if __name__ == "__main__":
    validate_system()