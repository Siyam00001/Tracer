import os
import json
from datetime import datetime

LINKS_FILE = os.path.join(os.path.dirname(__file__), 'links.txt')
CLICKS_FILE = os.path.join(os.path.dirname(__file__), 'clicks.txt')

def save_link(uuid, target_url):
    link = {
        'uuid': uuid,
        'target_url': target_url,
        'created_at': datetime.utcnow().isoformat()
    }
    with open(LINKS_FILE, 'a', encoding='utf-8') as f:
        f.write(json.dumps(link) + '\n')

def get_link(uuid):
    if not os.path.exists(LINKS_FILE):
        return None
    with open(LINKS_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            link = json.loads(line)
            if link['uuid'] == uuid:
                return link
    return None

def save_click(click_data):
    click_data['timestamp'] = datetime.utcnow().isoformat()
    with open(CLICKS_FILE, 'a', encoding='utf-8') as f:
        f.write(json.dumps(click_data) + '\n')
