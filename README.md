#  AiAssistant

AI assistant in "chat" and "text modes, includes Token Counting, Context Window Usage, RPM &amp; RPD &amp; TPM Limits and API Request handling.
"Chat" mode remembers the conversation history, however "Text" mode can not.

### --------**** Samples and Test Cases are shown at the end of the page. ****--------

## Importing Libraries
```ruby
import google.generativeai as genai 
import requests
import json 
import time # to handle 2 RPM Usage case
import google.api_core.exceptions # to catch API error sent by google
```
## API Key, Choosen Model and System Instruction
```ruby
api_key = ""  # Users own API key 
genai.configure(api_key=api_key)

# Model
chosen_model = "gemini-1.5-pro"
system_instruction = "You are helpful assistant."
model = genai.GenerativeModel(chosen_model, system_instruction=system_instruction)
```
## Rate Limit Settings

* (RPM) Requests per minute

* (RPD) Requests per day

* (TPM) Tokens per minute


![image](https://github.com/user-attachments/assets/fbaed3a6-0ded-4ce8-ad0d-39b9e837a98f)
```ruby
# Rate limit settings
MAX_RETRIES = 3  # Maximum number of retries
BASE_DELAY = 1    # Initial delay (seconds)
MAX_CONTEXT_TOKENS = 8192 # Model can handle 1 million tokens, but in our code we've decreased to 8k.
WARNING_THRESHOLD = 0.8 # Triggers a warning when 80% of MAX_CONTEXT_TOKENS is reached.
RPM_LIMIT = 2  # Maximum requests per minute
RPD_LIMIT = 50  # Maximum requests per day
TPM_LIMIT = 32000  # Maximum tokens per minute

# API usage counters
request_count_per_minute = 0
request_count_per_day = 0
token_count_per_minute = 0
last_request_time = time.time() #Records the time of the last request
```
## Handling the rate limits

1-) Resets counters every minute.

2-) Blocks requests if the daily limit is exceeded.

3-) Pauses execution if the per-minute limit is exceeded, waiting until the next window.

```ruby
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
        print("⛔ Daily API request limit exceeded!")
        return False
    if request_count_per_minute >= RPM_LIMIT:
        print("⚠️ Minute API request limit exceeded, waiting...")
        time.sleep(60 - elapsed_time)
        request_count_per_minute = 0
        token_count_per_minute = 0
        last_request_time = time.time()
    return True
```
## Send API Requests with Retry Mechanism

1-) Checks the rate limit before making a request.

2-) Handles both "text" and "chat" modes:

Text Mode: Calls model.generate_content(prompt).

Chat Mode: Sends messages using chat_session.send_message(prompt, stream=True).

3-) Handles errors and retries up to MAX_RETRIES times if an issue occurs.

4-) Updates API usage counters after a successful request.
```ruby
def send_request_with_retry(prompt, chat_session=None):
    global request_count_per_minute, request_count_per_day, token_count_per_minute
    retries = 0
    while retries < MAX_RETRIES:
        if not check_rate_limits():
            return None
        try:
            if mode == "text":
                response = model.generate_content(prompt)
                response_text = response.text
            else:
                response = chat_session.send_message(prompt, stream=True)
                response_text = "".join(chunk.text for chunk in response)

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
        except requests.exceptions.RequestException as e:
            print(f"Error: {e}")
            retries += 1
        except json.JSONDecodeError:
            print("JSON response error!")
            retries += 1
        except google.api_core.exceptions.TooManyRequests:
            print("⚠️ Too Many Request API limit. Please try again later.")
            return None

```

## User Mode Selection
Prompts the user to choose between "chat" and "text" modes.

Ensures valid input before proceeding.

Text Mode: Generates a response for each prompt.

Chat Mode: Maintains context-aware conversation.

✔ Implements rate limiting to avoid exceeding API usage limits.

✔ Includes error handling and retry mechanisms for request failures.

✔ Allows the user to interact with the model until they exit manually.

```ruby
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
```

# Samples and Test Cases

*  ("Chat" Mode: Remembers chat history)
 ![image](https://github.com/user-attachments/assets/e4340f4d-5e3f-4123-988a-d030e6a2660f)

* ("Text" Mode: Can't access chat history)
  ![image](https://github.com/user-attachments/assets/e0f4dece-25ea-4089-8da2-af42da5487c9)
* (Rate Limit Test: 2 RPM Usage)
![image](https://github.com/user-attachments/assets/d017e712-4e96-43d3-8710-894efa9ebb98)
* (Rate Limit Test: 50 RPD Usage)
![image](https://github.com/user-attachments/assets/1f99300e-db5d-4744-822b-08874996ddc6)
* (Code: 429 Too Many Requests API Error handling)
![image](https://github.com/user-attachments/assets/00290891-c726-4142-bee6-1e516682e4e9)





