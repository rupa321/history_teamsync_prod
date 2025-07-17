"""
    this generates the text from provided prompt+data
"""
import requests
from requests.adapters import HTTPAdapter
import Prompt_Config
from urllib3.util.retry import Retry
import time
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator
import logging
import os

logger = logging.get_logger(__name__)

API_TOKEN_IBM = os.getenv("API_TOKEN_IBM","")
PROJECT_ID_IBM = os.getenv("PROJECT_ID_IBM","")
MODEL_ID = os.getenv("MODEL_ID","meta-llama/llama-3-2-3b-instruct") 
MAX_NEW_TOKENS = int(os.getenv("MAX_NEW_TOKENS", 8192))
#---- Deprecated -> got error : message': "Model 'meta-llama/llama-3-1-8b-instruct' is not supported",

authenticator = IAMAuthenticator(API_TOKEN_IBM)
token = None

Selected_prompt_NL = Prompt_Config.get_prompt("NLP")
logger.warning(f"Selected Prompt NL : {Selected_prompt_NL.format(query ='[query]',text='[text]')}")

Selected_prompt_EXT = Prompt_Config.get_prompt("EXT")
logger.warning(f"Selected Prompt EXT : {Selected_prompt_EXT.format(query ='[query]',text='[text]')}")


def retry_get_token(max_retries=3, backoff_factor=2):
    global token
    for attempt in range(max_retries):
        try:
            tm = authenticator.token_manager
            token = tm.get_token() 
            return "Bearer " + token
        
                     
        except requests.exceptions.RequestException as e:
            if attempt == max_retries - 1:
                raise Exception(f"Token fetch failed after {max_retries} retries: {e}")
            sleep_time = backoff_factor ** attempt
            time.sleep(sleep_time)
            
def post_with_retry(url, headers, body, max_retries=5, backoff=2):
   
    for attempt in range(max_retries):
        try:
            #logger.info("Sending request to IBM Cloud LLM API")
            response = requests.post(url, headers=headers, json=body, timeout=120)
            
            if response.status_code == 429:
                wait = backoff * (2 ** attempt)
                logger.warning(f"Rate limit hit (429). Retrying in {wait} seconds... Attempt {attempt+1}/{max_retries}")
                time.sleep(wait)
                continue  # retry this attempt
            break
        except requests.exceptions.RequestException as e:
            logger.warning(f"Request attempt {attempt+1} failed: {e}")
            if attempt == max_retries - 1:
                #logging.warning(f"Number of Retries for sending sending prompt to IBM cloud : {attempt}")
                raise
            time.sleep(backoff * (2 ** attempt))

    if response.status_code != 200:
        logger.warning(f"IBM Cloud API error {response.status_code}: {response.text}")
  
    return response
  
def ibm_cloud(prompt, prompt_type):
    logger.info(f"Starting ibm_cloud function with prompt_type: {prompt_type}")
    # logger.info(f"Input text length: {len(text)} characters")
    # logger.info(f"Query: {query}")
    
    # Prompt selection based on type
    # if prompt_type == "NLP":
    #     logger.info("Using NLP prompt template")
    #     prompt = Selected_prompt_NL.format(text=text, query=query)
    # else:
    #     logger.info("Using EXT prompt template")
    #     prompt = Selected_prompt_EXT.format(text=text, query=query)
    
    # #num_tokens_prompt = len(tokenizer.encode(prompt))
    # logger.info(f"Generated prompt length: {num_tokens_prompt} tokens")
    
    # Authentication
    sa = time.time()
    logger.info("Retrieving authentication token")
    service = retry_get_token()
    ea = time.time()
    logger.info(f"\n{'+'*200}\nSuccessfully obtained authentication token : {ea-sa} seconds where token = {service[-10:]}\n{'+'*200}\n")
    
    # API endpoint setup
    url = "https://us-south.ml.cloud.ibm.com/ml/v1/text/generation?version=2023-05-29"
    
    
    print('---------- prompt ----------', prompt)
    
    # Request body construction
    logger.info("Constructing request body with parameters")
    body = {
        "input": prompt,
        "parameters": {
            "decoding_method": "greedy",
            "max_new_tokens": MAX_NEW_TOKENS,
            "stop_sequences": ["END"],
            "repetition_penalty": 1.1
        },
        "model_id": MODEL_ID,
        "project_id": PROJECT_ID_IBM,
        "moderations": {
            "hap": {
                "input": {
                    "enabled": True,
                    "threshold": 1.0,
                    "mask": {
                        "remove_entity_value": True
                    }
                },
                "output": {
                    "enabled": True,
                    "threshold": 1.0,
                    "mask": {
                        "remove_entity_value": True
                    }
                }
            }
        }
    }
    
    logger.info(f"Request body configured with model_id: {MODEL_ID}")
    logger.info(f"Using project_id: {PROJECT_ID_IBM}")
    
    
    # Headers setup
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": service
    }
    logger.info("Request headers configured")
    
    # API call with retry mechanism
    logger.info("Initiating API call to IBM Watson ML with retry mechanism")
    
    try:
        st= time.time()
        response = post_with_retry(url=url, headers=headers, body=body)
        et = time.time()
        logger.info(f"\n{'-' * 200}\nTIME TAKEN BY CALL TO IBM CLOUD : {et-st} seconds\n{'-' * 200}")
    except Exception as e:
        logger.warning(f"API call failed with error: {str(e)}")
        return "I am unable to respond right now. Please try again later."
    
    
    try:
        data = response.json()
    except Exception as e:
        logger.warning(f"Failed to parse JSON response: {str(e)}")
        return "I am unable to respond right now. Please try again later."
    
    try:
        generated_text = data['results'][0]['generated_text']
        # num_tokens_response = len(tokenizer.encode(generated_text))
        # logger.info(f"Generated text tokens: {num_tokens_response if generated_text else 0} tokens")
    except (KeyError, IndexError) as e:
        logger.warning(f"Failed to extract generated text from response: {str(e)}")
        logger.warning(f"Response structure: {data}")
        return "I am unable to respond right now. Please try again later."
    
    # Check if content was moderated
    if not generated_text:
        logger.warning("Generated text is empty - content may have been moderated")
        
        # Extract moderation details
        logger.info("Extracting moderation details from response")
        try:
            moderation_details = data['results'][0]['moderations']['hap']
            logger.info("Successfully extracted HAP moderation details")
        except (KeyError, IndexError) as e:
            logger.warning(f"Failed to extract moderation details: {str(e)}")
            moderation_details = None
            
        
        flagged_words = []
        
        if moderation_details:
            logger.info("Processing moderation details for flagged words")
            for moderation in moderation_details:
                if 'entity' in moderation:
                    flagged_word = moderation['word']
                    flagged_words.append(flagged_word)
                    logger.info(f"Flagged word detected: {flagged_word}")
        
        # Return moderation results
        if flagged_words:
            logger.warning(f"Content moderated. Total flagged words: {len(flagged_words)}")
            result = f"Unsuitable input detected. Flagged words: {', '.join(flagged_words)}"
            logger.info(f"Returning moderation message: {result}")
            return result
        else:
            logger.warning("No specific flagged words found, but content was deemed unsuitable")
            result = "No flagged words found, but input was unsuitable."
            logger.info(f"Returning generic moderation message: {result}")
            return result
    else:
        logger.info("Generated text successfully returned without moderation issues")
        logger.info(f"Final generated text preview: {generated_text[:100]}..." if len(generated_text) > 100 else f"Final generated text: {generated_text}")
        return generated_text

