"""
Reddit Provider - Quét video từ Reddit (subreddits)
Hỗ trợ: r/videos, r/Shorts, r/TikTokCringe, v.v...
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime
import re

from .base import BaseProvider
from core.schema import VideoItem

logger = logging.getLogger(__name__)


class RedditProvider(BaseProvider):
    """Provider cho Reddit"""
    
    name = "reddit"
    description = "Quét video từ các subreddit"
    
    def __init__(self, config: Dict):
        super().__init__(config)
        self.config = config.get('reddit', {})
        self.subreddits = self.config.get('subreddits', ['videos', 'Shorts', 'TikTokCringe'])
        self.limit_per_subreddit = self.config.get('limit_per_subreddit', 50)
        self.sort_by = self.config.get('sort_by', 'hot')  # hot, new, top
        self.time_filter = self.config.get('time_filter', 'week')  # hour, day, week, month, year, all
        
        # Reddit API credentials (dùng PRAW library)
        self.client_id = self.config.get('client_id', '')
        self.client_secret = self.config.get('client_secret', '')
        self.user_agent = self.config.get('user_agent', 'VideoPipelineBot/1.0')
        self.username = self.config.get('username', '')
        self.password = self.config.get('password', '')
        
        self.reddit = None
    
    def _init_reddit(self):
        """Khởi tạo Reddit API client"""
        try:
            import praw
            
            if not self.client_id or not self.client_secret:
                logger.warning("Thiếu Reddit API credentials. Sử dụng read-only mode.")
                # Dùng chế độ read-only không cần auth
                self.reddit = praw.Reddit(
                    user_agent=self.user_agent,
                    readonly=True
                )
            else:
                self.reddit = praw.Reddit(
                    client_id=self.client_id,
                    client_secret=self.client_secret,
                    user_agent=self.user_agent,
                    username=self.username,
                    password=self.password
                )
            
            logger.info("Đã kết nối Reddit API")
            return True
        except ImportError:
            logger.error("Chưa cài đặt praw. Chạy: pip install praw")
            return False
        except Exception as e:
            logger.error(f"Lỗi kết nối Reddit: {e}")
            return False
    
    def extract_video_url(self, post) -> Optional[str]:
        """Trích xuất URL video từ Reddit post"""
        # Reddit-hosted video
        if hasattr(post, 'is_video') and post.is_video:
            if hasattr(post, 'media') and post.media:
                reddit_video = post.media.get('reddit_video', {})
                fallback_url = reddit_video.get('fallback_url')
                if fallback_url:
                    return fallback_url
        
        # Direct video links (mp4, webm)
        if hasattr(post, 'url'):
            url = post.url
            if url.endswith(('.mp4', '.webm')):
                return url
            
            # gfycat, imgur, v.redd.it
            if 'v.redd.it' in url:
                return url
            if 'gfycat.com' in url:
                # Chuyển sang direct link
                gfycat_id = url.split('/')[-1].split('-')[0]
                return f"https://thumbs.gfycat.com/{gfycat_id}-mobile.mp4"
            if 'imgur.com' in url and not url.endswith(('.jpg', '.png', '.gif')):
                return url
        
        # Cross-post từ TikTok, YouTube, etc.
        if hasattr(post, 'url_overridden_by_dest'):
            url = post.url_overridden_by_dest
            if any(domain in url for domain in ['tiktok.com', 'youtube.com', 'instagram.com']):
                return url
        
        return None
    
    def search_by_topic(self, topic: str) -> List[VideoItem]:
        """Tìm video theo topic (search trong subreddit)"""
        videos = []
        
        if not self._init_reddit():
            return videos
        
        try:
            # Search trong tất cả subreddits
            search_query = topic
            subreddit_list = self.reddit.subreddit('+'.join(self.subreddits))
            
            posts = subreddit_list.search(
                search_query,
                sort=self.sort_by,
                time_filter=self.time_filter,
                limit=self.limit_per_subreddit
            )
            
            for post in posts:
                video_url = self.extract_video_url(post)
                if video_url:
                    video_info = VideoItem(
                        url=video_url,
                        source='reddit',
                        title=post.title[:100] if post.title else 'Reddit Video',
                        description=getattr(post, 'selftext', '')[:500] if hasattr(post, 'selftext') else '',
                        author=getattr(post, 'author', None),
                        hashtags=[topic.lower().replace(' ', '')],
                        metadata={
                            'post_id': post.id,
                            'subreddit': post.subreddit.display_name,
                            'score': getattr(post, 'score', 0),
                            'num_comments': getattr(post, 'num_comments', 0),
                            'created_utc': datetime.fromtimestamp(getattr(post, 'created_utc', 0)),
                            'permalink': f"https://reddit.com{post.permalink}"
                        }
                    )
                    videos.append(video_info)
                    
                    if len(videos) >= self.limit_per_subreddit:
                        break
            
            logger.info(f"Tìm thấy {len(videos)} videos cho topic '{topic}' từ Reddit")
            
        except Exception as e:
            logger.error(f"Lỗi search Reddit cho topic '{topic}': {e}")
        
        return videos
    
    def search_by_hashtag(self, hashtag: str) -> List[VideoItem]:
        """Tìm video theo hashtag (tương tự search topic)"""
        # Reddit không có hashtag chính thức, dùng như search keyword
        return self.search_by_topic(hashtag.replace('#', ''))
    
    def discover_videos(self, topics: List[str], hashtags: List[str]) -> List[VideoItem]:
        """Phát hiện videos từ Reddit dựa trên topics và hashtags"""
        all_videos = []
        
        if not self._init_reddit():
            return all_videos
        
        logger.info(f"Bắt đầu quét Reddit với {len(topics)} topics và {len(hashtags)} hashtags")
        
        # Search theo topics
        for topic in topics:
            videos = self.search_by_topic(topic)
            all_videos.extend(videos)
        
        # Search theo hashtags
        for hashtag in hashtags:
            videos = self.search_by_hashtag(hashtag)
            all_videos.extend(videos)
        
        # Deduplicate by URL
        seen_urls = set()
        unique_videos = []
        for video in all_videos:
            if video.url not in seen_urls:
                seen_urls.add(video.url)
                unique_videos.append(video)
        
        logger.info(f"Tổng cộng tìm thấy {len(unique_videos)} videos từ Reddit")
        return unique_videos
    
    def get_channel_videos(self, channel_id: str, limit: int = 50) -> List[VideoItem]:
        """Lấy videos từ một subreddit cụ thể"""
        videos = []
        
        if not self._init_reddit():
            return videos
        
        try:
            subreddit = self.reddit.subreddit(channel_id)
            posts = subreddit.hot(limit=limit)
            
            for post in posts:
                video_url = self.extract_video_url(post)
                if video_url:
                    video_info = VideoItem(
                        url=video_url,
                        source='reddit',
                        title=post.title[:100] if post.title else 'Reddit Video',
                        author=getattr(post, 'author', None),
                        hashtags=[channel_id],
                        metadata={
                            'post_id': post.id,
                            'subreddit': channel_id,
                            'score': getattr(post, 'score', 0),
                            'permalink': f"https://reddit.com{post.permalink}"
                        }
                    )
                    videos.append(video_info)
            
            logger.info(f"Tìm thấy {len(videos)} videos từ r/{channel_id}")
            
        except Exception as e:
            logger.error(f"Lỗi lấy videos từ r/{channel_id}: {e}")
        
        return videos
