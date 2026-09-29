"""Read-only social research with stable IDs; portable to Colab, stdlib only."""
import json
import os
import re
import sqlite3
import time
from pathlib import Path
from urllib.parse import urlencode, urlparse, parse_qs
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

REQUIRED = {'reddit': ('REDDIT_ACCESS_TOKEN',), 'youtube': ('YOUTUBE_API_KEY',),
            'facebook': ('FACEBOOK_ACCESS_TOKEN', 'FACEBOOK_GRAPH_VERSION'),
            'threads': ('THREADS_ACCESS_TOKEN',)}

def connection_status(platform):
    missing = [k for k in REQUIRED[platform] if not os.environ.get(k)]
    return 'Thiếu: ' + ', '.join(missing) if missing else 'Đã cấu hình; quyền nguồn sẽ được kiểm tra khi thu thập.'

def request_json(url, params=None, token=None):
    headers = {'User-Agent': 'PipelineResearch/1.0', 'Accept': 'application/json'}
    if token:
        headers['Authorization'] = 'Bearer ' + token
    try:
        with urlopen(Request(url + ('?' + urlencode(params) if params else ''), headers=headers), timeout=25) as r:
            return json.load(r)
    except HTTPError as e:
        raise RuntimeError(f'HTTP {e.code}: kiểm tra quyền/token hoặc giới hạn nguồn; thử lại sau.') from None
    except (URLError, TimeoutError, ValueError):
        raise RuntimeError('Không đọc được phản hồi nguồn. Kiểm tra mạng và thử lại.') from None

def source_id(platform, value):
    value = value.strip()
    if re.fullmatch(r'[A-Za-z0-9_-]+', value):
        return value
    p = urlparse(value)
    host = (p.hostname or '').lower()
    if p.scheme == 'https':
        if platform == 'reddit' and (host == 'reddit.com' or host.endswith('.reddit.com')):
            m = re.search(r'/comments/([a-z0-9]+)', p.path)
            if m:
                return m[1]
        if platform == 'reddit' and host == 'redd.it':
            return source_id(platform, p.path.strip('/'))
        if platform == 'youtube' and host in ('youtube.com', 'www.youtube.com', 'm.youtube.com', 'youtu.be'):
            v = parse_qs(p.query).get('v', [''])[0]
            if not v and (host == 'youtu.be' or p.path.startswith(('/shorts/', '/live/'))):
                v = p.path.rstrip('/').split('/')[-1]
            if re.fullmatch(r'[A-Za-z0-9_-]+', v):
                return v
    raise ValueError('URL không hợp lệ. Facebook cần PageID_PostID; Threads cần ID số từ API.')

def collect(platform, value, limit=100, get=request_json):
    limit = int(limit)
    if platform not in REQUIRED or not 1 <= limit <= 1000:
        raise ValueError('Chọn nguồn hợp lệ và giới hạn 1–1000 bình luận/bài.')
    missing = [k for k in REQUIRED[platform] if not os.environ.get(k)]
    if missing:
        raise ValueError('Cần cấu hình ' + ', '.join(missing))
    pid = source_id(platform, value)
    post = dict(platform=platform, post_id=pid, text='', url=value, reported_count=None,
                fetched_at=time.time(), comments=[], completeness='partial')
    seen = set()
    def add(cid, parent, text, author='', score=0, created=None, url=''):
        if not cid or cid in seen or len(seen) >= limit:
            return
        seen.add(cid)
        post['comments'].append(dict(comment_id=cid, parent_comment_id=parent, text=text,
                                    author=author, score=score, created_at=created, permalink=url))
    if platform == 'reddit':
        data = get(f'https://oauth.reddit.com/comments/{pid}',
                   {'limit': min(limit, 100), 'sort': 'top', 'raw_json': 1}, os.environ['REDDIT_ACCESS_TOKEN'])
        item = data[0]['data']['children'][0]['data']
        post.update(text=item.get('title', '') + '\n' + item.get('selftext', ''),
                    url='https://www.reddit.com' + item['permalink'], reported_count=item.get('num_comments'))
        more = False
        def walk(nodes):
            nonlocal more
            for node in nodes:
                row = node.get('data', {})
                if node.get('kind') == 'more':
                    more = True
                    continue
                if node.get('kind') != 't1':
                    continue
                parent = row.get('parent_id', '')
                add(row['name'], parent if parent.startswith('t1_') else None, row.get('body', ''),
                    row.get('author', ''), row.get('score', 0), row.get('created_utc'),
                    'https://www.reddit.com' + row.get('permalink', ''))
                if isinstance(row.get('replies'), dict):
                    walk(row['replies'].get('data', {}).get('children', []))
        walk(data[1]['data']['children'])
        post['completeness'] = 'partial' if more else 'complete'
    elif platform == 'youtube':
        key = os.environ['YOUTUBE_API_KEY']
        base = 'https://www.googleapis.com/youtube/v3/'
        data = get(base + 'videos', {'part': 'snippet,statistics', 'id': pid, 'key': key})
        if not data.get('items'):
            raise ValueError('Không tìm thấy video hoặc video không truy cập được.')
        item = data['items'][0]
        post.update(text=item['snippet'].get('title', '') + '\n' + item['snippet'].get('description', ''),
                    url=f'https://www.youtube.com/watch?v={pid}', reported_count=item.get('statistics', {}).get('commentCount'))
        def yt(row, parent=None):
            s = row['snippet']
            add(row['id'], parent, s.get('textOriginal', s.get('textDisplay', '')), s.get('authorDisplayName', ''),
                s.get('likeCount', 0), s.get('publishedAt'), post['url'] + '&lc=' + row['id'])
        page = ''
        pages = set()
        while True:
            data = get(base + 'commentThreads', {'part': 'snippet', 'videoId': pid, 'maxResults': 100,
                       'textFormat': 'plainText', 'key': key, 'pageToken': page})
            for row in data.get('items', []):
                top = row['snippet']['topLevelComment']
                yt(top)
                rp, rpages = '', set()
                if row['snippet'].get('totalReplyCount', 0):
                    while len(seen) < limit:
                        replies = get(base + 'comments', {'part': 'snippet', 'parentId': top['id'], 'maxResults': 100,
                                      'textFormat': 'plainText', 'key': key, 'pageToken': rp})
                        for reply in replies.get('items', []):
                            yt(reply, top['id'])
                        rp = replies.get('nextPageToken', '')
                        if not rp:
                            break
                        if rp in rpages:
                            raise RuntimeError('Nguồn trả trang lặp; dừng để tránh chạy vô hạn.')
                        rpages.add(rp)
                if len(seen) >= limit:
                    break
            page = data.get('nextPageToken', '')
            if len(seen) >= limit or not page:
                post['completeness'] = 'complete' if not page and len(seen) < limit else 'capped'
                break
            if page in pages:
                raise RuntimeError('Nguồn trả trang lặp; dừng để tránh chạy vô hạn.')
            pages.add(page)
    else:
        token = os.environ[REQUIRED[platform][0]]
        if platform == 'facebook':
            version = os.environ['FACEBOOK_GRAPH_VERSION']
            if not re.fullmatch(r'v\d+\.\d+', version):
                raise ValueError('FACEBOOK_GRAPH_VERSION cần dạng vNN.0 theo phiên bản app Meta.')
            base = f'https://graph.facebook.com/{version}/'
            item = get(base + pid, {'fields': 'id,message,permalink_url'}, token)
            post.update(text=item.get('message', ''), url=item.get('permalink_url', value))
            fields, edge = 'id,message,from,created_time,like_count,parent', 'comments'
        else:
            base = 'https://graph.threads.com/v1.0/'
            item = get(base + pid, {'fields': 'id,text,permalink'}, token)
            post.update(text=item.get('text', ''), url=item.get('permalink', value))
            fields, edge = 'id,text,username,timestamp,permalink,replied_to', 'conversation'
        cursor, cursors = '', set()
        while True:
            data = get(base + pid + '/' + edge, {'fields': fields, 'limit': min(100, limit), 'after': cursor}, token)
            for row in data.get('data', []):
                parent = row.get('parent', row.get('replied_to', {})) or {}
                parent_id = parent.get('id')
                add(row['id'], parent_id if parent_id != pid else None, row.get('text', row.get('message', '')),
                    row.get('username', (row.get('from') or {}).get('name', '')), row.get('like_count', 0),
                    row.get('timestamp', row.get('created_time')), row.get('permalink', ''))
            paging = data.get('paging', {})
            cursor = paging.get('cursors', {}).get('after', '')
            if len(seen) >= limit or not paging.get('next') or not cursor:
                break
            if cursor in cursors:
                raise RuntimeError('Nguồn trả trang lặp; dừng để tránh chạy vô hạn.')
            cursors.add(cursor)
    if len(seen) >= limit:
        post['completeness'] = 'capped'
    post['retrieved_count'] = len(post['comments'])
    return post

class ResearchStore:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.path) as db:
            db.execute('CREATE TABLE IF NOT EXISTS social_posts (platform TEXT, post_id TEXT, payload TEXT NOT NULL, PRIMARY KEY(platform, post_id))')
    def save(self, post):
        with sqlite3.connect(self.path) as db:
            db.execute('INSERT OR REPLACE INTO social_posts VALUES (?, ?, ?)',
                       (post['platform'], post['post_id'], json.dumps(post, ensure_ascii=False)))
    def posts(self):
        with sqlite3.connect(self.path) as db:
            return [json.loads(r[0]) for r in db.execute('SELECT payload FROM social_posts ORDER BY rowid DESC')]
