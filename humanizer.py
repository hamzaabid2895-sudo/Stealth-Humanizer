import random
import re
import asyncio
import os
import sys
import argparse
import json
from dotenv import load_dotenv
from groq import AsyncGroq
from anthropic import AsyncAnthropic
from openai import AsyncOpenAI
import httpx

# Load API keys and strip whitespace (Crucial for Railway/Render copy-pastes)
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY", "").strip()
OPENAI_KEY = os.getenv("OPENAI_API_KEY", "").strip()

claude_available = bool(ANTHROPIC_KEY)
openai_available = bool(OPENAI_KEY)


# ─────────────────────────────────────────────
# STEALTH ENGINE
# ─────────────────────────────────────────────
class StealthEngine:
    """
    Applies 'Human Noise' and 'Syntactic Irregularity' to break
    the mathematical patterns that detectors like Quetext or GPTZero flag.
    """

    def __init__(self):
        self.human_fillers = [
            "Now, here's the thing:", "Truth be told,",
            "It's worth mentioning that", "I've noticed that",
            "To be fair,", "Honestly,", "Basically,", "Look —",
            "Here's what I mean:", "And honestly,",
        ]

        self.phrase_map = {
            "utilize":       "use",
            "facilitate":    "help with",
            "comprehensive": "thorough",
            "subsequently":  "then",
            "implement":     "set up",
            "ensure":        "make sure",
            "demonstrate":   "show",
            "leverage":      "use",
            "robust":        "solid",
            "delve":         "dive",
            "tapestry":      "mix",
            "transformative":"game-changing",
            "unlock":        "open up",
            "in the realm of": "in",
            "it is important to note that": "note that",
            "it is worth noting that":      "worth noting —",
            "due to the fact that":         "because",
        }

    def _protect_bold_keywords(self, text):
        """Extract **bold** phrases and replace with placeholders to protect them."""
        protected = {}
        pattern = re.compile(r'\*\*(.+?)\*\*')
        counter = [0]

        def replace(m):
            token = f"__BOLD_{counter[0]}__"
            protected[token] = m.group(0)
            counter[0] += 1
            return token

        text = pattern.sub(replace, text)
        return text, protected

    def _restore_bold_keywords(self, text, protected):
        """Restore **bold** placeholders back to original bold text."""
        for token, original in protected.items():
            text = text.replace(token, original)
        return text

    def _inject_burstiness(self, text):
        """Randomly injects human interjections to create 'bursty' rhythm."""
        sentences = re.split(r'(?<=[.!?]) +', text)
        result = []
        for i, sent in enumerate(sentences):
            if i % 4 == 0 and len(sent.split()) > 10:
                filler = random.choice(self.human_fillers)
                result.append(f"{filler} {sent[0].lower() + sent[1:]}")
            else:
                result.append(sent)
        return " ".join(result)

    def _apply_synonym_drift(self, text):
        """Swaps robotic AI formalisms for natural conversational language."""
        for robot, human in self.phrase_map.items():
            pattern = re.compile(re.escape(robot), re.IGNORECASE)
            text = pattern.sub(human, text)
        return text

    def apply_stealth_layer(self, text):
        """Full stealth workflow — protects bold keywords throughout."""
        text, protected = self._protect_bold_keywords(text)
        text = self._apply_synonym_drift(text)
        text = self._inject_burstiness(text)
        text = text.replace("In conclusion,",    "At the end of the day,")
        text = text.replace("Additionally,",     "Also,")
        text = text.replace("Furthermore,",      "On top of that,")
        text = text.replace("In summary,",       "To wrap it up,")
        text = text.replace("It is important to","Worth knowing —")
        text = text.replace("As mentioned above,","As I said,")
        text = self._restore_bold_keywords(text, protected)
        return text


# ─────────────────────────────────────────────
# ULTIMATE HUMANIZER — 3-Stage Dual AI Pipeline
# ─────────────────────────────────────────────
class UltimateHumanizer:
    """
    High-performance humanizer with automatic fallback from Groq to OpenAI.
    """

    STAGE1_MODEL = "llama-3.3-70b-versatile"
    STAGE3_MODEL = "llama-3.1-8b-instant"
    STAGE4_MODEL = "qwen2.5-72b-instruct"
    FALLBACK_MODEL = "gpt-4o"

    def __init__(self):
        self.stealth = StealthEngine()
        http_client = httpx.AsyncClient(timeout=60.0, follow_redirects=True)

        self.groq = AsyncGroq(api_key=GROQ_API_KEY, http_client=http_client) if GROQ_API_KEY else None
        self.gpt = AsyncOpenAI(api_key=OPENAI_KEY, http_client=http_client) if openai_available else None
        self.claude = AsyncAnthropic(api_key=ANTHROPIC_KEY, http_client=http_client) if claude_available else None

        if self.groq: print("[OK] Groq Client Initialized")
        if self.gpt:  print("[OK] OpenAI Fallback Ready")

    async def _ai_call(self, system_prompt: str, user_text: str, temperature: float = 0.8, p: float = 0.9, use_json: bool = True) -> str:
        """Universal router: Groq (Primary) -> GPT-4o (Fallback on 401/429)"""
        
        # 1. Try Groq (Fast/Free)
        if self.groq:
            models = [self.STAGE1_MODEL, "llama-3.1-8b-instant"]
            for model in models:
                try:
                    resp = await self.groq.chat.completions.create(
                        model=model,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_text}
                        ],
                        temperature=temperature,
                        top_p=p,
                        max_tokens=2048,
                        response_format={"type": "json_object"} if use_json else None
                    )
                    return resp.choices[0].message.content.strip()
                except Exception as e:
                    err = str(e).lower()
                    if "401" in err or "unauthorized" in err:
                        print(f"  [!] Groq Auth Error. Switching to OpenAI...")
                        break 
                    if "429" in err or "rate_limit" in err:
                        print(f"  [!] Groq Rate Limit on {model}. Trying next...")
                        continue
                    raise e

        # 2. Try OpenAI Fallback
        if self.gpt:
            print(f"  [FALLBACK] Routing request to OpenAI ({self.FALLBACK_MODEL})...")
            try:
                resp = await self.gpt.chat.completions.create(
                    model=self.FALLBACK_MODEL,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_text}
                    ],
                    temperature=temperature,
                    response_format={"type": "json_object"} if use_json else None
                )
                return resp.choices[0].message.content.strip()
            except Exception as e:
                print(f"  [!] OpenAI Error: {str(e)}")
                raise e
        
        # 3. Complete Failure
        raise ConnectionError("Both AI providers failed. Check your API Keys on Railway.")

    async def _llama_structure_pass(self, text: str) -> str:
        print("  [Stage 1] Structural rewrite...")
        system_prompt = """You are a seasoned human author. Rewrite the AI content to sound incredibly raw, authentic, and undetectable. 
        Zero Plagiarism. Exact Word Count. Short human transitions. Output ONLY JSON: {"humanized_text": "..."}"""
        
        raw_json = await self._ai_call(system_prompt, f"TEXT:\n{text}")
        try:
            return json.loads(raw_json).get("humanized_text", raw_json).strip()
        except:
            return raw_json

    async def _empathy_pass(self, text: str) -> str:
        print("  [Stage 2] Empathy & Flow...")
        system_prompt = """You are a warm human writer. Polish for flow and resonance. 
        Simple words. Direct tone. Output ONLY JSON: {"humanized_text": "..."}"""
        
        raw_json = await self._ai_call(system_prompt, f"TEXT:\n{text}", temperature=0.9)
        try:
            return json.loads(raw_json).get("humanized_text", raw_json).strip()
        except:
            return raw_json

    async def _seo_pass(self, text: str, keywords: list[str]) -> str:
        print("  [Stage 3] SEO Final Lock...")
        kw_list = ", ".join(keywords) if keywords else "None"
        system_prompt = f"""Master SEO editor. Weave in these keywords naturally: {kw_list}. 
        No bloat. Preserve human tone. Output ONLY JSON: {{"humanized_text": "..."}}"""
        
        raw_json = await self._ai_call(system_prompt, f"TEXT:\n{text}", temperature=0.7)
        try:
            return json.loads(raw_json).get("humanized_text", raw_json).strip()
        except:
            return raw_json

    async def humanize(self, raw_text: str, keywords: list[str] = None) -> dict:
        """Full dual-provider pipeline with chunking."""
        print(f"\n[*] Processing {len(raw_text.split())} words...")
        chunks = [c.strip() for c in raw_text.split("\n\n") if c.strip()]
        final_chunks = []
        
        for i, chunk in enumerate(chunks):
            print(f"  [Chunk {i+1}/{len(chunks)}] Working...")
            try:
                s1 = await self._llama_structure_pass(chunk)
                s2 = self.stealth.apply_stealth_layer(s1)
                s3 = await self._empathy_pass(s2)
                s4 = await self._seo_pass(s3, keywords or [])
                final_chunks.append(s4)
            except Exception as e:
                print(f"  [!] Chunk {i+1} failed: {str(e)}")
                final_chunks.append(f"\n[Error: {str(e)}]\n")
        
        return {
            "original": raw_text,
            "final": "\n\n".join(final_chunks)
        }


# ─────────────────────────────────────────────
# CLI SCRIPT / DEMO
# ─────────────────────────────────────────────
async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("file", nargs="?")
    parser.add_argument("-k", "--keywords")
    args = parser.parse_args()

    humanizer = UltimateHumanizer()
    text = "AI is change our life."
    if args.file:
        with open(args.file, "r") as f: text = f.read()
    
    kw = [k.strip() for k in args.keywords.split(",")] if args.keywords else []
    res = await humanizer.humanize(text, kw)
    print("\nFINAL OUTPUT:\n" + res["final"])

if __name__ == "__main__":
    asyncio.run(main())
