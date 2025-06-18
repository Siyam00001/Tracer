from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import os
import requests
import re
from urllib.parse import urljoin, urlparse

def download_resource(url, out_path):
    try:
        r = requests.get(url, timeout=10)
        with open(out_path, 'wb') as f:
            f.write(r.content)
        return True
    except Exception:
        return False

def render_and_save(url, out_dir):
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    driver = webdriver.Chrome(options=options)
    driver.get(url)
    # Wait for body to load
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
    driver.implicitly_wait(2)
    html = driver.page_source
    screenshot_path = os.path.join(out_dir, 'screenshot.png')
    driver.save_screenshot(screenshot_path)
    driver.quit()
    os.makedirs(out_dir, exist_ok=True)
    soup = BeautifulSoup(html, 'html.parser')
    # Download and rewrite resources
    for tag, attr in [('img', 'src'), ('link', 'href'), ('script', 'src')]:
        for el in soup.find_all(tag):
            res_url = el.get(attr)
            if not res_url:
                continue
            if not res_url.startswith(('http://', 'https://', 'data:', 'javascript:')):
                res_url = urljoin(url, res_url)
            if res_url.startswith(('http://', 'https://')):
                filename = os.path.basename(urlparse(res_url).path) or 'resource'
                local_path = os.path.join(out_dir, filename)
                if download_resource(res_url, local_path):
                    el[attr] = f'./{filename}'
    # Download and rewrite CSS url() references
    for el in soup.find_all('link', rel='stylesheet'):
        css_url = el.get('href')
        if css_url and css_url.startswith(('http://', 'https://')):
            css_path = os.path.join(out_dir, os.path.basename(urlparse(css_url).path) or 'style.css')
            if os.path.exists(css_path):
                with open(css_path, 'r', encoding='utf-8', errors='ignore') as f:
                    css = f.read()
                def css_url_rewrite(match):
                    asset_url = match.group(1).strip('"\'')
                    if asset_url.startswith(('http://', 'https://', 'data:')):
                        return f'url({asset_url})'
                    abs_url = urljoin(css_url, asset_url)
                    asset_name = os.path.basename(urlparse(abs_url).path) or 'asset'
                    asset_path = os.path.join(out_dir, asset_name)
                    download_resource(abs_url, asset_path)
                    return f'url({asset_name})'
                css = re.sub(r'url\(([^)]+)\)', css_url_rewrite, css)
                with open(css_path, 'w', encoding='utf-8') as f:
                    f.write(css)
    # Save rewritten HTML
    html_path = os.path.join(out_dir, 'index.html')
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(str(soup))
    return html_path, screenshot_path
