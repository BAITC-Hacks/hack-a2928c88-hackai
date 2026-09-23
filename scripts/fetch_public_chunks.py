from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import re
import urllib.request

root = Path(__file__).resolve().parent.parent
folder = root / 'docs' / 'site-chunks'
folder.mkdir(exist_ok=True)
page = (root / 'docs/site-live.html').read_text(encoding='utf-8')
urls = re.findall(r'<script[^>]+src="([^"]+)"', page)
def fetch(url):
    target = folder / url.rsplit('/', 1)[-1]
    try:
        with urllib.request.urlopen('https://edu.astanahub.com' + url, timeout=12) as r:
            target.write_bytes(r.read())
        return target.name
    except Exception as e:
        return str(e)
with ThreadPoolExecutor(max_workers=10) as pool:
    print('\n'.join(pool.map(fetch, urls)))
