from flask import Flask, render_template_string, request, jsonify
import requests
import time
import threading
import os
from datetime import datetime

app = Flask(__name__)

# Storage
urls_to_monitor = []
monitoring_results = []
monitoring_active = False

# Integration configurations (from environment variables)
SLACK_WEBHOOK = os.environ.get('SLACK_WEBHOOK', '')
DISCORD_WEBHOOK = os.environ.get('DISCORD_WEBHOOK', '')
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '')

def send_slack_alert(url, status, response_time):
    if not SLACK_WEBHOOK:
        return
    message = f"🔴 ALERT: {url} is DOWN! Status: {status}" if status != 200 else f"✅ {url} is BACK UP! Status: {status}"
    payload = {"text": message}
    try:
        requests.post(SLACK_WEBHOOK, json=payload, timeout=5)
    except:
        pass

def send_discord_alert(url, status, response_time):
    if not DISCORD_WEBHOOK:
        return
    message = f"🔴 ALERT: {url} is DOWN! Status: {status}" if status != 200 else f"✅ {url} is BACK UP! Status: {status}"
    payload = {"content": message}
    try:
        requests.post(DISCORD_WEBHOOK, json=payload, timeout=5)
    except:
        pass

def send_telegram_alert(url, status, response_time):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    message = f"🔴 ALERT: {url} is DOWN! Status: {status}" if status != 200 else f"✅ {url} is BACK UP! Status: {status}"
    url_tg = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    try:
        requests.post(url_tg, json=payload, timeout=5)
    except:
        pass

def send_all_alerts(url, status, response_time):
    send_slack_alert(url, status, response_time)
    send_discord_alert(url, status, response_time)
    send_telegram_alert(url, status, response_time)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>URL Monitor Pro - 50 Free Monitors</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta name="description" content="Free URL monitoring with Slack, Discord & Telegram alerts. Monitor up to 50 websites free.">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); min-height: 100vh; color: #fff; padding: 20px; }
        .container { max-width: 900px; margin: 0 auto; }
        h1 { text-align: center; margin-bottom: 10px; color: #00d4ff; }
        .tagline { text-align: center; color: #888; margin-bottom: 30px; font-size: 18px; }
        .card { background: rgba(255,255,255,0.1); border-radius: 15px; padding: 25px; margin-bottom: 20px; backdrop-filter: blur(10px); }
        .input-group { display: flex; gap: 10px; margin-bottom: 20px; flex-wrap: wrap; }
        input { flex: 1; min-width: 200px; padding: 15px; border: none; border-radius: 10px; background: rgba(255,255,255,0.15); color: #fff; font-size: 16px; }
        input::placeholder { color: rgba(255,255,255,0.5); }
        button { padding: 15px 30px; border: none; border-radius: 10px; cursor: pointer; font-size: 16px; font-weight: bold; transition: transform 0.2s; }
        button:hover { transform: scale(1.05); }
        .btn-add { background: #00d4ff; color: #1a1a2e; }
        .btn-start { background: #00ff88; color: #1a1a2e; }
        .btn-stop { background: #ff4757; color: #fff; }
        .btn-check { background: #ffa502; color: #1a1a2e; }
        .url-list { list-style: none; }
        .url-item { display: flex; justify-content: space-between; align-items: center; padding: 15px; background: rgba(255,255,255,0.05); border-radius: 10px; margin-bottom: 10px; flex-wrap: wrap; gap: 10px; }
        .url-item .url { font-size: 18px; word-break: break-all; }
        .status { padding: 5px 15px; border-radius: 20px; font-size: 14px; font-weight: bold; }
        .status.ok { background: #00ff88; color: #1a1a2e; }
        .status.error { background: #ff4757; color: #fff; }
        .status.pending { background: #ffa502; color: #1a1a2e; }
        .results { max-height: 400px; overflow-y: auto; }
        .result-item { padding: 12px; background: rgba(255,255,255,0.05); border-radius: 8px; margin-bottom: 8px; font-size: 14px; }
        .result-item .time { color: #00d4ff; font-size: 12px; }
        .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 15px; margin-bottom: 20px; }
        .stat { background: rgba(255,255,255,0.1); padding: 20px; border-radius: 10px; text-align: center; }
        .stat .value { font-size: 32px; font-weight: bold; color: #00d4ff; }
        .stat .label { font-size: 14px; opacity: 0.7; }
        .delete-btn { background: #ff4757; color: white; padding: 8px 15px; font-size: 14px; }
        .integrations { display: flex; gap: 10px; flex-wrap: wrap; margin-top: 20px; padding-top: 20px; border-top: 1px solid rgba(255,255,255,0.1); }
        .integration-badge { background: rgba(255,255,255,0.1); padding: 8px 15px; border-radius: 20px; font-size: 14px; }
        .integration-badge.enabled { background: #00ff88; color: #1a1a2e; }
        .hero-text { text-align: center; margin-bottom: 30px; }
        .hero-text h2 { color: #00ff88; margin-bottom: 10px; }
        .feature-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 20px; }
        .feature { background: rgba(255,255,255,0.05); padding: 15px; border-radius: 10px; text-align: center; }
        .feature-icon { font-size: 32px; margin-bottom: 10px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔗 URL Monitor Pro</h1>
        <p class="tagline">🚀 Monitor 50 websites FREE • Slack • Discord • Telegram Alerts</p>
        
        <div class="hero-text">
            <h2>Start Monitoring in 30 Seconds</h2>
            <p>No credit card required • 50 free monitors • Better than UptimeRobot</p>
        </div>
        
        <div class="feature-grid">
            <div class="feature"><div class="feature-icon">⚡</div>50 Free Monitors</div>
            <div class="feature"><div class="feature-icon">💬</div>Slack Alerts</div>
            <div class="feature"><div class="feature-icon">🎮</div>Discord Alerts</div>
            <div class="feature"><div class="feature-icon">✈️</div>Telegram Alerts</div>
        </div>
        
        <div class="card">
            <div class="input-group">
                <input type="text" id="urlInput" placeholder="Enter URL to monitor (e.g., https://example.com)">
                <button class="btn-add" onclick="addUrl()">+ Add URL</button>
            </div>
            
            <div class="stats">
                <div class="stat">
                    <div class="value" id="totalUrls">0</div>
                    <div class="label">/50 URLs</div>
                </div>
                <div class="stat">
                    <div class="value" id="activeMonitors">OFF</div>
                    <div class="label">Active</div>
                </div>
                <div class="stat">
                    <div class="value" id="upCount">0</div>
                    <div class="label">Up</div>
                </div>
                <div class="stat">
                    <div class="value" id="downCount">0</div>
                    <div class="label">Down</div>
                </div>
            </div>
            
            <div class="input-group">
                <button class="btn-start" onclick="startMonitoring()">▶ Start Auto-Monitor</button>
                <button class="btn-stop" onclick="stopMonitoring()">⏹ Stop</button>
                <button class="btn-check" onclick="checkNow()">🔄 Check Now</button>
            </div>
            
            <div class="integrations">
                <span class="integration-badge" id="slackStatus">💬 Slack</span>
                <span class="integration-badge" id="discordStatus">🎮 Discord</span>
                <span class="integration-badge" id="telegramStatus">✈️ Telegram</span>
            </div>
        </div>
        
        <div class="card">
            <h3>Monitored URLs</h3>
            <ul class="url-list" id="urlList"></ul>
        </div>
        
        <div class="card">
            <h3>Recent Checks</h3>
            <div class="results" id="results"></div>
        </div>
    </div>
    
    <script>
        let urls = [];
        let monitoring = false;
        
        function addUrl() {
            const url = document.getElementById('urlInput').value.trim();
            if (!url) return;
            fetch('/add_url', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({url})
            }).then(() => {
                document.getElementById('urlInput').value = '';
                loadUrls();
            });
        }
        
        function removeUrl(url) {
            fetch('/remove_url', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({url})
            }).then(() => loadUrls());
        }
        
        function loadUrls() {
            fetch('/get_urls').then(r => r.json()).then(data => {
                urls = data.urls;
                const list = document.getElementById('urlList');
                list.innerHTML = urls.map(u => `
                    <li class="url-item">
                        <span class="url">${u.url}</span>
                        <span class="status ${u.status}">${u.status === 'ok' ? '✓ UP' : u.status === 'error' ? '✗ DOWN' : '⏳'}</span>
                        <button class="delete-btn" onclick="removeUrl('${u.url}')">Delete</button>
                    </li>
                `).join('');
                
                document.getElementById('totalUrls').textContent = urls.length;
                document.getElementById('upCount').textContent = urls.filter(u => u.status === 'ok').length;
                document.getElementById('downCount').textContent = urls.filter(u => u.status === 'error').length;
                document.getElementById('activeMonitors').textContent = monitoring ? 'ON' : 'OFF';
            });
        }
        
        function startMonitoring() {
            fetch('/start_monitoring', {method: 'POST'}).then(() => {
                monitoring = true;
                loadUrls();
            });
        }
        
        function stopMonitoring() {
            fetch('/stop_monitoring', {method: 'POST'}).then(() => {
                monitoring = false;
                loadUrls();
            });
        }
        
        function checkNow() {
            fetch('/check_now', {method: 'POST'}).then(() => loadResults());
        }
        
        function loadResults() {
            fetch('/get_results').then(r => r.json()).then(data => {
                const results = document.getElementById('results');
                results.innerHTML = data.results.map(r => `
                    <div class="result-item">
                        <span class="time">${r.time}</span> - ${r.url}: 
                        <span style="color: ${r.status === 200 ? '#00ff88' : '#ff4757'}">
                            ${r.status} (${r.response_time}s)
                        </span>
                    </div>
                `).join('');
            });
        }
        
        setInterval(loadUrls, 5000);
        setInterval(loadResults, 5000);
        loadUrls();
        loadResults();
    </script>
</body>
</html>
"""

@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)

@app.route('/add_url', methods=['POST'])
def add_url():
    data = request.json
    url = data.get('url')
    if url and len(urls_to_monitor) < 50 and url not in [u['url'] for u in urls_to_monitor]:
        urls_to_monitor.append({'url': url, 'status': 'pending'})
    return jsonify({'success': True})

@app.route('/remove_url', methods=['POST'])
def remove_url():
    data = request.json
    url = data.get('url')
    urls_to_monitor[:] = [u for u in urls_to_monitor if u['url'] != url]
    return jsonify({'success': True})

@app.route('/get_urls')
def get_urls():
    return jsonify({'urls': urls_to_monitor})

@app.route('/start_monitoring', methods=['POST'])
def start_monitoring():
    global monitoring_active
    monitoring_active = True
    return jsonify({'success': True})

@app.route('/stop_monitoring', methods=['POST'])
def stop_monitoring():
    global monitoring_active
    monitoring_active = False
    return jsonify({'success': True})

@app.route('/check_now', methods=['POST'])
def check_now():
    check_all_urls()
    return jsonify({'success': True})

@app.route('/get_results')
def get_results():
    return jsonify({'results': monitoring_results[-20:]})

def check_all_urls():
    for item in urls_to_monitor:
        url = item['url']
        prev_status = item.get('status', 'pending')
        try:
            start = time.time()
            response = requests.get(url, timeout=10)
            response_time = round(time.time() - start, 2)
            status = response.status_code
            item['status'] = 'ok' if status == 200 else 'error'
            
            # Send alerts only on status change
            if prev_status != item['status']:
                send_all_alerts(url, status, response_time)
                
        except Exception as e:
            item['status'] = 'error'
            response_time = 0
            status = 'ERROR'
            if prev_status != 'error':
                send_all_alerts(url, status, response_time)
        
        monitoring_results.append({
            'url': url,
            'status': status,
            'response_time': response_time,
            'time': datetime.now().strftime('%H:%M:%S')
        })
    
    # Keep only last 50 results
    del monitoring_results[:-50]

def monitor_loop():
    while True:
        if monitoring_active:
            check_all_urls()
        time.sleep(60)  # Check every minute

if __name__ == '__main__':
    # Start monitoring thread
    thread = threading.Thread(target=monitor_loop, daemon=True)
    thread.start()
    
    app.run(host='0.0.0.0', port=10000)
