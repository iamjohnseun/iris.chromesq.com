import os
import requests
import redis
from flask import Flask, jsonify, request, send_from_directory
from validators import url as validate_url
from celery.result import AsyncResult
from celery.states import PENDING, SUCCESS, FAILURE, STARTED, RETRY
from urllib.parse import urlparse

from config import Config
from main import main
from tasks import process_website_task
from web_scraper import get_urls_to_process

app = Flask(__name__)
app.config.from_object(Config)

def normalize_input_url(url):
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    return url

def is_valid_url(url):
    if not url:
        return False
    normalized_url = normalize_input_url(url)
    return validate_url(normalized_url)

def is_small_website(url):
    try:
        response = requests.get(url, timeout=Config.SYNCHRONOUS_THRESHOLD)
        response.raise_for_status()
        if response.content is not None:
            content_length = len(response.content)
        else:
            content_length = 0
        return content_length < Config.SMALL_WEBSITE_THRESHOLD
    except Exception as e:
        return False

def is_absolute_path(url):
    parsed = urlparse(normalize_input_url(url))
    return bool(parsed.path) and parsed.path != '/' and not parsed.path.rstrip('/') == ''

@app.route('/', methods=['GET'])
def home():
    return jsonify({
        "status": "online",
        "message": "Iris API is running",
        "version": "1.0"
    })

@app.route('/', methods=['POST'])
def generate_corpus_route():
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                "status": "error", 
                "message": "Request body is required"
            }), 400
            
        url = data.get('url')
        if not is_valid_url(url):
            return jsonify({
                "status": "error", 
                "message": "Invalid or missing URL in request"
            }), 400
        
        normalized_url = normalize_input_url(url) 
        single_page = is_absolute_path(url)
            
        result = main(normalized_url, single_page=single_page)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/process', methods=['POST'])        
def process_website():
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                "status": "error", 
                "message": "Request body is required"
            }), 400
            
        url = data.get('url')
        url_list = data.get('urls') or []
        
        if not isinstance(url_list, list):
            return jsonify({
                "status": "error", 
                "message": "The provided 'urls' must be a list"
            }), 400
        
        if url_list and url:
            url_list = [url for url in url_list if is_valid_url(url)]
        elif url:
            url_list = [url] if is_valid_url(url) else []
            
        if not url_list:
            return jsonify({
                "status": "error", 
                "message": "Invalid or missing URL in request"
            }), 400
        
        url_list = [normalize_input_url(url) for url in url_list]
        
        if url_list and len(url_list) > 1:
            task = process_website_task.delay(url_list, single_page=False)
            return jsonify({
                'task_id': task.id,
                'status': 'processing',
                'status_url': f'{Config.APP_URL}/status/{task.id}'
            })
        else:  # Single URL case
            single_page = is_absolute_path(url_list[0])
            urls = get_urls_to_process(url_list[0], single_page)
            
            if not urls:
                return jsonify({
                    "status": "error",
                    "message": "No URLs found to process"
                }), 400
                
            total_urls = len(urls)
            
            if single_page or (total_urls <= Config.SYNCHRONOUS_THRESHOLD and is_small_website(url_list[0])):
                # Synchronous processing
                result = process_website_task.apply(args=[url_list[0], single_page])
                return jsonify(result.get())
            else:
                # Asynchronous processing
                task = process_website_task.delay(url_list[0], single_page)
                return jsonify({
                    'task_id': task.id,
                    'status': 'processing',
                    'status_url': f'{Config.APP_URL}/status/{task.id}'
                })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
        
@app.route('/status/<task_id>', methods=['GET'])
def check_task_status(task_id):
    redis_client = redis.Redis(host='localhost', port=6379, db=0)
    try:
        task_result = AsyncResult(task_id)
        task_key = f"celery-task-meta-{task_id}"
        
        if not redis_client.exists(task_key):
            return {
                "state": "NOT_FOUND",
                "status": "task_not_found",
                "task_id": task_id,
                "message": "This task was not found. It may have expired or the provided task ID may be incorrect."
            }
            
        response = {
            "state": task_result.state,
            "status": task_result.state.lower(),
            "task_id": task_id,
            "status_url": f"{Config.APP_URL}/status/{task_id}"
        }
        
        if task_result.state == PENDING:
            response.update({
                'status': 'task pending',
                'message': 'Task is in queue and waiting to be processed.'
            })
        elif task_result.state == STARTED and task_result.info:
            response.update({
                'status': task_result.info.get('status', ''),
                'url': task_result.info.get('url'),
                'progress': f"{task_result.info.get('current', 0)} / {task_result.info.get('total', 1)}",
                'progress_percentage': int((task_result.info.get('current', 0) / task_result.info.get('total', 1)) * 100)
            })
        elif task_result.state == RETRY:
            response.update({
                'status': 'task retrying',
                'message': 'Task encountered an issue, It will be retried.'
            })
        elif task_result.ready():
            if task_result.successful():
                response.update({
                    "state": SUCCESS,
                    "status": "completed",
                    "result": task_result.get()
                })
            else:
                response.update({
                    "state": FAILURE,
                    "status": "failed",
                    "error": str(task_result.result)
                })
        
        return response
    
    except Exception as e:
        return {
            "state": "ERROR",
            "status": "error",
            "message": str(e)
        }


@app.route('/download/<filename>')
def download_file(filename):
    if not os.path.exists(os.path.join('download', filename)):
        return jsonify({'error': 'File not found'}), 404
    return send_from_directory('download', filename)
    

@app.route('/git', methods=['POST', 'GET'])
def git_webhook():
    try:
        import subprocess
        from datetime import datetime
        subprocess.run(['git', 'pull'], cwd='/var/www/iris')
        subprocess.run(['systemctl', 'restart', 'iris'])
        return jsonify({
            "status": "updated",
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
@app.errorhandler(404)
def not_found(error):
    return jsonify({
        "status": "error",
        "message": "Route not found"
    }), 404

@app.errorhandler(405)
def method_not_allowed(error):
    return jsonify({
        "status": "error",
        "message": "Method not allowed for this endpoint"
    }), 405

if __name__ == '__main__':
    os.makedirs('download', exist_ok=True)
    app.run(host='0.0.0.0', port=5000, debug=Config.DEBUG)