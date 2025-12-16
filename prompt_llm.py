import configparser
import requests
import json

def get_openrouter_key():
    """
    Helper function to retrieve the OpenRouter API key from a config file.
    """
    
    config = configparser.ConfigParser()
    config.read('config.ini')
    openrouter_api_key = config.get('API', 'OPENROUTER_API_KEY')

    return openrouter_api_key

def call_deepseek_model(message: str):

    message = f"""
        You are a helpful assistant. Answer the question **only using the context provided**.

        Return a **single, unformatted answer** with:
        - no quotes
        - no markdown
        - no curly braces
        - no formatting
        - no extra words

        Just return the raw answer text — nothing else.

        Question: {message}
    """
    
    response = requests.post(
        url="https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {get_openrouter_key()}",
            "Content-Type": "application/json"
        },
        data=json.dumps({
            "model": "deepseek/deepseek-chat-v3-0324:free",
            "messages": [
            {
                "role": "user",
                "content": message
            }
            ],
            
        })
    )

    return response.json().get('choices')[0].get('message').get('content')