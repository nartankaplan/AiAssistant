import google.generativeai as genai
import requests
import json
import time
import google.api_core.exceptions
 
 
api_key = " "
genai.configure(api_key=api_key)
 

chosen_model = "gemini-1.5-pro"
system_instruction = "You are helpful assistant"
model = genai.GenerativeModel(chosen_model, system_instruction=system_instruction)
 
# Rate limit settings
MAX_RETRIES = 3  # Maximum number of retries
BASE_DELAY = 1    # Initial delay (seconds)
MAX_CONTEXT_TOKENS = 8192
WARNING_THRESHOLD = 0.8
RPM_LIMIT = 2  # Maximum requests per minute
RPD_LIMIT = 50  # Maximum requests per day
TPM_LIMIT = 32000  # Maximum tokens per minute
 
# API usage counters
request_count_per_minute = 0
request_count_per_day = 0
token_count_per_minute = 0
last_request_time = time.time()
 
 
# Rate limit check function
def check_rate_limits():
    global request_count_per_minute, request_count_per_day, token_count_per_minute, last_request_time
    current_time = time.time()
    elapsed_time = current_time - last_request_time
    if elapsed_time >= 60:
        request_count_per_minute = 0
        token_count_per_minute = 0
        last_request_time = current_time
    if request_count_per_day >= RPD_LIMIT:
        print("⛔ You have exceeded the daily API request limit. Please try again later.")
        return False
    if request_count_per_minute >= RPM_LIMIT:
        print("⚠️ Minute API request limit exceeded, waiting...")
        time.sleep(60 - elapsed_time)
        request_count_per_minute = 0
        token_count_per_minute = 0
        last_request_time = time.time()
    return True
 
# Function to send an API request with retry mechanism
def send_request_with_retry(prompt, chat_session=None):
    global request_count_per_minute, request_count_per_day, token_count_per_minute
    retries = 0
    while retries < MAX_RETRIES:
        if not check_rate_limits():
            print("⚠️ You have exceeded the daily API request limit. Please try again later.")
            return None  # Return an error message to the user
        try:
            if mode == "text":
                response = model.generate_content(prompt)
                if not response or not response.text:
                    raise ValueError("Received an empty response from the model.")
                response_text = response.text
            else:
                response = chat_session.send_message(prompt, stream=False)  # Receive response directly
                if not response or not response.parts:
                    raise ValueError("Chat response is empty or invalid.")
                response_text = response.parts[0].text  # Get the first part
 
            print(f"Response: {response_text}\n")
 
            usage_data = response.usage_metadata
            total_tokens_used = usage_data.total_token_count
            request_count_per_minute += 1
            request_count_per_day += 1
            token_count_per_minute += total_tokens_used
 
            system_instruction_tokens = model.count_tokens(system_instruction).total_tokens
            context_window_tokens = system_instruction_tokens + total_tokens_used
 
            print(f"➡️ Context Window Usage: {context_window_tokens} / {MAX_CONTEXT_TOKENS} tokens")
            if context_window_tokens > MAX_CONTEXT_TOKENS * WARNING_THRESHOLD:
                print(f"⚠️ Warning: Context window token count is {context_window_tokens}, approaching {WARNING_THRESHOLD * 100}% of the limit!")
 
            print("➡️ Rate Limit Usage:")
            print(f"    - Requests per Minute: {request_count_per_minute} / {RPM_LIMIT}")
            print(f"    - Requests per Day: {request_count_per_day} / {RPD_LIMIT}")
            print(f"    - Tokens per Minute: {token_count_per_minute} / {TPM_LIMIT}")
 
            return response_text
 
        except (requests.exceptions.RequestException, json.JSONDecodeError, google.api_core.exceptions.TooManyRequests, ValueError, IndexError) as e:
            retries += 1
            print(f"⚠️ Error ({retries}/{MAX_RETRIES}): {e}")
            time.sleep(BASE_DELAY * retries)
            if retries == MAX_RETRIES:
                print("❌ Maximum retries reached. Please try again later.")
                return None
 
# User mode selection
mode = input("Select mode (chat/text): ").strip().lower()
while mode not in ["chat", "text"]:
    print("Invalid input! Please enter 'chat' or 'text'.")
    mode = input("Select mode (chat/text): ").strip().lower()
 
# Start chat session
chat_session = model.start_chat() if mode == "chat" else None
 
# Continue until the user exits
while True:
    user_prompt = input("Enter your question (Press 'q' to exit): ")
    if user_prompt.lower() == "q":
        print("Exiting...")
        break
    send_request_with_retry(user_prompt, chat_session)