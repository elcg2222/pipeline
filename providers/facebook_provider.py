"""
Facebook Provider - Quét video từ Facebook (Pages, Groups, Reels)
Lưu ý: Facebook API rất hạn chế, cần access token hợp lệ
Hỗ trợ: Public Pages, Groups (nếu có quyền), Reels
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime
import re
import json

from .base import BaseProvider
from core.schema import VideoItem

logger = logging.getLogger(__name__)


class FacebookProvider(BaseProvider):
    """Provider cho Facebook"""
    
    name = "facebook"
    description = "Quét video từ Facebook Pages, Groups, Reels"
    
    def __init__(self, config: Dict):
        super().__init__(config)
        self.config = config.get('facebook', {})
        self.access_token = self.config.get('access_token', '')
        self.app_id = self.config.get('app_id', '')
        self.app_secret = self.config.get('app_secret', '')
        
        # Danh sách pages/groups cần quét
        self.pages = self.config.get('pages', [])
        self.groups = self.config.get('groups', [])
        self.limit_per_source = self.config.get('limit_per_source', 50)
        
        # Tự động scrape (không cần API) - chỉ hoạt động với public content
        self.use_scraper = self.config.get('use_scraper', True)
        
        self.graph_api_url = "https://graph.facebook.com/v18.0"
    
    def _make_graph_request(self, endpoint: str, params: Dict = None) -> Optional[Dict]:
        """Gửi request tới Facebook Graph API"""
        try:
            import requests
            
            if not params:
                params = {}
            
            if self.access_token:
                params['access_token'] = self.access_token
            else:
                logger.warning("Không có access token, một số tính năng sẽ bị giới hạn")
            
            url = f"{self.graph_api_url}/{endpoint}"
            response = requests.get(url, params=params, timeout=30)
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Facebook API error {response.status_code}: {response.text}")
                return None
                
        except ImportError:
            logger.error("Chưa cài đặt requests. Chạy: pip install requests")
            return None
        except Exception as e:
            logger.error(f"Lỗi request Facebook API: {e}")
            return None
    
    def extract_video_from_post(self, post: Dict) -> Optional[VideoItem]:
        """Trích xuất thông tin video từ Facebook post"""
        try:
            # Kiểm tra nếu post có video
            if 'attachments' in post:
                attachments = post['attachments']
                if 'data' in attachments and len(attachments['data']) > 0:
                    attachment = attachments['data'][0]
                    
                    if attachment.get('type') == 'video' or 'media' in attachment:
                        video_data = attachment.get('media', {})
                        
                        # Lấy video URL
                        video_url = None
                        if 'source' in video_data:
                            video_url = video_data['source']
                        elif 'playable_url' in video_data:
                            video_url = video_data['playable_url']
                        elif 'playable_url_quality_hd' in video_data:
                            video_url = video_data['playable_url_quality_hd']
                        
                        if video_url:
                            # Trích xuất metadata
                            title = post.get('message', post.get('story', 'Facebook Video'))[:100]
                            description = post.get('message', '')[:500] if 'message' in post else ''
                            
                            # Extract hashtags từ message
                            hashtags = []
                            if 'message' in post:
                                hashtag_pattern = r'#\w+'
                                hashtags = re.findall(hashtag_pattern, post['message'])
                            
                            return VideoItem(
                                url=video_url,
                                source='facebook',
                                title=title,
                                description=description,
                                author=post.get('from', {}).get('name', 'Unknown'),
                                hashtags=hashtags,
                                metadata={
                                    'post_id': post.get('id'),
                                    'created_time': post.get('created_time'),
                                    'permalink_url': post.get('permalink_url'),
                                    'likes': post.get('reactions', {}).get('summary', {}).get('total_count', 0),
                                    'comments': post.get('comments', {}).get('summary', {}).get('total_count', 0),
                                    'shares': post.get('shares', {}).get('count', 0)
                                }
                            )
            
            # Kiểm tra native video fields
            if 'source' in post:
                video_url = post['source']
                title = post.get('title', post.get('message', 'Facebook Video'))[:100]
                
                hashtags = []
                if 'message' in post:
                    hashtag_pattern = r'#\w+'
                    hashtags = re.findall(hashtag_pattern, post['message'])
                
                return VideoItem(
                    url=video_url,
                    source='facebook',
                    title=title,
                    description=post.get('description', '')[:500],
                    author=post.get('from', {}).get('name', 'Unknown'),
                    hashtags=hashtags,
                    metadata={
                        'post_id': post.get('id'),
                        'created_time': post.get('created_time'),
                        'permalink_url': post.get('permalink_url')
                    }
                )
            
        except Exception as e:
            logger.error(f"Lỗi trích xuất video từ Facebook post: {e}")
        
        return None
    
    def get_page_videos(self, page_id: str) -> List[VideoItem]:
        """Lấy videos từ một Facebook Page"""
        videos = []
        
        if not self.access_token:
            logger.warning("Không có access token, không thể lấy videos từ Page")
            return videos
        
        try:
            # Lấy posts từ page
            endpoint = f"{page_id}/posts"
            params = {
                'fields': 'id,message,story,created_time,permalink_url,reactions,comments,shares,from,attachments{media,source,type},source,title,description',
                'limit': self.limit_per_source
            }
            
            data = self._make_graph_request(endpoint, params)
            
            if data and 'data' in data:
                for post in data['data']:
                    video_info = self.extract_video_from_post(post)
                    if video_info:
                        videos.append(video_info)
                        
                        if len(videos) >= self.limit_per_source:
                            break
            
            logger.info(f"Tìm thấy {len(videos)} videos từ Page {page_id}")
            
        except Exception as e:
            logger.error(f"Lỗi lấy videos từ Page {page_id}: {e}")
        
        return videos
    
    def get_group_videos(self, group_id: str) -> List[VideoItem]:
        """Lấy videos từ một Facebook Group"""
        videos = []
        
        if not self.access_token:
            logger.warning("Không có access token, không thể lấy videos từ Group")
            return videos
        
        try:
            endpoint = f"{group_id}/feed"
            params = {
                'fields': 'id,message,story,created_time,permalink_url,reactions,comments,shares,from,attachments{media,source,type},source,title,description',
                'limit': self.limit_per_source
            }
            
            data = self._make_graph_request(endpoint, params)
            
            if data and 'data' in data:
                for post in data['data']:
                    video_info = self.extract_video_from_post(post)
                    if video_info:
                        videos.append(video_info)
                        
                        if len(videos) >= self.limit_per_source:
                            break
            
            logger.info(f"Tìm thấy {len(videos)} videos từ Group {group_id}")
            
        except Exception as e:
            logger.error(f"Lỗi lấy videos từ Group {group_id}: {e}")
        
        return videos
    
    def search_by_topic(self, topic: str) -> List[VideoItem]:
        """Tìm video theo topic (chỉ hoạt động với access token hợp lệ)"""
        videos = []
        
        if not self.access_token:
            logger.warning("Không có access token, không thể search Facebook")
            return videos
        
        try:
            # Search posts chứa topic
            endpoint = "search"
            params = {
                'q': topic,
                'type': 'post',
                'fields': 'id,message,story,created_time,permalink_url,reactions,comments,shares,from,attachments{media,source,type},source,title,description',
                'limit': self.limit_per_source
            }
            
            data = self._make_graph_request(endpoint, params)
            
            if data and 'data' in data:
                for post in data['data']:
                    video_info = self.extract_video_from_post(post)
                    if video_info:
                        videos.append(video_info)
            
            logger.info(f"Tìm thấy {len(videos)} videos cho topic '{topic}' từ Facebook")
            
        except Exception as e:
            logger.error(f"Lỗi search Facebook cho topic '{topic}': {e}")
        
        return videos
    
    def search_by_hashtag(self, hashtag: str) -> List[VideoItem]:
        """Tìm video theo hashtag"""
        # Facebook Graph API không support search hashtag trực tiếp
        # Phải search như topic bình thường
        return self.search_by_topic(hashtag.replace('#', ''))
    
    def scrape_public_reels(self, limit: int = 50) -> List[VideoItem]:
        """Scrape public reels (phương pháp thay thế khi không có API)"""
        # Lưu ý: Đây chỉ là placeholder, thực tế cần dùng Selenium hoặc Playwright
        # để scrape Facebook Reels vì API rất hạn chế
        logger.warning("Facebook Reels scraping chưa được implement đầy đủ. Cần dùng Selenium/Playwright.")
        return []
    
    def discover_videos(self, topics: List[str], hashtags: List[str]) -> List[VideoItem]:
        """Phát hiện videos từ Facebook dựa trên topics và hashtags"""
        all_videos = []
        
        logger.info(f"Bắt đầu quét Facebook với {len(topics)} topics và {len(hashtags)} hashtags")
        
        # Lấy videos từ các pages đã cấu hình
        for page_id in self.pages:
            videos = self.get_page_videos(page_id)
            all_videos.extend(videos)
        
        # Lấy videos từ các groups đã cấu hình
        for group_id in self.groups:
            videos = self.get_group_videos(group_id)
            all_videos.extend(videos)
        
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
        
        logger.info(f"Tổng cộng tìm thấy {len(unique_videos)} videos từ Facebook")
        return unique_videos
    
    def get_channel_videos(self, channel_id: str, limit: int = 50) -> List[VideoItem]:
        """Lấy videos từ một page/group cụ thể"""
        # Kiểm tra xem là page hay group
        if not self.access_token:
            return []
        
        # Thử lấy từ page trước
        videos = self.get_page_videos(channel_id)
        
        # Nếu không có, thử lấy từ group
        if not videos:
            videos = self.get_group_videos(channel_id)
        
        return videos[:limit]
