"""
    this is the main file 
    - api hits here
"""


from fastapi import FastAPI,HTTPException
import uvicorn
import os
import time
import Doc_Process
import logging

SERVICE_PORT = int(os.getenv("SERVICE_PORT",8989))
GATEWAY_TIME = os.getenv("GATEWAY_TIME",0)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

app = FastAPI()
logger = logging.getLogger(__name__)


@app.post("/teamsync/nlp/docutalk/search_documents")
async def search_documents(query,username,modeltype,answerType,path='T_'):
    
    logger.info(f"{'+'*100} \n BACKEND_FOLDER_PATH : {path} \n {'+'*100}")
    path="T"+path.replace("/","_") if not path.startswith("T_") else path
    username=username.replace("@","_")
    logger.info(f"{'+'*100} \n CHANGED_FOLDER_PATH : {path} \n USERNAME : {username} \n MODELTYPE : {modeltype} \n ANSWERTYPE : {answerType} \n {'+'*100}")

    if not query:
        logger.error(f"Query parameter 'query' is required.")
        raise HTTPException(status_code=400, detail="Query parameter 'query' is required.")
    
    else :
        result = Doc_Process.search_documents_gpt(query,username,modeltype,answerType,path)

    logger.info(f"{'+'*25} Universal DONE {'+'*25} \n\n")

    if GATEWAY_TIME:
        time.sleep(int(GATEWAY_TIME))
    return result


@app.post("/teamsync/nlp/docutalk/search_by_fid")
async def search_by_fid(fid,query,modeltype,session_id ):
    logger.info(f"----inside search_by_fid-----")

    if not fid:
        logger.error("===== File id required =====")
        raise HTTPException(status_code=400, detail="File id required")
    else :
        result = Doc_Process.Data_By_FID(fid,query,modeltype,session_id)
        logger.info(f"{'+'*25} Fid Docutalk DONE {'+'*25} \n\n")

    if GATEWAY_TIME:
        time.sleep(int(GATEWAY_TIME))
    return result


if __name__ == '__main__':
    uvicorn.run("Main:app", host="0.0.0.0", port=SERVICE_PORT)