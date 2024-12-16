import os
import json
from celery_config import celery_app
from main import main
from generate_qa_intents import get_model
from urllib.parse import urlparse
from datetime import datetime

def get_output_filename(url, job_id):
    domain = urlparse(url).netloc.replace('www.', '') or 'local'
    return f"{domain}-{job_id}.json"

@celery_app.task(bind=True)
def process_website_task(self, url, single_page=False):
    steps = [
        "Setting up task",
        "Initializing models",
        "Fetching website content",
        "Processing content",
        "Generating Q&A pairs",
        "Saving results"
    ]
    total_steps = len(steps)
    
    try:
        # Step 1: Create directory structure
        self.update_state(
            state='STARTED',
            meta={
                'status': steps[0],
                'current': 1,
                'total': total_steps,
                'url': url
            }
        )
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create output directory
        output_dir = os.path.join('download', timestamp)
        os.makedirs(output_dir, exist_ok=True)
        
        # Create filename with domain and task ID
        filename = f"{get_output_filename(url, self.request.id)}.json"
        
        # Step 2: Initialize model
        self.update_state(
            state='STARTED',
            meta={
                'status': steps[1],
                'current': 2,
                'total': total_steps,
                'url': url
            }
        )
        model = get_model()
        
        # Step 3-5: Process using main function
        self.update_state(
            state='STARTED',
            meta={
                'status': "Processing website content",
                'current': 3,
                'total': total_steps,
                'url': url
            }
        )
        
        result = main(url, single_page)
        
        # Step 6: Save results with new filename
        self.update_state(
            state='STARTED',
            meta={
                'status': steps[5],
                'current': 6,
                'total': total_steps,
                'url': url
            }
        )
        
        output_file = os.path.join(output_dir, filename)
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=4)
            
        return {
            'status': 'completed',
            'result': result,
            'file_path': output_file,
            'url': url,
            'stats': result.get('stats', {})
        }
        
    except Exception as e:
        return {
            'status': 'failed',
            'error': str(e),
            'url': url
        }
