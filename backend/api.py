from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from backend.instagram_scraper import scrape_instagram_profile, InstagramScraperError
import motor.motor_asyncio
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
import logging

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
CACHE_DURATION = int(os.getenv("CACHE_DURATION", "24"))  # Cache duration in hours

# Initialize FastAPI app
app = FastAPI(title="Instagram Analytics API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize MongoDB
client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URL)
db = client["insta_analytics"]
profiles = db["profiles"]


from datetime import datetime

def serialize_profile(profile: dict) -> dict:
    """Convert Mongo ObjectId and ensure consistent data types"""
    serialized = {}
    
    # Convert ObjectId to string
    if "_id" in profile:
        serialized["_id"] = str(profile["_id"])
    
    # Copy basic fields
    serialized["username"] = profile["username"]
    serialized["full_name"] = profile.get("full_name", profile["username"])
    serialized["profile_pic_url"] = profile.get("profile_pic_url", "")
    
    # Ensure consistent integer types for counts
    serialized["followers_count"] = int(profile.get("followers_count", 0))
    serialized["following_count"] = int(profile.get("following_count", 0))
    serialized["posts_count"] = int(profile.get("posts_count", 0))
    
    # Handle recent posts
    serialized["recent_posts"] = profile.get("recent_posts", [])
    
    # Handle last_updated
    last_updated = profile.get("last_updated")
    if isinstance(last_updated, str):
        serialized["last_updated"] = last_updated
    elif isinstance(last_updated, datetime):
        serialized["last_updated"] = last_updated.isoformat()
    else:
        serialized["last_updated"] = datetime.utcnow().isoformat()
    
    return serialized

@app.get("/api/profile/{username}")
async def get_profile(username: str, force_refresh: bool = False):
    try:
        logger.info(f"Fetching profile for username: {username} (force_refresh: {force_refresh})")
        
        # Always check cache first for immediate response
        cached_profile = await profiles.find_one({"username": username.lower()})
        
        if cached_profile and not force_refresh:
            try:
                # Check if cache is recent (within 1 hour)
                if isinstance(cached_profile["last_updated"], str):
                    last_updated = datetime.fromisoformat(cached_profile["last_updated"])
                else:
                    last_updated = cached_profile["last_updated"]
                
                cache_age = datetime.utcnow() - last_updated
                
                # If cache is fresh (less than 1 hour), return immediately
                if cache_age < timedelta(hours=1):
                    logger.info("Returning fresh cached profile")
                    return serialize_profile(cached_profile)
                
                # If cache is old but has data, return it immediately and refresh in background
                elif cached_profile.get("recent_posts") and len(cached_profile["recent_posts"]) > 0:
                    logger.info("Returning cached profile, refreshing in background")
                    
                    # Start background refresh (don't await)
                    import asyncio
                    asyncio.create_task(refresh_profile_background(username))
                    
                    return serialize_profile(cached_profile)
                    
            except Exception as e:
                logger.error(f"Error processing cached profile: {str(e)}")
        
        # No cache or force refresh - scrape fresh data
        logger.info("Scraping fresh profile data")
        
        # Try multiple scraping approaches
        data = None
        scraping_errors = []
        
        # Approach 1: Try the main scraper
        try:
            data = await scrape_instagram_profile(username)
            if data and (data.get('followers_count', 0) > 0 or data.get('posts_count', 0) > 0):
                logger.info("Main scraper succeeded")
            else:
                data = None
        except Exception as e:
            scraping_errors.append(f"Main scraper: {str(e)}")
            logger.warning(f"Main scraper failed: {str(e)}")
        
        # Approach 2: Try bypass scraper if main failed
        if not data or (data.get('followers_count', 0) == 0 and data.get('posts_count', 0) == 0):
            try:
                from .instagram_bypass import scrape_instagram_profile_bypass
                data = await scrape_instagram_profile_bypass(username)
                if data and (data.get('followers_count', 0) > 0 or data.get('posts_count', 0) > 0):
                    logger.info("Bypass scraper succeeded")
                else:
                    data = None
            except ImportError:
                scraping_errors.append("Bypass scraper: Module not found")
                logger.warning("Bypass scraper module not found")
            except Exception as e:
                scraping_errors.append(f"Bypass scraper: {str(e)}")
                logger.warning(f"Bypass scraper failed: {str(e)}")
        
        # If all scraping fails, handle gracefully
        if not data or (data.get('followers_count', 0) == 0 and data.get('posts_count', 0) == 0):
            if cached_profile:
                logger.warning("All scraping failed, returning cached data")
                return serialize_profile(cached_profile)
            else:
                # Create a minimal profile entry to avoid repeated scraping attempts
                minimal_data = {
                    "username": username,
                    "full_name": username,
                    "profile_pic_url": None,
                    "followers_count": 0,
                    "following_count": 0,
                    "posts_count": 0,
                    "recent_posts": [],
                    "last_updated": datetime.utcnow().isoformat(),
                    "scraping_blocked": True  # Flag to indicate scraping was blocked
                }
                
                # Store minimal data to prevent repeated scraping
                await profiles.update_one(
                    {"username": username.lower()},
                    {"$set": minimal_data},
                    upsert=True
                )
                
                # Return a user-friendly error message
                error_msg = "Instagram is currently blocking automated access. This profile may be private, or Instagram's anti-bot measures are preventing data collection. Please try again later or contact support if this persists."
                raise InstagramScraperError(error_msg)
            
        logger.debug(f"Scraped data: {data}")
        
        # Update or insert in MongoDB
        await profiles.update_one(
            {"username": username.lower()},
            {"$set": data},
            upsert=True
        )
        
        serialized_data = serialize_profile(data)
        logger.debug(f"Serialized response: {serialized_data}")
        return serialized_data
        
    except InstagramScraperError as e:
        logger.error(f"Scraper error for {username}: {str(e)}")
        # Try to return cached data if available
        if cached_profile:
            logger.warning("Scraper failed, returning cached data")
            return serialize_profile(cached_profile)
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error for {username}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

async def refresh_profile_background(username: str):
    """Background task to refresh profile data"""
    try:
        logger.info(f"Background refresh for {username}")
        data = await scrape_instagram_profile(username)
        
        if data:
            await profiles.update_one(
                {"username": username.lower()},
                {"$set": data},
                upsert=True
            )
            logger.info(f"Background refresh completed for {username}")
        else:
            logger.warning(f"Background refresh failed for {username}")
            
    except Exception as e:
        logger.error(f"Background refresh error for {username}: {str(e)}")

@app.get("/health")
async def health_check():
    try:
        # Check MongoDB connection
        await client.admin.command('ping')
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database connection failed: {str(e)}")

@app.get("/api/profile/{username}/cached")
async def get_cached_profile(username: str):
    """Get only cached profile data (fastest response)"""
    try:
        profile = await profiles.find_one({"username": username.lower()})
        if profile:
            return serialize_profile(profile)
        else:
            raise HTTPException(status_code=404, detail="Profile not found in cache")
    except Exception as e:
        logger.error(f"Error getting cached profile for {username}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/debug/{username}")
async def debug_profile(username: str):
    """Debug endpoint for testing scraper"""
    try:
        profile_data = await scrape_instagram_profile(username)
        return {
            "success": True,
            "data": profile_data,
            "raw_metrics": {
                "posts": profile_data["posts_count"],
                "followers": profile_data["followers_count"],
                "following": profile_data["following_count"]
            }
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@app.post("/api/profile/{username}/manual")
async def add_manual_profile(username: str, profile_data: dict):
    """Manually add profile data for testing"""
    try:
        # Ensure required fields
        data = {
            "username": username,
            "full_name": profile_data.get("full_name", username),
            "profile_pic_url": profile_data.get("profile_pic_url"),
            "followers_count": int(profile_data.get("followers_count", 0)),
            "following_count": int(profile_data.get("following_count", 0)),
            "posts_count": int(profile_data.get("posts_count", 0)),
            "recent_posts": profile_data.get("recent_posts", []),
            "last_updated": datetime.utcnow().isoformat(),
            "manual_entry": True  # Flag to indicate manual entry
        }
        
        # Store in database
        await profiles.update_one(
            {"username": username.lower()},
            {"$set": data},
            upsert=True
        )
        
        return {"success": True, "message": f"Profile data added for {username}"}
    except Exception as e:
        logger.error(f"Error adding manual profile: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/profile/{username}/status")
async def get_profile_status(username: str):
    """Get profile status and scraping information"""
    try:
        profile = await profiles.find_one({"username": username.lower()})
        if profile:
            return {
                "username": profile["username"],
                "exists": True,
                "has_data": profile.get("followers_count", 0) > 0 or profile.get("posts_count", 0) > 0,
                "is_manual": profile.get("manual_entry", False),
                "is_blocked": profile.get("scraping_blocked", False),
                "last_updated": profile.get("last_updated"),
                "followers_count": profile.get("followers_count", 0),
                "posts_count": profile.get("posts_count", 0)
            }
        else:
            return {
                "username": username,
                "exists": False,
                "has_data": False,
                "is_manual": False,
                "is_blocked": False,
                "last_updated": None,
                "followers_count": 0,
                "posts_count": 0
            }
    except Exception as e:
        logger.error(f"Error getting profile status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
