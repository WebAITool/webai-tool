from openai import OpenAI

from llm_config import (
    API_KEY,
    LLM_API_BASE_URL,
    LLM_MODEL,
)


def generate(prompt):
    # api_key = "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"
    client = OpenAI(
        # base_url="https://openrouter.ai/api/v1",
        base_url=LLM_API_BASE_URL,
        api_key=API_KEY,
    )


    completion = client.chat.completions.create(
        # model="deepseek/deepseek-chat-v3.1:free",
        # model="x-ai/grok-4-fast:free",
        # model="openai/gpt-oss-20b:free",
        # model="meituan/longcat-flash-chat:free",
        # model="deepseek/deepseek-chat-v3.1",
        # model = "deepseek/deepseek-v3.1-terminus",
        model=LLM_MODEL,
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
