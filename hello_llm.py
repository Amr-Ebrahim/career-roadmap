import os
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

messages = [
    {"role": "system", "content": "You are a career advisor for junior AI engineers. Answer in 5 short bullet points."},
    {"role": "user", "content": "What skills do I need for my first AI engineer job?"},
]

response = client.chat.completions.create(
    model="openai/gpt-oss-120b",
    messages=messages,
    temperature=0.3,
    max_completion_tokens=800,
    reasoning_effort="low",
)

print(response.choices[0].message.content)
print("---")
print("Tokens used:", response.usage.total_tokens)