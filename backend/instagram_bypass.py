"""
Instagram scraping bypass solutions
"""
import asyncio
import aiohttp
import json
import re
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class InstagramBypass:
    """Multiple strategies to bypass Instagram's anti-bot measures"""
    
    def __init__(self):
        self.session = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def scrape_profile(self, username: str) -> Dict[str, Any]:
        """Try multiple bypass strategies"""
        
        # Strategy 1: Use Instagram's embed endpoint
        try:
            result = await self._scrape_embed(username)
            if result and result.get('followers_count', 0) > 0:
                logger.info("Embed scraping succeeded")
                return result
        except Exception as e:
            logger.debug(f"Embed scraping failed: {str(e)}")
        
        # Strategy 2: Use mobile user agent
        try:
            result = await self._scrape_mobile(username)
            if result and result.get('followers_count', 0) > 0:
                logger.info("Mobile scraping succeeded")
                return result
        except Exception as e:
            logger.debug(f"Mobile scraping failed: {str(e)}")
        
        # Strategy 3: Use different headers
        try:
            result = await self._scrape_headers(username)
            if result and result.get('followers_count', 0) > 0:
                logger.info("Headers scraping succeeded")
                return result
        except Exception as e:
            logger.debug(f"Headers scraping failed: {str(e)}")
        
        # Return empty result if all fail
        return {
            "username": username,
            "full_name": username,
            "profile_pic_url": None,
            "followers_count": 0,
            "following_count": 0,
            "posts_count": 0,
            "recent_posts": [],
            "last_updated": None
        }
    
    async def _scrape_embed(self, username: str) -> Optional[Dict[str, Any]]:
        """Scrape using Instagram's embed endpoint"""
        try:
            embed_url = f"https://www.instagram.com/{username}/embed/"
            headers = {
                'User-Agent': 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
            }
            
            async with self.session.get(embed_url, headers=headers, timeout=30) as response:
                if response.status == 200:
                    content = await response.text()
                    
                    # Look for follower count
                    follower_match = re.search(r'(\d+(?:,\d+)*(?:\.\d+)?[KMB]?)\s*followers', content, re.IGNORECASE)
                    following_match = re.search(r'(\d+(?:,\d+)*(?:\.\d+)?[KMB]?)\s*following', content, re.IGNORECASE)
                    posts_match = re.search(r'(\d+(?:,\d+)*(?:\.\d+)?[KMB]?)\s*posts', content, re.IGNORECASE)
                    
                    if follower_match:
                        return {
                            "username": username,
                            "full_name": username,
                            "profile_pic_url": None,
                            "followers_count": self._parse_number(follower_match.group(1)),
                            "following_count": self._parse_number(following_match.group(1)) if following_match else 0,
                            "posts_count": self._parse_number(posts_match.group(1)) if posts_match else 0,
                            "recent_posts": [],
                            "last_updated": None
                        }
        except Exception as e:
            logger.debug(f"Embed scraping error: {str(e)}")
        
        return None
    
    async def _scrape_mobile(self, username: str) -> Optional[Dict[str, Any]]:
        """Scrape using mobile user agent"""
        try:
            url = f"https://www.instagram.com/{username}/"
            headers = {
                'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
            }
            
            async with self.session.get(url, headers=headers, timeout=30) as response:
                if response.status == 200:
                    content = await response.text()
                    
                    # Try to extract JSON data
                    json_match = re.search(r'window\._sharedData\s*=\s*({.+?});', content)
                    if json_match:
                        data = json.loads(json_match.group(1))
                        if 'entry_data' in data and 'ProfilePage' in data['entry_data']:
                            user_data = data['entry_data']['ProfilePage'][0]['graphql']['user']
                            
                            return {
                                "username": user_data.get('username', username),
                                "full_name": user_data.get('full_name', username),
                                "profile_pic_url": user_data.get('profile_pic_url_hd') or user_data.get('profile_pic_url'),
                                "followers_count": user_data.get('edge_followed_by', {}).get('count', 0),
                                "following_count": user_data.get('edge_follow', {}).get('count', 0),
                                "posts_count": user_data.get('edge_owner_to_timeline_media', {}).get('count', 0),
                                "recent_posts": [],
                                "last_updated": None
                            }
        except Exception as e:
            logger.debug(f"Mobile scraping error: {str(e)}")
        
        return None
    
    async def _scrape_headers(self, username: str) -> Optional[Dict[str, Any]]:
        """Scrape using different headers"""
        try:
            url = f"https://www.instagram.com/{username}/"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Cache-Control': 'max-age=0',
            }
            
            async with self.session.get(url, headers=headers, timeout=30) as response:
                if response.status == 200:
                    content = await response.text()
                    
                    # Look for any numbers that might be counts
                    numbers = re.findall(r'(\d+(?:,\d+)*(?:\.\d+)?[KMB]?)', content)
                    if numbers:
                        # Try to find meaningful patterns
                        return {
                            "username": username,
                            "full_name": username,
                            "profile_pic_url": None,
                            "followers_count": 0,
                            "following_count": 0,
                            "posts_count": 0,
                            "recent_posts": [],
                            "last_updated": None
                        }
        except Exception as e:
            logger.debug(f"Headers scraping error: {str(e)}")
        
        return None
    
    def _parse_number(self, num_str: str) -> int:
        """Parse Instagram number format (1.2K, 1M, etc.)"""
        try:
            num_str = num_str.replace(',', '').upper()
            if 'K' in num_str:
                return int(float(num_str.replace('K', '')) * 1000)
            elif 'M' in num_str:
                return int(float(num_str.replace('M', '')) * 1000000)
            elif 'B' in num_str:
                return int(float(num_str.replace('B', '')) * 1000000000)
            else:
                return int(float(num_str))
        except:
            return 0

async def scrape_instagram_profile_bypass(username: str) -> Dict[str, Any]:
    """Bypass function for Instagram scraping"""
    async with InstagramBypass() as bypass:
        return await bypass.scrape_profile(username)

# Test function
if __name__ == "__main__":
    async def test():
        result = await scrape_instagram_profile_bypass("kbv_kishore")
        print(json.dumps(result, indent=2))
    
    asyncio.run(test())
