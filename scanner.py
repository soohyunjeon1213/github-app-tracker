#!/usr/bin/env python3
"""Incremental discovery by GitHub topic search. Python stdlib only."""
import datetime as dt
import json
import os
import pathlib
import time
import urllib.error
import urllib.parse
import urllib.request

BASE = pathlib.Path(__file__).resolve().parent
CONFIG = BASE / 'config.json'
DATABASE = BASE / 'data/repos.json'
OUTPUT = BASE / 'docs/data.json'
API = 'https://api.github.com/search/repositories'

def load_json(path, fallback):
    return json.loads(path.read_text()) if path.exists() else fallback

def query(topic, page, token):
    params = urllib.parse.urlencode({'q': f'topic:{topic} fork:false archived:false', 'sort':'updated', 'order':'desc', 'per_page':100, 'page':page})
    request = urllib.request.Request(API+'?'+params, headers={
        'Accept':'application/vnd.github+json', 'User-Agent':'Mac-App-Discovery-Tracker',
        'X-GitHub-Api-Version':'2022-11-28', **({'Authorization':'Bearer '+token} if token else {})})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(request, timeout=35) as response:
                return json.load(response)
        except urllib.error.HTTPError as e:
            reset = e.headers.get('X-RateLimit-Reset')
            if e.code in (403,429) and reset and attempt < 3:
                pause = max(1, min(90, int(reset)-int(time.time())+2))
                time.sleep(pause)
                continue
            if 500 <= e.code < 600 and attempt < 3:
                time.sleep(2 ** attempt)
                continue
            raise RuntimeError(f'GitHub API HTTP {e.code}: {e.read(250).decode(errors="replace")}') from e
        except (TimeoutError, OSError) as e:
            if attempt == 3:
                raise RuntimeError(str(e)) from e
            time.sleep(2 ** attempt)

def normalize(item, topic, first_seen):
    return {'id':item['id'], 'name':item['name'], 'full_name':item['full_name'],
        'url':item['html_url'], 'description':item.get('description') or '',
        'stars':item.get('stargazers_count',0), 'language':item.get('language'),
        'license':(item.get('license') or {}).get('spdx_id'),
        'topics':sorted(set(item.get('topics') or []) | {topic}),
        'matching_topics':[topic], 'created_at':item.get('created_at'),
        'updated_at':item.get('updated_at'), 'pushed_at':item.get('pushed_at'),
        'first_seen':first_seen, 'release_url':item['html_url']+'/releases',
        'mac_compatibility':'unverified','apple_silicon':'unverified',
        'installed_size':'unverified'}

def merge(previous, fresh):
    fresh['first_seen'] = previous['first_seen']
    fresh['matching_topics'] = sorted(set(previous.get('matching_topics',[])) | set(fresh['matching_topics']))
    fresh['topics'] = sorted(set(previous.get('topics',[])) | set(fresh['topics']))
    return fresh

def scan(fetch=query, now=None):
    now = now or dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')
    config = load_json(CONFIG, {})
    data = load_json(DATABASE, {'schema':1,'repositories':{},'scans':[],'last_success':None})
    repos = data.setdefault('repositories',{})
    errors = []
    stats = []
    additions = 0
    token = os.environ.get('GITHUB_TOKEN','')
    budget = min(150, max(1,int(config.get('scan',{}).get('max_search_requests',80))))
    pages = min(10, max(1,int(config.get('scan',{}).get('pages_per_topic',3))))
    scanned = 0
    for entry in config.get('topics',[]):
        topic = entry['name'].strip().lower()
        if not entry.get('enabled',True) or not topic:
            continue
        count, status = 0, 'complete'
        for page in range(1,pages+1):
            if scanned >= budget:
                status = 'incomplete: request budget reached'
                break
            scanned += 1
            try:
                result = fetch(topic,page,token)
                items = result.get('items',[])
                for item in items:
                    key = str(item['id'])
                    fresh = normalize(item,topic,now)
                    if key not in repos:
                        repos[key] = fresh
                        additions += 1
                    else:
                        repos[key] = merge(repos[key],fresh)
                    count += 1
                if result.get('incomplete_results'):
                    status = 'incomplete: GitHub search response'
                if result.get('total_count',0) > 1000:
                    status = 'incomplete: GitHub search caps results at 1000'
                if len(items)<100:
                    break
                if page==pages:
                    status = 'incomplete: configured page limit reached' if status=='complete' else status
                time.sleep(2.2)  # Search API has its own restrictive rate limits.
            except Exception as exc:
                status='error: '+str(exc)
                errors.append({'topic':topic,'message':str(exc)})
                break
        stats.append({'topic':topic,'observed':count,'status':status})
    record = {'time':now,'new':additions,'topics':stats,'errors':errors}
    data['scans'] = (data.get('scans',[])+[record])[-50:]
    if any(s['observed']>0 for s in stats):
        data['last_success']=now
    DATABASE.parent.mkdir(exist_ok=True)
    DATABASE.write_text(json.dumps(data,ensure_ascii=False,separators=(',',':'))+'\n')
    OUTPUT.parent.mkdir(exist_ok=True)
    OUTPUT.write_text(json.dumps({'repositories':list(repos.values()),'last_success':data.get('last_success'), 'latest_scan':record, 'scan_history':data['scans'][-10:]},ensure_ascii=False,separators=(',',':'))+'\n')
    print(f'{additions} new; {len(repos)} total; {len(errors)} topic errors')
    return record

if __name__=='__main__':
    scan()
