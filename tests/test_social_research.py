import json
import zipfile
from unittest.mock import patch
import pytest
from core.social_research import collect, ResearchStore, source_id, request_json
from brain.assembly import assemble_project, export_package, parse_script


def reddit_data():
    reply = {'kind': 't1', 'data': {'name': 't1_b', 'parent_id': 't1_a', 'body': 'Trả lời tiếng Việt'}}
    top = {'kind': 't1', 'data': {'name': 't1_a', 'parent_id': 't3_p', 'body': 'Meme hay',
                                'replies': {'data': {'children': [reply]}}}}
    return [{'data': {'children': [{'data': {'title': 'Bài mẫu', 'permalink': '/r/test/comments/p/', 'num_comments': 8}}]}},
            {'data': {'children': [top, {'kind': 'more', 'data': {}}]}}]


def test_reddit_tree_partial_cap_and_store(tmp_path, monkeypatch):
    monkeypatch.setenv('REDDIT_ACCESS_TOKEN', 'fixture')
    post = collect('reddit', 'p', get=lambda *args: reddit_data())
    assert post['completeness'] == 'partial'
    assert post['comments'][1]['parent_comment_id'] == 't1_a'
    assert post['retrieved_count'] == 2
    assert collect('reddit', 'p', 1, get=lambda *args: reddit_data())['completeness'] == 'capped'
    store = ResearchStore(tmp_path / 'research.db')
    store.save(post); store.save(post)
    assert store.posts() == [post]


def test_youtube_paginates_replies_and_threads(monkeypatch):
    monkeypatch.setenv('YOUTUBE_API_KEY', 'fixture')
    calls = []
    def get(url, params):
        calls.append((url, params.copy()))
        if url.endswith('/videos'):
            return {'items': [{'snippet': {'title': 'Test'}, 'statistics': {'commentCount': '4'}}]}
        if url.endswith('/commentThreads'):
            if params['pageToken']:
                return {'items': [{'snippet': {'topLevelComment': {'id': 'd', 'snippet': {'textOriginal': 'D'}}}}]}
            return {'items': [{'snippet': {'topLevelComment': {'id': 'a', 'snippet': {'textOriginal': 'A'}}, 'totalReplyCount': 2}}], 'nextPageToken': 'next'}
        if params['pageToken']:
            return {'items': [{'id': 'c', 'snippet': {'textOriginal': 'C'}}]}
        return {'items': [{'id': 'b', 'snippet': {'textOriginal': 'B'}}], 'nextPageToken': 'reply-next'}
    p = collect('youtube', 'abc', get=get)
    assert p['retrieved_count'] == 4 and p['completeness'] == 'complete'
    assert [c['parent_comment_id'] for c in p['comments']] == [None, 'a', 'a', None]
    assert len(calls) == 5


@pytest.mark.parametrize('platform', ['facebook', 'threads'])
def test_meta_cursor_and_partial(platform, monkeypatch):
    monkeypatch.setenv('FACEBOOK_ACCESS_TOKEN', 'fixture')
    monkeypatch.setenv('FACEBOOK_GRAPH_VERSION', 'v99.0')
    monkeypatch.setenv('THREADS_ACCESS_TOKEN', 'fixture')
    def get(url, params, token):
        if 'after' not in params:
            return {'id': 'p', 'text': 'Post', 'message': 'Post'}
        if params['after']:
            return {'data': [{'id': 'b', 'text': 'Reply', 'parent': {'id': 'a'}}]}
        return {'data': [{'id': 'a', 'text': 'Comment'}], 'paging': {'next': 'never-follow-untrusted-url', 'cursors': {'after': 'next'}}}
    p = collect(platform, 'p', get=get)
    assert p['retrieved_count'] == 2 and p['completeness'] == 'partial'
    assert p['comments'][1]['parent_comment_id'] == 'a'


def test_invalid_url_and_missing_config(monkeypatch):
    assert source_id('youtube', 'https://youtu.be/abc') == 'abc'
    with pytest.raises(ValueError):
        source_id('reddit', 'https://reddit.com.evil.test/comments/abc')
    monkeypatch.delenv('REDDIT_ACCESS_TOKEN', raising=False)
    with pytest.raises(ValueError, match='REDDIT_ACCESS_TOKEN'):
        collect('reddit', 'p')


def test_request_redacts_secret():
    from urllib.error import HTTPError
    with patch('core.social_research.urlopen', side_effect=HTTPError('https://test?key=SECRET', 403, 'SECRET', {}, None)):
        with pytest.raises(RuntimeError) as result:
            request_json('https://test', {'key': 'SECRET'})
        assert 'SECRET' not in str(result.value)


def test_research_survives_handoff(tmp_path, monkeypatch):
    monkeypatch.setenv('REDDIT_ACCESS_TOKEN', 'fixture')
    p = collect('reddit', 'p', get=lambda *args: reddit_data())
    project = assemble_project('Meme', parse_script('Meme'), [], tmp_path, 'Test', research_context=[p])
    output = export_package(project, tmp_path / 'handoff.zip')
    with zipfile.ZipFile(output) as z:
        assert json.loads(z.read('research_context.jsonl')) == p
        assert 'Ý kiến' in z.read('research.md').decode('utf-8')


def test_ui_selection_transfers_context(tmp_path):
    import tkinter as tk
    from types import SimpleNamespace
    from tkinter import ttk
    from ui_assembly import AssemblyPane
    from ui_research import ResearchPane
    root = tk.Tk(); root.withdraw()
    try:
        tabs = ttk.Notebook(root)
        creation = ttk.Frame(tabs); tabs.add(creation)
        pages = ttk.Notebook(creation)
        script = ttk.Frame(pages); pages.add(script)
        host = ttk.Frame(root)
        app = SimpleNamespace(sections=tabs, creation_tab=creation, creation_pages=pages, script_host=script)
        app.assembly = AssemblyPane(app, script, tmp_path)
        pane = ResearchPane(app, host, tmp_path)
        post = dict(platform='reddit', post_id='p', url='https://reddit.com', text='Bài mẫu',
                    retrieved_count=1, reported_count=1, completeness='complete',
                    comments=[dict(comment_id='a', parent_comment_id=None, text='Meme Việt', author='test', permalink='')])
        pane.store.save(post); pane.reload(); pane.posts.selection_set('0'); pane.show_post()
        pane.comments.selection_set('0'); pane.transfer()
        assert app.assembly.research_context[0]['comments'][0]['text'] == 'Meme Việt'
        pane.transfer()
        assert len(app.assembly.research_context) == 1
        app.assembly.clear_research()
        assert not app.assembly.research_context
    finally:
        root.destroy()
