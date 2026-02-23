from flask import Flask, render_template_string, request, jsonify
import requests
import time
import threading
from datetime import datetime

app = Flask(__name__)

# Storage
urls_to_monitor = []
monitoring_results = []
monitoring_active = False

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>URL Monitor Pro</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); min-height: 100vh; color: #fff; padding: 20px; }
        .container { max-width: 900px; margin: 0 auto; }
        h1 { text-align: center; margin-bottom: 30px; color: #00d4ff; }
        .card { background: rgba(255,255,255,0.1); border-radius: 15px; padding: 25px; margin-bottom: 20px; backdrop-filter: blur(10px); }
        .input-group { display: flex; gap: 10px; margin-bottom: 20px; }
        input { flex: 1; padding: 15px; border: none; border-radius: 10px; background: rgba(255,255,255,0.15); color: #fff; font-size: 16px; }
        input::placeholder { color: rgba(255,255,255,0.5); }
        button { padding: 15px 30px; border: none; border-radius: 10px; cursor: pointer; font-size: 16px; font-weight: bold; transition: transform 0.2s; }
        button:hover { transform: scale(1.05); }
        .btn-add { background: #00d4ff; color: #1a1a2e; }
        .btn-start { background: #00ff88; color: #1a1a2e; }
        .btn-stop { background: #ff4757; color: #fff; }
        .btn-check { background: #ffa502; color: #1a1a2e; }
        .url-list { list-style: none; }
        .url-item { display: flex; justify-content: space-between; align-items: center; padding: 15px; background: rgba(255,255,255,0.05); border-radius: 10px; margin-bottom: 10px; }
        .url-item .url { font-size: 18px; }
        .status { padding: 5px 15px; border-radius: 20px; font-size: 14px; font-weight: bold; }
        .status.ok { background: #00ff88; color: #1a1a2e; }
        .status.error { background: #ff4757; color: #fff; }
        .status.pending { background: #ffa502; color: #1a1a2e; }
        .results { max-height: 400px; overflow-y: auto; }
        .result-item { padding: 12px; background: rgba(255,255,255,0.05); border-radius: 8px; margin-bottom: 8px; font-size: 14px; }
        .result-item .time { color: #00d4ff; font-size: 12px; }
        .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px; margin-bottom: 20px; }
        .stat { background: rgba(255,255,255,0.1); padding: 20px; border-radius: 10px; text-align: center; }
        .stat .value { font-size: 32px; font-weight: bold; color: #00d4ff; }
        .stat .label { font-size: 14px; opacity: 0.7; }
        .delete-btn { background: #ff4757; color: white; padding: 8px 15px; font-size: 14px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔗 URL Monitor Pro</h1>
        
        <div class="card">
            <div class="input-group">
                <input type="text" id="urlInput" placeholder="Enter URL to monitor (e.g., https://example.com)">
                <button class="btn-add" onclick="addUrl()">+ Add URL</button>
            </div>
            
            <div class="stats">
                <div class="stat">
                    <div class="value" id="totalUrls">0</div>
                    <div class="label">URLs</div>
                </div>
                <div class="stat">
                    <div class="value" id="activeMonitors">0</div>
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
    if url and url not in [u['url'] for u in urls_to_monitor]:
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
        try:
            start = time.time()
            response = requests.get(url, timeout=10)
            response_time = round(time.time() - start, 2)
            status = response.status_code
            item['status'] = 'ok' if status == 200 else 'error'
        except Exception as e:
            item['status'] = 'error'
            response_time = 0
            status = 'ERROR'
        
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
