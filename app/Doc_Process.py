"""
    this is the augmentation layer 
    - this is the service layer that calls the ES_Con for document search and model_call for text generation
"""
import Es_Con
import logging
import Model_Call as call
from Model_IBM import select_context
from User_History_Redis import build_prompt,store_chat_history
from langchain_community.chat_message_histories import RedisChatMessageHistory 
import os

REDIS_URL=os.getenv("REDIS_URL","")
ES = Es_Con.ES_connector()


def search_documents_gpt(query_text, user_name, model_type, answerType, path):

    logging.info(f" File with path {path} are being searched by user {user_name}")
    hits = ES.Search_Docs_gpt(query_text, user_name, path)
    filelist = []
    search_results = []
    #lst = []
    logging.warning(f"__inside search_documents_gpt of universal docutalk__\n QUERY  :   {query_text} -------------")
    if answerType not in ["singleDocument", "multiDocument"]:
        logging.warning(f"Unsupported answer type : {answerType}")
        return [{"text": f"Unsupported answer type: {answerType}. Supported types: ['singleDocument', 'multiDocument']"}]

    if model_type not in ["NLP", "EXT"]:
        logging.warning(f"Unsupported responses type : {model_type}")
        return [{"text": f"Unsupported responses type: {model_type}. Supported types: ['NLP', 'EXT']"}]

    if not hits:
        logging.warning(f"No documents found -->")
        return [{"text": "No documents found for the query."}]

    file_id = hits[0]["_source"].get("fId", "")
    page_no = hits[0]["_source"].get("pageNo", "")
    text = hits[0]["_source"].get("text", "")
    combined_text_single_doc = "Context:" + above_and_below_pagedata(text, int(page_no), file_id)
    combined_text_multi_doc = ""
    i=0
    max_score = hits[0]["_score"]
    threshold = 0.5*max_score
    for hit in hits:
        score = hit["_score"]
        if score >= threshold:
            filename = hit["_source"].get("fileName", "")
            
            file_id = hit["_source"].get("fId", "")
            text = hit["_source"].get("text", "")
            page_no = hit["_source"].get("pageNo", "")
            context += f"Context {i+1}: {text}"
            combined_text_multi_doc += f"{context}"+  "\n-------------------------\n"
            i+=1
            if filename not in filelist:
            
                filelist.append(filename)
              
                search_results.append({"filename": filename, "fId": file_id, "page_no": page_no, "score": score})
        
    chat_history = RedisChatMessageHistory(url=REDIS_URL, session_id=user_name, ttl= 400)
    history= chat_history.messages
    history_chat=''
    if history :
        for message in history:
            if message.type == "ai":
                history_chat += "### Its Response:" + message.content + "\n"
            elif message.type == "human":
                history_chat += "### Previous Question asked by user:"+message.content+"\n"
    
    if not search_results:
        logging.warning(f"Search Results --> []")
        return [{"text": "I am unable to provide an answer based on the information I have."}]

    if answerType == "singleDocument":
        # if model_type == "mistral":
        selected_context= select_context(query_text,history_chat,combined_text_single_doc)
        prompt =build_prompt(query_text,selected_context)
        model_answer = call.ibm_cloud(prompt, model_type)
        store_chat_history(chat_history, query_text, model_answer)

        # elif model_type == "phi3":  # Gemini
        #     model_answer = using_gemini(combined_text_single_doc, query_text)

    elif answerType == "multiDocument":
        # if model_type == "mistral":
        selected_context = select_context(query_text,history_chat,combined_text_multi_doc)
        prompt = build_prompt(query_text,selected_context)
        model_answer = call.ibm_cloud(prompt, model_type)
        store_chat_history(chat_history, query_text, model_answer)
        # elif model_type == "phi3":  # Gemini
        #     model_answer = using_gemini(combined_text_multi_doc, query_text)

    search_results.insert(0, {"text": model_answer})
    logging.warning(f"search_results :: {search_results}")
    return search_results



def above_and_below_pagedata(text, page_no, file_id):
    
    """So this code basically give the full context :
     now text will be =  whole previous page + whole page of chunk +whole next page,
     
     It help to get the whole context of the chunk """
    
    #gets whole text from current page (of the chunk)
    text = ES.Data_By_pageno(page_no_below, file_id)
    #gets text from next page
    page_no_below = page_no + 1
    below_page_text = ES.Data_By_pageno(page_no_below, file_id)

    if below_page_text is not None:
        below_page_text = below_page_text['text'][0]
    else:
        below_page_text = ''

    #gets text from previous page
    if (page_no != 1):
        page_no_above = page_no - 1
        above_page_text = ES.Data_By_pageno(page_no_above, file_id)

        if above_page_text is not None:
            above_page_text = above_page_text['text'][0]
        else:
            above_page_text = ''
        return above_page_text + text + below_page_text # if chunk is not from the first page

    else:
        page_no_above = page_no + 2
        below_page_text_2 = ES.Data_By_pageno(page_no_above, file_id)

        if below_page_text_2 is not None:
            below_page_text_2 = below_page_text_2['text'][0]
        else:
            below_page_text_2 = ''
        return text + below_page_text + below_page_text_2 # if chunk is from the first page


  
    
def Data_By_FID_1(fid, query, model_type):# ES_Con.Default_size == 1

    session_id='uuuu' #get session id from frontend
    logging.warning(f"__inside Data_By_FID_1 of fileid docutalk__\n QUERY  :   {query} -------------")
    if model_type not in ["NLP", "EXT"]:
        outres = f"responses type not match :: {model_type}, responses :: ['NLP', 'EXT']"
        logging.warning(f"{outres}")
        return outres
    chat_history = RedisChatMessageHistory(url=REDIS_URL, session_id=session_id, ttl= 400)
    history= chat_history.messages
    history_chat=''
    if history :
        for message in history:
            if message.type == "ai":
                history_chat += "### Its Response:" + message.content + "\n"
            elif message.type == "human":
                history_chat += "### Previous Question asked by user:"+message.content+"\n"
    
    hits = ES.Data_By_FID_ES(fid, query)
    try:
        text = hits[0]["_source"].get("text", "")
        logging.warning(f"-----retrieved text----- \n{text}")
    except Exception as e:
        logging.warning(f"No hits from database2 --> {e}")
        return [{"text": "No hits from database"}]

    page_no = hits[0]["_source"].get("pageNo", "")
    combined_text = "Context:" + above_and_below_pagedata(text, int(page_no), fid)
    selected_context= select_context(query,history_chat,combined_text)
    # prompt =build_prompt(query,selected_context)
    model_answer = call.ibm_cloud(query,selected_context, model_type)
    store_chat_history(chat_history, query, model_answer)
    logging.warning(f"model_answer --> {model_answer}")
    return [{"text": model_answer}]

def Data_By_FID_More(fid, query, model_type): # ES_Con.Default_size != 1
    session_id='uuuu' #get session id from frontend
    logging.warning(f"__inside Data_By_FID_More of fileid docutalk__\n QUERY  :   {query} -------------")
    if model_type not in ["NLP", "EXT"]:
        outres = f"responses type not match :: {model_type}, responses :: ['NLP', 'EXT']"
        logging.warning(f"{outres}")
        return outres
    
    chat_history = RedisChatMessageHistory(url=REDIS_URL, session_id=session_id, ttl= 400)
    history= chat_history.messages
    history_chat=''
    if history :
        for message in history:
            if message.type == "ai":
                history_chat += "### Its Response:" + message.content + "\n"
            elif message.type == "human":
                history_chat += "### Previous Question asked by user:"+message.content+"\n"
    hits = ES.Data_By_FID_ES(fid, query)
    combined_text = ""
    j=0
    if hits:
        for i in hits:
            try:
                text = i["_source"].get("text","")
                if text:
                    context += f"Context {j+1}: {text}"
                    combined_text_multi_doc += f"{context}"+  "\n-------------------------\n"
                    j+=1
            except Exception as e:
                logging.warning(f"Error from elstic data --> ")

        if not combined_text:
            logging.warning(f"No hits from database --> {e} ")
            return [{"text": "No hits from database"}]
        logging.warning(f"------- combined text from Data_By_FID_MORE --------\n {combined_text}")
        selected_context= select_context(query,history_chat,combined_text)
        # prompt =build_prompt(query,selected_context)
        model_answer = call.ibm_cloud(query,selected_context, model_type)
        store_chat_history(chat_history, query, model_answer)
        logging.warning(f"model_answer --> {model_answer}")
        return [{"text": model_answer}] 
    else:
        return [{"text":"No hits from database---"}]

if Es_Con.RESPONSE_SIZE_FOR_FILEID != 1:
    Data_By_FID = Data_By_FID_More
else:
    Data_By_FID = Data_By_FID_1




