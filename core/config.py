import os
from dotenv import load_dotenv
from dataclasses import dataclass

load_dotenv()


@dataclass
class Config:
    # OpenAI
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    planner_model: str = "gpt-4o-mini"
    codegen_model: str = "gpt-4o"
    review_model: str = "gpt-4o"
    temperature: float = 0.0

    # LangSmith
    langchain_api_key: str = os.getenv("LANGCHAIN_API_KEY", "")
    langchain_project: str = os.getenv("LANGCHAIN_PROJECT", "app-builder")
    langchain_tracing: str = os.getenv("LANGCHAIN_TRACING_V2", "true")

    # App
    max_retries: int = 3
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"

    def validate(self):
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY is not set in .env")
        if not self.langchain_api_key:
            raise ValueError("LANGCHAIN_API_KEY is not set in .env")
        return self


config = Config().validate()