"""
    it calls elasticsearch to search the data based on the query 
"""

from elasticsearch import Elasticsearch
import os
from sentence_transformers import SentenceTransformer
import logging


logger = logging.get_logger("Es_Con")

ES_HOST =os.environ["ES_HOST"]
ES_PORT = int(os.getenv("ES_PORT",9200))
ELASTIC_PASSWORD =os.getenv("ELASTIC_PASSWORD","admin123")
ELASTIC_USER =os.getenv("ELASTIC_USER","elastic")
RESPONSE_SIZE_FOR_FILEID=os.environ.get("RESPONSE_SIZE_FOR_FILEID",5)
DEFAULT_SIZE_UNIVERSAL=os.environ.get("DEFAULT_SIZE_UNIVERSAL",10)
SCHEME=os.environ.get("SCHEME","http")
DOCUTALK_INDEX=os.getenv("DOCUTALK_INDEX","newteamsyncfirstn") #FIXME

Emb_Model = SentenceTransformer("intfloat/multilingual-e5-small")


class ES_connector:
    
    def __init__(self) -> None:
        self.es_client = None
        self.Connect()

    def Connect(self):
        self.es = Elasticsearch([{'host': ES_HOST, 'port': ES_PORT, 'scheme':SCHEME}],basic_auth=(ELASTIC_USER, ELASTIC_PASSWORD),headers={"Content-Type":"application/json", "Accept": "application/json"})
        
        
        
    def get_domain_name(self, username):
        username = username.replace("@", "_")
        u1 = username.split('_')[1]
        domain = u1.split('.')[0]
        return domain + DOCUTALK_INDEX
        
    def get_all_files_in_folder_path(self, username, path, size=10000):
        domain_index_name = self.get_domain_name(username=username)
        response = self.es.search(
            index=domain_index_name,
            body={
                "size": size,
                "query": {
                    "bool": {
                        "must": [
                            {"term": {"username": username}},
                            {"match_phrase_prefix": {"path.text": path}}
                        ]
                    }
                },
                "collapse": {
                    "field": "fId"
                },
                "_source": ["fileName"]
            }
        )

        filenames = list({hit["_source"]["fileName"] for hit in response["hits"]["hits"] if "fileName" in hit["_source"]})
        logger.info(f"Files found: {filenames}")
        return filenames
    
#__________________________________________________________________________________
    def Search_Docs_gpt(self, query, username,path,size=DEFAULT_SIZE_UNIVERSAL):
        
        all_files_in_path = self.get_all_files_in_folder_path(username, path)

        logger.info(f"All files in the folder path : {path} : \n {all_files_in_path} \n" )

        embedding = Emb_Model.encode(query).tolist()
        logger.info(f'Embedding generated for query : {query} -- > \n EMBEDDING  : {embedding}')
        logger.info(f"Username : {username}\t path : {path}\t Index selected : {DOCUTALK_INDEX}")

        response = self.es.search(
            index=DOCUTALK_INDEX,
            body={
                "size":size,
                "query": {
                    "bool": {
                        "must": [
                            {"match": {"username": username}},# Filter by username
                            {"match_phrase_prefix": {"path.text": path}}, 
                            {
                                "bool": {
                                    "should": [
                                        {
                                    "knn": {
                                        "field": "text_embedding",
                                        "query_vector": embedding,
                                        "k": size,
                                        "num_candidates": 100  # Adjust for better results
                                    }
                                    },
                                    {
                                    "match": {
                                        "text": query  # Match exact phrase in the text field
                                    }
                                    }
                                    ]
                                }
                            }
                        ]
                    }
                },
                "_source": [
                    "text", "pageNo", "fId", "username", "fileName"
                ]  
            }
        )

        logger.info(f"Hits received :{response['hits']['hits']}")
        return response['hits']['hits']


#__________________________________________________________________________________
      
    def Data_By_FID_ES(self, f_id, query,size=RESPONSE_SIZE_FOR_FILEID):
        embedding = Emb_Model.encode(query).tolist()
        
        logger.info(f"Index selected 1: {DOCUTALK_INDEX}")
        
        response = self.es.search(
            index=DOCUTALK_INDEX,
            body={
                "size":size,
                "query": {
                    "bool": {
                        "must": [
                            {"match": {"fId": f_id}},  # Filter by fid
                            {
                                "bool": {
                                    "should": [
                                        {
                                        "knn": {
                                            "field": "text_embedding",
                                            "query_vector": embedding,
                                            "k": size,
                                            "num_candidates": 100  # Adjust for better results
                                        }
                                        },
                                        {
                                            "match": {
                                                "text": query  # Match exact phrase in the text field
                                            }
                                        }
                                    ]
                                }
                            }
                        ]
                    }
                }
            }
        )

        if response['hits']['hits']:
            return response['hits']['hits']
        

#__________________________________________________________________________________

    def Data_By_pageno(self,page_no, fid):
        logger.info(f"Index selected : {DOCUTALK_INDEX}")
        match = self.es.search(
            index=DOCUTALK_INDEX,
            body={
                "size": 15,
                "sort":[{"para":{"order":"asc"}}],
                "query": {
                    "bool": {
                        "must": [
                            {"match": {"pageNo": page_no}},
                            {"match": {"fId": fid}}
                        ]
                    }
                },
                "script_fields": {
                    "text": {
                        "script": "params['_source']['text']"
                    }
                }
            }
        )
        if match['hits']['hits']:
            details = match['hits']['hits']
            return details[0]["fields"]


    

    
