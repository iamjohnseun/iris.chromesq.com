import torch
import gc
import re
from transformers import pipeline
from config import Config
from urllib.parse import urlparse

_paraphrase_model = None

def get_paraphrase_model():
    global _paraphrase_model
    if _paraphrase_model is None:
        _paraphrase_model = pipeline('text2text-generation', model='t5-base', device='cpu')
    return _paraphrase_model

def load_models():
    try:
        question_generator = pipeline('text2text-generation', model='t5-small', device='cpu', batch_size=1)
        topic_generator = pipeline('text2text-generation', model='t5-small', device='cpu', batch_size=1)
        intent_classifier = pipeline('text-classification', model='distilbert-base-uncased', device='cpu', batch_size=1)
        return question_generator, intent_classifier, topic_generator
    except Exception as e:
        raise RuntimeError(f"Failed to load models: {str(e)}")

question_generator, intent_classifier, topic_generator = load_models()

def clean_text(text):
    # Remove extra whitespace and special characters
    text = re.sub(r'\s+', ' ', text)  # Replace multiple spaces with single space
    text = re.sub(r'[^\w\s.,!?$€£¥%@#&*()\-]', '', text)  # Keep alphanumeric, common punctuation and symbols
    text = re.sub(r'\s+([.,!?])', r'\1', text)  # Remove spaces before punctuation
    text = re.sub(r'([.,!?])\s+', r'\1 ', text)  # Ensure single space after punctuation
    text = text.replace('..', '.').replace(',,', ',')  # Remove duplicate punctuation
    return text.strip()

def generate_intent_name(text, url):
    # Extract page name from URL
    path = urlparse(url).path.strip('/')
    page_context = path.split('/')[-1] if path else 'content'
    
    # Generate topic for the text
    topic_prompt = f"Generate a single word topic for: {text}"
    topic = topic_generator(topic_prompt, max_length=10, num_return_sequences=1)[0]['generated_text']
    
    # Generate descriptive subject
    subject_prompt = f"Generate a single word description for: {text}"
    subject = topic_generator(subject_prompt, max_length=20, num_return_sequences=1)[0]['generated_text']
    
    # Clean and format the intent name
    topic = topic.lower().strip().replace(' ', '_')
    subject = subject.lower().strip().replace(' ', '_')
    
    intent_name = f"{page_context}.{topic}.{subject}"
        
    return intent_name

def generate_utterances(question, num_variations=3):
    model = get_paraphrase_model()
    
    # Ensure question ends with question mark
    question = question.strip()
    if not question.endswith('?'):
        question += '?'

    question = clean_text(question)
    
    # Generate question variations
    prompt = f"Generate different ways to ask: {question}"
    variations = model(
        prompt,
        max_length=Config.MAX_QUESTION_LENGTH,
        num_return_sequences=num_variations,
        temperature=0.7
    )
    
    utterances = []
    for var in variations:
        text = clean_text(var['generated_text'])
        if text.endswith('?') and len(text.split()) >= 3:
            utterances.append(text)
    
    return utterances

def summarize_answer(text):
    summary_prompt = f"Being direct and concise, summarize: {text}"
    summary = topic_generator(summary_prompt, max_length=Config.MAX_SENTENCES, num_return_sequences=1)[0]['generated_text']
    return clean_text(summary)

def generate_questions_and_intents(sentences, url, batch_size=Config.MAX_BATCH_SIZE):
    sentences = sentences[:Config.MAX_SENTENCES]
    qa_pairs = []
    
    torch.set_num_threads(Config.TORCH_THREADS)
    gc.collect()
    torch.cuda.empty_cache() if torch.cuda.is_available() else None
    
    # Process sentences in batches
    for i in range(0, len(sentences), batch_size):
        batch = sentences[i:i + batch_size]
        batch_qa_pairs = []
        
        for sentence in batch:
            if len(sentence.split()) >= Config.MIN_WORDS_PER_ELEMENT:
                # Generate concise answer
                answer = summarize_answer(sentence)
                
                # Generate natural question
                question_prompt = f"Generate a clear and concise question that would be answered by: {answer}"
                question = question_generator(question_prompt, max_length=Config.MAX_QUESTION_LENGTH)[0]['generated_text']
                question = clean_text(question)
                
                # Generate intent name
                intent_name = generate_intent_name(answer, url)
                
                batch_qa_pairs.append({
                    "question": question,
                    "answer": answer,
                    "intent": intent_name
                })
        
        qa_pairs.extend(batch_qa_pairs)
        
        # Resource management after each batch
        if i + batch_size < len(sentences):
            gc.collect()
            torch.cuda.empty_cache() if torch.cuda.is_available() else None
    
    return qa_pairs

# USAGE
# sentences = ["Your extracted sentences here..."]
# qa_pairs = generate_questions_and_intents(sentences)
# print(qa_pairs)