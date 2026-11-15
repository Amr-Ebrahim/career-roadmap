# groq_judge.py - lets DeepEval use Groq (free) as its judge model
import json
import os

from dotenv import load_dotenv

load_dotenv()  # before importing deepeval, so it sees DEEPEVAL_TELEMETRY_OPT_OUT

from groq import Groq
from pydantic import BaseModel
from deepeval.models import DeepEvalBaseLLM

JUDGE_MODEL = "openai/gpt-oss-120b"


class GroqJudge(DeepEvalBaseLLM):
    def __init__(self, model_name=JUDGE_MODEL):
        self.model_name = model_name
        super().__init__(model_name)  # this calls load_model() below

    def load_model(self):
        # max_retries: when Groq says "too many tokens this minute" (429),
        # the client waits the time Groq asks for and tries again
        return Groq(api_key=os.getenv("GROQ_API_KEY"), max_retries=8)

    def generate(self, prompt, schema=None):
        messages = [{"role": "user", "content": prompt}]
        extra = {}
        if schema is not None:
            shape = json.dumps(schema.model_json_schema())
            messages.insert(0, {
                "role": "system",
                "content": "Reply with ONE JSON object only, no other text. "
                           "It must follow this JSON schema:\n" + shape,
            })
            extra["response_format"] = {"type": "json_object"}

        response = self.model.chat.completions.create(
            model=self.model_name,
            messages=messages,
            temperature=0,
            reasoning_effort="low",
            max_tokens=4000,
            **extra,
        )
        text = response.choices[0].message.content

        if schema is None:
            return text
        return schema.model_validate_json(text)

    async def a_generate(self, prompt, schema=None):
        return self.generate(prompt, schema)

    def get_model_name(self):
        return f"Groq {self.model_name}"


# ---- quick self-test: python groq_judge.py ----
class Check(BaseModel):
    verdict: str
    reason: str


if __name__ == "__main__":
    judge = GroqJudge()
    print("Model:", judge.get_model_name())

    print("\n1) Plain text:")
    print(judge.generate("Say hello in five words."))

    print("\n2) JSON with a schema:")
    result = judge.generate(
        "Is this claim supported by the context? Answer verdict yes or no.\n"
        "Context: The job asks for 2 years of Python.\n"
        "Claim: The job requires Python experience.",
        schema=Check,
    )
    print(type(result).__name__, "->", result)