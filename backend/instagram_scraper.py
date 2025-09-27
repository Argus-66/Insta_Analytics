from playwright.async_api import async_playwright
import asyncio
import logging
import random
from datetime import datetime
from typing import Dict, Any, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class InstagramScraperError(Exception):
    """Custom exception for Instagram scraper errors"""
    pass

async def parse_count(element) -> Optional[int]:
    """Parse Instagram number format (e.g., 1.2K, 1M) to integer"""
    try:
        text = await element.text_content()
        if not text:
            return None
            
        # Remove commas and convert to lowercase
        text = text.lower().replace(',', '').strip()
        
        # Extract number and multiplier using regex
        import re
        match = re.match(r'([\d,.]+)([kmb])?', text)
        if not match:
            return None
            
        number_str, suffix = match.groups()
        number = float(number_str.replace(',', ''))
        
        # Convert based on suffix
        multipliers = {'k': 1000, 'm': 1000000, 'b': 1000000000}
        if suffix:
            number *= multipliers.get(suffix, 1)
            
        return int(number)
    except Exception as e:
        logger.error(f"Error parsing count from {text}: {str(e)}")
        return 0  # Return 0 instead of None for failed parses

async def scrape_instagram_profile(username: str, retries: int = 3) -> Dict[str, Any]:
    """
    Scrape Instagram profile data with retries and anti-detection measures
    """
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/121.0'
    ]

    for attempt in range(retries):
        try:
            async with async_playwright() as p:
                # Launch browser with enhanced anti-detection
                browser = await p.chromium.launch(
                    headless=True,
                    args=[
                        '--no-sandbox',
                        '--disable-blink-features=AutomationControlled',
                        '--disable-dev-shm-usage',
                        '--disable-gpu',
                        '--no-first-run',
                        '--disable-default-apps',
                        '--disable-extensions',
                        '--disable-plugins',
                        '--disable-images',
                        '--disable-javascript',
                        '--user-agent=' + random.choice(user_agents)
                    ]
                )
                
                # Create context with realistic settings
                context = await browser.new_context(
                    user_agent=random.choice(user_agents),
                    viewport={'width': 1366, 'height': 768},
                    locale='en-US',
                    timezone_id='America/New_York',
                    extra_http_headers={
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                        'Accept-Language': 'en-US,en;q=0.5',
                        'Accept-Encoding': 'gzip, deflate',
                        'DNT': '1',
                        'Connection': 'keep-alive',
                        'Upgrade-Insecure-Requests': '1',
                    }
                )
                
                page = await context.new_page()
                
                # Add stealth measures
                await page.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined,
                    });
                    Object.defineProperty(navigator, 'plugins', {
                        get: () => [1, 2, 3, 4, 5],
                    });
                    Object.defineProperty(navigator, 'languages', {
                        get: () => ['en-US', 'en'],
                    });
                    window.chrome = {
                        runtime: {},
                    };
                """)
                
                # Add random delay
                await page.wait_for_timeout(random.randint(3000, 6000))
                
                # Navigate to profile with retries
                max_nav_retries = 3
                for nav_attempt in range(max_nav_retries):
                    try:
                        logger.info(f"Navigation attempt {nav_attempt + 1} for {username}")
                        await page.goto(f'https://www.instagram.com/{username}/', timeout=45000)
                        await page.wait_for_load_state('networkidle', timeout=30000)
                        
                        # Check if we're redirected to login
                        current_url = page.url
                        if 'login' in current_url.lower() or 'challenge' in current_url.lower():
                            logger.warning(f"Redirected to login page, attempt {nav_attempt + 1}")
                            if nav_attempt < max_nav_retries - 1:
                                await page.wait_for_timeout(random.randint(5000, 10000))
                                continue
                            else:
                                raise InstagramScraperError(f"Instagram is blocking access - redirected to login")
                        
                        # Check if profile exists
                        error_message = await page.query_selector('text="Sorry, this page isn\'t available."')
                        if error_message:
                            raise InstagramScraperError(f"Profile {username} does not exist")
                        
                        break  # Success, exit retry loop
                        
                    except Exception as e:
                        if nav_attempt < max_nav_retries - 1:
                            logger.warning(f"Navigation failed, retrying: {str(e)}")
                            await page.wait_for_timeout(random.randint(5000, 10000))
                        else:
                            raise e
                
                # Wait for page to load and try multiple selector strategies
                await page.wait_for_timeout(random.randint(2000, 4000))
                
                # Try to find metrics using multiple strategies
                metrics = []
                metrics_found = False
                
                # Strategy 1: Try modern Instagram selectors
                try:
                    # Look for the new Instagram structure
                    metrics = await page.query_selector_all('main section ul li')
                    if metrics and len(metrics) >= 3:
                        metrics_found = True
                        logger.info("Found metrics using main section ul li")
                except:
                    pass
                
                # Strategy 2: Try header-based selectors
                if not metrics_found:
                    try:
                        metrics = await page.query_selector_all('header section ul li')
                        if metrics and len(metrics) >= 3:
                            metrics_found = True
                            logger.info("Found metrics using header section ul li")
                    except:
                        pass
                
                # Strategy 3: Try alternative header selectors
                if not metrics_found:
                    try:
                        metrics = await page.query_selector_all('header ul li')
                        if metrics and len(metrics) >= 3:
                            metrics_found = True
                            logger.info("Found metrics using header ul li")
                    except:
                        pass
                
                # Strategy 4: Try to find any elements with numbers
                if not metrics_found:
                    try:
                        # Look for any elements that might contain follower/following counts
                        all_links = await page.query_selector_all('a')
                        metrics = []
                        for link in all_links:
                            href = await link.get_attribute('href')
                            if href and ('/followers/' in href or '/following/' in href):
                                metrics.append(link)
                        if len(metrics) >= 2:
                            metrics_found = True
                            logger.info("Found metrics using href-based detection")
                    except:
                        pass
                
                # Strategy 5: JavaScript-based extraction
                if not metrics_found:
                    try:
                        logger.info("Attempting JavaScript-based metric extraction...")
                        js_metrics = await page.evaluate("""
                            () => {
                                const metrics = [];
                                // Look for elements with numbers that might be counts
                                const allElements = document.querySelectorAll('*');
                                for (const el of allElements) {
                                    const text = el.textContent;
                                    if (text && /^[\d,\.KMB]+$/.test(text.trim()) && text.length < 10) {
                                        metrics.push(el);
                                    }
                                }
                                return metrics.slice(0, 10); // Return first 10 potential metrics
                            }
                        """)
                        if js_metrics and len(js_metrics) >= 3:
                            # Convert JS elements back to Playwright elements
                            metrics = []
                            for i, js_metric in enumerate(js_metrics):
                                try:
                                    element = await page.query_selector(f'*:has-text("{js_metric.textContent}")')
                                    if element:
                                        metrics.append(element)
                                except:
                                    pass
                            if len(metrics) >= 3:
                                metrics_found = True
                                logger.info("Found metrics using JavaScript extraction")
                    except Exception as e:
                        logger.debug(f"JavaScript extraction failed: {str(e)}")
                
                if not metrics_found:
                    logger.warning(f"Could not find metrics for {username} using any strategy")
                    # Log page content for debugging
                    try:
                        page_content = await page.content()
                        logger.debug(f"Page content (first 1000 chars): {page_content[:1000]}")
                    except:
                        pass
                
                # Log raw metrics text for debugging
                for i, metric in enumerate(metrics):
                    text = await metric.text_content()
                    logger.debug(f"Raw metric {i}: {text}")
                
                # Parse counts with fallbacks
                posts_count = await parse_count(metrics[0]) if len(metrics) > 0 else 0
                followers_count = await parse_count(metrics[1]) if len(metrics) > 1 else 0
                following_count = await parse_count(metrics[2]) if len(metrics) > 2 else 0
                
                logger.debug(f"Parsed metrics - Posts: {posts_count}, Followers: {followers_count}, Following: {following_count}")
                
                # Get profile name with multiple selectors
                name = username
                try:
                    name_selectors = [
                        "header section h2",
                        "header h2",
                        "header span[class*='title']",
                        "header [class*='profile'] h2"
                    ]
                    for selector in name_selectors:
                        name_el = await page.query_selector(selector)
                        if name_el:
                            name = await name_el.text_content()
                            break
                    logger.debug(f"Found profile name: {name}")
                except Exception as e:
                    logger.error(f"Error getting profile name: {str(e)}")
                
                # Get profile picture with multiple selectors
                profile_pic = None
                try:
                    img_selectors = [
                        "header img[class*='profile']",
                        "header img",
                        "[class*='ProfilePic'] img"
                    ]
                    for selector in img_selectors:
                        img_el = await page.query_selector(selector)
                        if img_el:
                            profile_pic = await img_el.get_attribute("src")
                            if profile_pic:
                                break
                    logger.debug(f"Found profile picture: {profile_pic is not None}")
                except Exception as e:
                    logger.error(f"Error getting profile picture: {str(e)}")
                
                # Get recent posts
                posts = []
                try:
                    # Initial wait for content
                    await page.wait_for_load_state('networkidle')
                    
                    # Try to find and click "Load more posts" button if it exists
                    try:
                        load_more = await page.query_selector('text="Load more posts"')
                        if load_more:
                            await load_more.click()
                            await page.wait_for_timeout(2000)
                    except:
                        pass

                    # Scroll multiple times to ensure posts are loaded
                    previous_height = 0
                    scroll_attempts = 0
                    max_attempts = 5

                    while scroll_attempts < max_attempts:
                        # Scroll and wait
                        current_height = await page.evaluate('document.body.scrollHeight')
                        if current_height == previous_height:
                            break
                            
                        await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                        await page.wait_for_timeout(2000)  # Wait longer for content to load
                        
                        previous_height = current_height
                        scroll_attempts += 1

                    # Try to find posts using JavaScript evaluation with improved selectors
                    posts_data = await page.evaluate("""() => {
                        const posts = [];
                        
                        // Try different selectors for the posts grid
                        const gridSelectors = [
                            'article div[style*="grid"]',
                            'article div[class*="grid"]',
                            'main article',
                            'div[class*="Post"]'
                        ];
                        
                        let container = null;
                        for (const selector of gridSelectors) {
                            container = document.querySelector(selector);
                            if (container) break;
                        }
                        
                        if (!container) return posts;
                        
                        // Find all post elements
                        const postElements = container.querySelectorAll('a');
                        
                        for (const post of postElements) {
                            const img = post.querySelector('img');
                            if (!img) continue;
                            
                            const src = img.src;
                            if (!src || !src.includes('instagram')) continue;
                            
                            let caption = img.alt || '';
                            
                            // Try to find caption in surrounding elements
                            const captionEl = post.querySelector('span[class*="caption"], span[class*="Caption"], span[class*="alt"]');
                            if (captionEl) {
                                caption = captionEl.textContent || caption;
                            }
                            
                            posts.push({
                                image_url: src,
                                caption: caption,
                            });
                            
                            if (posts.length >= 12) break;  // Stop after finding 12 posts
                        }
                        
                        return posts;
                    }""")
                    
                    logger.debug(f"Found {len(posts_data)} posts using JavaScript evaluation")
                    
                    # If JavaScript evaluation didn't find enough posts, try alternative methods
                    if len(posts_data) < 10:
                        logger.debug("Not enough posts found, trying alternative methods")
                        
                        # Method 1: Try direct img selectors
                        post_selectors = [
                            'article a img[src*="instagram"]',
                            'article div[role="button"] img',
                            'main article img[src*="instagram"]',
                            'div[class*="Post"] img'
                        ]
                        
                        for selector in post_selectors:
                            if len(posts_data) >= 10:
                                break
                                
                            try:
                                images = await page.query_selector_all(selector)
                                logger.debug(f"Found {len(images)} images with selector: {selector}")
                                
                                for img in images:
                                    src = await img.get_attribute("src")
                                    if not src or not src.includes("instagram"):
                                        continue
                                        
                                    alt = await img.get_attribute("alt")
                                    posts_data.append({
                                        "image_url": src,
                                        "caption": alt or "",
                                    })
                                    
                                    if len(posts_data) >= 10:
                                        break
                            except Exception as e:
                                logger.debug(f"Error with selector {selector}: {str(e)}")
                                continue
                        
                        # Method 2: Try finding post links
                        if len(posts_data) < 10:
                            try:
                                post_links = await page.query_selector_all('a[href*="/p/"]')
                                for link in post_links:
                                    img = await link.query_selector('img[src*="instagram"]')
                                    if img:
                                        src = await img.get_attribute("src")
                                        alt = await img.get_attribute("alt")
                                        if src:
                                            posts_data.append({
                                                "image_url": src,
                                                "caption": alt or "",
                                            })
                                            
                                            if len(posts_data) >= 10:
                                                break
                            except Exception as e:
                                logger.debug(f"Error finding post links: {str(e)}")
                                
                        logger.debug(f"After alternative methods, found {len(posts_data)} posts")
                    
                    # Remove any duplicate posts based on image_url
                    seen_urls = set()
                    unique_posts = []
                    for post in posts_data:
                        if post["image_url"] not in seen_urls:
                            seen_urls.add(post["image_url"])
                            unique_posts.append(post)
                    
                    # Add timestamp and ensure we have at least some posts
                    posts = [{**post, "timestamp": datetime.utcnow().isoformat()} for post in unique_posts[:12]]
                    
                    if not posts:
                        logger.warning(f"No posts found for {username}")
                    else:
                        logger.info(f"Successfully retrieved {len(posts)} posts for {username}")
                        logger.debug("First post image URL: " + posts[0]["image_url"])
                        
                except Exception as e:
                    logger.error(f"Error fetching posts for {username}: {str(e)}")
                    # Log the full page HTML for debugging
                    page_content = await page.content()
                    logger.debug(f"Page HTML (first 1000 chars): {page_content[:1000]}")
                finally:
                    try:
                        await browser.close()
                    except:
                        pass
                
                # If we still don't have good data, try the legacy JSON approach
                if (followers_count == 0 and following_count == 0 and posts_count == 0) or not posts:
                    logger.info("Trying legacy JSON extraction method...")
                    try:
                        # Try to extract data from window._sharedData
                        json_data = await page.evaluate("""
                            () => {
                                try {
                                    const scripts = document.querySelectorAll('script');
                                    for (const script of scripts) {
                                        const content = script.textContent;
                                        if (content && content.includes('window._sharedData')) {
                                            const match = content.match(/window\\._sharedData\\s*=\\s*({.+?});/);
                                            if (match) {
                                                return JSON.parse(match[1]);
                                            }
                                        }
                                    }
                                    return null;
                                } catch (e) {
                                    return null;
                                }
                            }
                        """)
                        
                        if json_data and json_data.get('entry_data', {}).get('ProfilePage'):
                            logger.info("Found JSON data, extracting profile info...")
                            user_data = json_data['entry_data']['ProfilePage'][0]['graphql']['user']
                            
                            # Extract from JSON
                            followers_count = user_data.get('edge_followed_by', {}).get('count', 0)
                            following_count = user_data.get('edge_follow', {}).get('count', 0)
                            posts_count = user_data.get('edge_owner_to_timeline_media', {}).get('count', 0)
                            name = user_data.get('full_name', username)
                            profile_pic = user_data.get('profile_pic_url_hd') or user_data.get('profile_pic_url')
                            
                            # Extract recent posts from JSON
                            posts = []
                            edges = user_data.get('edge_owner_to_timeline_media', {}).get('edges', [])
                            for edge in edges[:12]:
                                node = edge.get('node', {})
                                posts.append({
                                    "image_url": node.get('display_url', ''),
                                    "caption": node.get('edge_media_to_caption', {}).get('edges', [{}])[0].get('node', {}).get('text', ''),
                                    "timestamp": datetime.utcnow().isoformat()
                                })
                            
                            logger.info(f"Successfully extracted data from JSON: {followers_count} followers, {posts_count} posts")
                    except Exception as e:
                        logger.debug(f"JSON extraction also failed: {str(e)}")
                
                # Return data with ISO formatted date
                return {
                    "username": username,
                    "full_name": name,
                    "profile_pic_url": profile_pic,
                    "followers_count": followers_count or 0,
                    "following_count": following_count or 0,
                    "posts_count": posts_count or 0,
                    "recent_posts": posts,
                    "last_updated": datetime.utcnow().isoformat()  # Convert to ISO string
                }
                
        except Exception as e:
            logger.error(f"Attempt {attempt + 1}/{retries} failed for {username}: {str(e)}")
            if attempt == retries - 1:
                raise InstagramScraperError(f"Failed to scrape profile after {retries} attempts: {str(e)}")
            await asyncio.sleep(random.randint(3, 7))  # Random delay between retries

# Example usage for testing
if __name__ == "__main__":
    import json
    username = input("Enter Instagram username: ")
    profile = asyncio.run(scrape_instagram_profile(username))
    print(json.dumps(profile, indent=4))
