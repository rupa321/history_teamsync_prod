import os
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator
import requests
import time
import logging
import Prompt_Config

logger = logging.getLogger(__name__)



API_TOKEN_IBM = os.getenv("API_TOKEN_IBM","")
PROJECT_ID_IBM = os.getenv("PROJECT_ID_IBM","")
MODEL_ID = os.getenv("MODEL_ID","meta-llama/llama-3-3-70b-instruct") 
MAX_NEW_TOKENS = int(os.getenv("MAX_NEW_TOKENS", 4192))

authenticator = IAMAuthenticator(API_TOKEN_IBM)
token = None

Selected_prompt_NL = Prompt_Config.get_prompt("NLP")
# if Selected_prompt_NL is not None:
#     logger.warning(f"Selected Prompt NL : {Selected_prompt_NL.format(query='[query]', text='[text]')}")
# else:
#     logger.warning("Selected Prompt NL : None (prompt not found)")

Selected_prompt_EXT = Prompt_Config.get_prompt("EXT")
# if Selected_prompt_EXT is not None:
#     logger.warning(f"Selected Prompt EXT : {Selected_prompt_EXT.format(query='[query]', text='[text]')}")
# else:
#     logger.warning("Selected Prompt EXT : None (prompt not found)")


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
                time.sleep(wait)
                continue  # retry this attempt
            break
        except requests.exceptions.RequestException as e:
            if attempt == max_retries - 1:
                #logging.warning(f"Number of Retries for sending sending prompt to IBM cloud : {attempt}")
                raise
            time.sleep(backoff * (2 ** attempt))

    
    return response
  
def select_context (question, history, contexts):
 

    # Prompt selection based on type
    prompt=f"""
       Question: {question}
        Chat History: {history} 
        Contexts: {contexts} 
        Prompt: 
        - Select all relevant contexts out of these contexts list that is most relevant according to Question asked by user and User's chat history.
        - Write response strictly based on given instructions.

        Instruction:
        - Do not show the entire context list and response, just show the selected context.
        - Do not add any Note in response.
        - Select the context not only based on its heading but also consider its content while selection.
        - If there is no Chat history then select on basis of question asked by user, and give that context as a response in text.
        - If the Chat history does not match with question aksked, then select context on basis of question asked by user.
        - Each context is seperated by '-------------------------' and strictly consider this as sepearator between contexts.
        - Do not add or fabricate question asked by user.
        - Do not convert response in HTML format.
        - Select context strictly on basis of history or question provided and do not use your own knowledge.
        """
    
    # Authentication
    service = retry_get_token()
    
    # API endpoint setup
    url = "https://us-south.ml.cloud.ibm.com/ml/v1/text/generation?version=2023-05-29"
    
    
    # print('---------- prompt ----------', prompt)
    
    # Request body construction
    body = {
        "input": prompt,
        "parameters": {
            "decoding_method": "greedy",
            "max_new_tokens": 500,
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
    
    
    
    # Headers setup
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": service
    }
    
    # API call with retry mechanism
    
    try:
        
        response = post_with_retry(url=url, headers=headers, body=body)
        
    except Exception as e:
        return "I am unable to respond right now. Please try again later. response"
    
    
    try:
        data = response.json()
    except Exception as e:
        return "I am unable to respond right now. Please try again later. data"
    # print(data)
    try:
        generated_text = data['results'][0]['generated_text']
    except (KeyError, IndexError) as e:
        return "I am unable to respond right now. Please try again later. generated_text"
    
    return generated_text

def generate_response (query,text,prompt_type):
    
    
    logger.info(f"Starting ibm_cloud function with prompt_type: {prompt_type}")
    logger.info(f"Input text length: {len(text)} characters")
    logger.info(f"Query: {query}")
    
    # Prompt selection based on type
    if prompt_type == "NLP":
        logger.info("Using NLP prompt template")
        if Selected_prompt_NL is not None:
            prompt = Selected_prompt_NL.format(text=text, query=query)
        else:
            logger.warning("Selected_prompt_NL is None. Cannot format prompt.")
            return "Prompt template for NLP not found."
    else:
        logger.info("Using EXT prompt template")
        if Selected_prompt_EXT is not None:
            prompt = Selected_prompt_EXT.format(text=text, query=query)
        else:
            logger.warning("Selected_prompt_EXT is None. Cannot format prompt.")
            return "Prompt template for EXT not found."
    
    # #num_tokens_prompt = len(tokenizer.encode(prompt))
    # logger.info(f"Generated prompt length: {num_tokens_prompt} tokens")
    
    # Authentication
    sa = time.time()
    logger.info("Retrieving authentication token")
    service = retry_get_token()
    ea = time.time()
    if service is not None:
        logger.info(f"\n{'+'*200}\nSuccessfully obtained authentication token : {ea-sa} seconds where token = {service[-10:]}\n{'+'*200}\n")
    else:
        logger.warning(f"\n{'+'*200}\nFailed to obtain authentication token : {ea-sa} seconds\n{'+'*200}\n")
    
    # API endpoint setup
    url = "https://us-south.ml.cloud.ibm.com/ml/v1/text/generation?version=2023-05-29"
    
    
    # print('---------- prompt ----------', prompt)
    
    # Request body construction
    body = {
        "input": prompt,
        "parameters": {
            "decoding_method": "greedy",
            "max_new_tokens": 100,
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
    
    
    
    # Headers setup
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": service
    }
    
    # API call with retry mechanism
    
    try:
        
        response = post_with_retry(url=url, headers=headers, body=body)
        # print(response.json())
        
    except Exception as e:
        return "I am unable to respond right now. Please try again later."
    
    
    try:
        data = response.json()
    except Exception as e:
        return "I am unable to respond right now. Please try again later."
    
    try:
        generated_text = data['results'][0]['generated_text']
    except (KeyError, IndexError) as e:
        return "I am unable to respond right now. Please try again later."
    
    return generated_text
    
# if __name__ == "__main__":
#     question = "What is apple?"
#     history = "I like Apple mobile phones."
#     contexts = [
#         "Apple Fruit: An Overview The apple is one of the most popular and widely consumed fruits globally.",
#         "Apple Mobile Phones: An Overview Apple Inc., founded by Steve Jobs, Steve Wozniak, and Ronald Wayne, is renowned for revolutionizing the smartphone industry with its iconic iPhone series."
#     ]
    
#     response = select_context(question, history, contexts)
#     prompt = f"""
#         Question asked by user: {question} \n
#         Context from document :{response}\n
#         Prompt: 
#         Role: Chatbot assistant.
#         You are a chatbot assistant which provide answer to user's question based on the context in concise manner.
#         Provide answer to the user's question according to the context provided from document.
#         Do not use prefix like Answer: or Response: or anything like that.
#         Do not use extra words, just provide the answer."""
    
#     answer=generate_response(prompt)
#     # print("Generated Response:", answer)
