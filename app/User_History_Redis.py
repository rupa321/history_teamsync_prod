
# from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
# from langchain.memory import ConversationBufferMemory
# from langchain_community.chat_message_histories import RedisChatMessageHistory 
# import redis


# redis_url = "redis://localhost:6379"
# session_id = "user_124"
# redis_client = redis.Redis.from_url(redis_url)


def build_prompt( user_message, context):
    # prompt_history = ""
    # count=10
    # print(history.messages)
    # if not history.messages:
    #     prompt_history = "No chat history available, generate response according to the context.\n"
    # for message in history.messages:
    #     # if count == 0:
    #     #     break
    #     # count-=1
    #     # if message.type == "human":
    #     #     prompt_history += "### Question:\n" + message.content + "\n"
    #     if message.type == "ai":
    #         prompt_history += "### Response History:" + message.content + "\n"
     
    prompt = f"""
        Question asked by user: {user_message} \n
        Context from document :{context}\n
        Prompt: 
        Role: Chatbot Assisstant
        You are a chatbot assisstant which provide answer to user's question based on the context provided in short and concise manner.
        Instruction: 
        - Write response strictly on the basis of context provided and do not use your own knowledge
        - Do not assume or fabricate any details beyond the given context.  
        - Write response in 2-3 sententences in concise manner
        - Do not use prefix like Answer: or Response: or anything like that.
        - Do not use extra words or sentences, just provide the answer.
        - Do not add User's Question in the response.
        - Do not show or write context in answer and user should not be able to know from where this answer is coming from.
        - Do not use stoping keywords in the response.
    """
    
    # print("Final prompt built successfully.",prompt)
    return prompt


# def generate_response(pipe, prompt):
#     response = pipe(prompt)
#     answer = response[0]["generated_text"].replace(prompt, "").strip()
#     print("Response generated successfully.")
#     return answer

def store_chat_history(chat_history, user_message, ai_message):
    chat_history.add_user_message(user_message)
    chat_history.add_ai_message(ai_message)
    print("Chat history stored successfully.")

def print_chat_history(chat_history):
    print('Stored chat history:')
    for message in chat_history.messages:
        if message.type == "human":
            print(f"User: {message.content}")
        elif message.type == "ai":
            print(f"AI: {message.content}")

# def main():
#     print("-----------------------------------")
#     session_id = "user_124"
#     chat_history = RedisChatMessageHistory(url=redis_url, session_id=session_id)
#     # memory = ConversationBufferMemory(chat_memory=chat_history, return_messages=True)
#     model_id = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
#     user_message = "when was apple founded?"
#     context = """[The apple is one of the most popular and widely consumed fruits globally. 
#             Known for its crisp texture, sweet-tart flavor, and health benefits, apples have been cultivated for thousands of years.
#             They belong to the species Malus domestica and are part of the Rosaceae family.],
#             [Apple Inc., founded by Steve Jobs, Steve Wozniak, and Ronald Wayne, is renowned for revolutionizing the smartphone industry with its iconic iPhone series. 
#             Introduced in 2007, the iPhone changed the way people interact with technology, combining a phone, an iPod, and an internet communicator into a single, 
#             sleek device.],
#             [Since the release of the first iPhone in 2007, Apple has launched numerous models, each featuring significant advancements in design, hardware, and software. 
#             The evolution of iPhones reflects Apple’s continuous commitment to innovation, privacy, and user experience.] """
#     final_prompt = build_prompt(chat_history, user_message, context)
#     print("Final prompt:", final_prompt)
    
#     answer = generate_response(final_prompt)
#     store_chat_history(chat_history, user_message, answer)
#     print(f"AI: {answer}")
#     # print_chat_history(chat_history)
#     print('-----------------------------------')
#     return 0

# if __name__ == "__main__":
#     main()