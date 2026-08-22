"""
SHARED Azure OpenAI client -- everyone on the team imports from here.
Don't instantiate AzureOpenAI() directly in your own files; use this module
so the endpoint/deployment names/retry logic live in exactly one place.

=== SETUP (once, on your machine) ===
    pip install openai          # NOT anthropic -- we're on Azure OpenAI
    export AZURE_OPENAI_API_KEY=<key 1 from the team dashboard>
    export AZURE_OPENAI_ENDPOINT=https://hackathon-eastus2-openai2.openai.azure.com/
    export AZURE_OPENAI_API_VERSION=2024-10-21

Endpoint and API version aren't secret (they're the same for the whole
team) so they're hardcoded as defaults below -- only the key needs an env
var. If your team dashboard shows a different endpoint, override via the
env var of the same name and it'll take precedence.

=== DEPLOYMENT NAMES (use these as `model=`, NEVER the raw model name) ===
    CHAT_FAST      -- gpt-5.4-nano deployment. Fast & cheap. Use for anything
                      high-volume: batch profile text (D1), brief parsing (D2).
    CHAT_CAPABLE   -- gpt-5.4-mini deployment. More capable, slower/costlier.
                      Use for final-mile polish shown directly to a sales rep
                      (D5 agentic recommendation, LLM profile enrichment).
    EMBEDDING      -- text-embedding-3-small, 1536 dims. Only if someone
                      upgrades D2's scoring from rule-based to embedding
                      cosine similarity.

=== RATE LIMITS ===
500 requests/min PER DEPLOYMENT, shared across the whole team hitting the
same key. A 429 means back off and retry -- chat_completion() below already
does this with exponential backoff, so call it instead of the raw SDK.

=== ONE MORE GOTCHA FROM THE DASHBOARD ===
Use `max_completion_tokens`, NOT `max_tokens`. The old `max_tokens` param is
silently accepted by some SDK versions but ignored by these deployments in
practice per the team's own getting-started example -- always pass
max_completion_tokens explicitly.
"""
import os
import time
import random
from dotenv import load_dotenv
from openai import AzureOpenAI, RateLimitError

load_dotenv()  # reads .env in the project root, if present -- silently does
               # nothing if the file doesn't exist, so this is safe even if
               # you set the env var some other way instead.

CHAT_FAST = "Team73-GPT-5.4-nano-62a442fe7bc2d89a5a33"
CHAT_CAPABLE = "Pod27-GPT-5.4-mini-efd94316b4d907432772"
EMBEDDING = "text-embedding-3-small"

DEFAULT_ENDPOINT = "https://hackathon-eastus2-openai2.openai.azure.com/"
DEFAULT_API_VERSION = "2024-10-21"

_client = None


def get_client() -> AzureOpenAI:
    """Singleton client -- reuse across calls instead of reconnecting each time."""
    global _client
    if _client is None:
        api_key = os.environ.get("AZURE_OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "AZURE_OPENAI_API_KEY is not set. Get it from the team dashboard "
                "(API key 1) and `export AZURE_OPENAI_API_KEY=...` before running."
            )
        _client = AzureOpenAI(
            azure_endpoint=os.environ.get("AZURE_OPENAI_ENDPOINT", DEFAULT_ENDPOINT),
            api_key=api_key,
            api_version=os.environ.get("AZURE_OPENAI_API_VERSION", DEFAULT_API_VERSION),
        )
    return _client


def chat_completion(messages, model=CHAT_FAST, max_completion_tokens=1000,
                    max_retries=5, **kwargs) -> str:
    """
    Wraps client.chat.completions.create with retry-with-backoff on 429,
    per the dashboard's explicit warning. Returns the response TEXT directly
    (r.choices[0].message.content) since every caller in this codebase wants
    that, not the raw response object.
    """
    client = get_client()
    last_err = None
    for attempt in range(max_retries):
        try:
            r = client.chat.completions.create(
                model=model,
                messages=messages,
                max_completion_tokens=max_completion_tokens,
                **kwargs,
            )
            return r.choices[0].message.content
        except RateLimitError as e:
            last_err = e
            wait = (2 ** attempt) + random.uniform(0, 1)
            print(f"  429 rate limited (attempt {attempt+1}/{max_retries}), "
                  f"backing off {wait:.1f}s...")
            time.sleep(wait)
    raise RuntimeError(f"Exceeded max retries on rate limiting: {last_err}")


def clean_json_response(text: str) -> str:
    """Strip markdown code fences some models wrap JSON in, before json.loads()."""
    text = text.strip()
    for fence in ("```json", "```"):
        if text.startswith(fence):
            text = text[len(fence):]
        if text.endswith("```"):
            text = text[:-3]
    return text.strip()