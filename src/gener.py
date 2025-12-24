from openai import OpenAI
import dotenv
import os

dotenv.load_dotenv()
api_key = os.getenv('API_KEY')


def generate(prompt):
    # api_key = "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"
    client = OpenAI(
        # base_url="https://openrouter.ai/api/v1",
        base_url="https://api.polza.ai/api/v1",
        api_key=api_key,
    )


    completion = client.chat.completions.create(
        # model="deepseek/deepseek-chat-v3.1:free",
        # model="x-ai/grok-4-fast:free",
        # model="openai/gpt-oss-20b:free",
        # model="meituan/longcat-flash-chat:free",
        # model="deepseek/deepseek-chat-v3.1",
        # model = "deepseek/deepseek-v3.1-terminus",
        model = "qwen/qwen3-coder",
        # model = "minimax/minimax-m2:free",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )
    return completion.choices[0].message.content


if __name__ == '__main__':
    print(generate('how many wheels has car'))



from smolagents.models import LiteLLMModel

model = LiteLLMModel(
    model="openai/qwen/qwen3-235b-a22b-2507",   
    api_base="https://api.polza.ai/api/v1",
    api_key=api_key,
    temperature=0.1,
    write_file_allowed=True
)