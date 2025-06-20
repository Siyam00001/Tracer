# Tracer

Tracer is a Flask-based web application for discreet IP tracking, redirection, and advanced website cloning. It allows you to generate trackable links, capture user technical data, and create runtime or static clones of target websites—including dynamic content and login forms.

## Features
- **Trackable Links:** Generate unique links to capture IP, geolocation, device, and browser info.
- **Redirection:** Seamlessly redirect users after tracking.
- **Website Cloning:**
  - Static and dynamic (Selenium-based) cloning of any website.
  - Special templates for Facebook/Instagram.
  - Resource rewriting for high-fidelity clones.
- **Credential Capture:** Injects dummy login forms and stores submitted credentials.
- **Proxy Dynamic Requests:** Proxies AJAX/fetch/XHR requests for undetectable clones.
- **Data Storage:** All tracking and credential data is stored in `.txt` files.
- **Admin Endpoints:** API endpoints for link management and statistics.

## Usage
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Run the app:
   ```bash
   python run.py
   ```
3. Open your browser to `http://localhost:5000`.
4. Use the web UI to generate trackable links and clone sites.

## File Structure
- `app.py` / `run.py`: App entry points
- `routes.py`: All main routes and logic
- `models.py`: Data storage helpers
- `browser_clone.py`: Selenium-based dynamic cloning
- `templates/`: Frontend HTML
- `clones/`: Stores runtime clones
- `clone_template/`: Static templates for special sites
- `links.txt`, `clicks.txt`, `dummy_creds.txt`: Data files

## Disclaimer
This project is for educational and research purposes only. Do not use it for unethical or illegal activities.
