import json
import os
import time
from celery_config import celery_app
from config import Config
from main import main
from urllib.parse import urlparse

def get_output_filename(url, job_id):
    domain = urlparse(url).netloc.replace('www.', '') or 'local'
    return f"{domain}-{job_id}.json"

@celery_app.task(bind=True)
def process_website_task(self, url, single_page=False):
    steps = [
        "setting up task",
        "initializing models",
        "fetching content",
        "processing content",
        "generating responses",
        "saving results"
    ]
    total_steps = len(steps)
    
    try:
        # Step 1: Create directory structure
        self.update_state(
            state='STARTED',
            meta={
                'status': steps[0],
                'progress': f"1/{total_steps}",
                'url': url
            }
        )
        
        # Create output directory
        output_dir = Config.OUTPUT_DIRECTORY
        os.makedirs(output_dir, exist_ok=True)
        
        # Create filename with domain and task ID
        filename = get_output_filename(url, self.request.id)
        
        # Step 2: Initialize model
        self.update_state(
            state='STARTED',
            meta={
                'status': steps[1],
                'progress': f"2/{total_steps}",
                'url': url
            }
        )
        
        generation_start_time = time.time()
        
        # Step 3-5: Process using main function
        self.update_state(
            state='STARTED',
            meta={
                'status': steps[3],
                'progress': f"3/{total_steps}",
                'url': url
            }
        )
        
        result = main(url, single_page)
        # Add generation time to stats
        result['stats']['generation_time'] = time.time() - generation_start_time
        
        # Step 6: Save results with new filename
        self.update_state(
            state='STARTED',
            meta={
                'status': steps[5],
                'progress': f"6/{total_steps}",
                'url': url
            }
        )
        
        output_file = os.path.join(output_dir, filename)
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=4)
            
        return {
            'url': url,
            'data': result.get('data', {}),
            'errors': result.get('errors', []),
            'stats': result.get('stats', {}),
            'result_url': f"{Config.APP_URL}/{output_file}"
        }
        
    except Exception as e:
        return {
            'status': 'failed',
            'error': str(e),
            'url': url
        }
