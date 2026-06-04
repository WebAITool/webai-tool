import sys
from pathlib import Path

from openai import OpenAI

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
from llm_config import load_llm_config, validate_llm_config  # noqa: E402


def generate(prompt):
    config = load_llm_config()
    validate_llm_config(config)
    client = OpenAI(
        base_url=config.api_base_url,
        api_key=config.api_key,
    )


    completion = client.chat.completions.create(
        model=config.model,
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
