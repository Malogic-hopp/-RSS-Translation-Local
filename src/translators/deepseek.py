import os
from openai import OpenAI
from .base import BaseTranslator

class DeepSeekTranslator(BaseTranslator):
    def __init__(self, api_key, source_lang="auto", target_lang="zh"):
        super().__init__(source_lang, target_lang)
        self.api_key = api_key
        try:
            self.client = OpenAI(
                api_key=self.api_key,
                base_url="https://api.deepseek.com"
            )
        except Exception as e:
            print(f"Error initializing DeepSeek Client: {e}")
            self.client = None

    def translate(self, content):
        if not content or not self.client:
            return content

        try:
            # Construct system prompt based on languages
            source_desc = "the original language" if self.source_lang == "auto" else self.source_lang
            target_desc = "Simplified Chinese" if self.target_lang in ["zh", "zh-cn"] else self.target_lang
            
            system_prompt = (
                f"You are a professional translator. Translate the following text from {source_desc} to {target_desc}. "
                "Maintain the original formatting. Do not output any explanation, just the translated text."
            )

            response = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": content},
                ],
                stream=False
            )
            
            return response.choices[0].message.content

        except Exception as e:
            print(f" [DeepSeek Translation Error: {e}]")
            return None
