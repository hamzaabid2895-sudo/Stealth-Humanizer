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
            "Anyway,", "The reality is,", "So here's the deal:",
            "And honestly,", "Regardless,",
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
            "a testament to":  "proof of",
            "across the board": "everywhere",
            "key takeaway":     "main point",
            "optimal":          "best",
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
        """Randomly injects human interjections and breaks 'robotic' sentence rhythm."""
        sentences = re.split(r'(?<=[.!?]) +', text)
        result = []
        for i, sent in enumerate(sentences):
            # Inject a filler at approximately every 4th semi-long sentence
            if i % 4 == 0 and len(sent.split()) > 10 and random.random() > 0.4:
                filler = random.choice(self.human_fillers)
                # Ensure we don't double-capitalize
                sent = sent[0].lower() + sent[1:] if sent else sent
                result.append(f"{filler} {sent}")
            else:
                result.append(sent)
        return " ".join(result)

    def _apply_synonym_drift(self, text):
        """Swaps robotic AI formalisms for natural professional-casual language."""
        for robot, human in self.phrase_map.items():
            # Use word boundaries to avoid partial matches
            pattern = re.compile(r'\b' + re.escape(robot) + r'\b', re.IGNORECASE)
            text = pattern.sub(human, text)
        return text

    def apply_stealth_layer(self, text):
        """Full stealth workflow — protects bold keywords throughout."""
        text, protected = self._protect_bold_keywords(text)
        
        # 1. Vocabulary Swap
        text = self._apply_synonym_drift(text)
        
        # 2. Burstiness Injection
        text = self._inject_burstiness(text)
        
        # 3. Connector Cleansing (AI Transitions)
        text = text.replace("In conclusion,",    "At the end of the day,")
        text = text.replace("Additionally,",     "Also,")
        text = text.replace("Furthermore,",      "On top of that,")
        text = text.replace("In summary,",       "To wrap it up,")
        text = text.replace("Not only that but", "Plus,")
        text = text.replace("It is crucial to",  "You really need to")
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

    async def _llama_structure_pass(self, text: str, prev_text: str = "") -> str:
        print("  [Stage 1] High-Perplexity Structural Rewrite...")
        
        # Expert Persona (Professional Casual)
        system_prompt = f"""You are a seasoned, expert human author writing for a high-end publication. 
Your goal is to REWRITE the following AI-generated text to sound 100% human, authentic, and undetectable.

MANDATORY PERSONA CONSTRAINTS:
- VOICE: Professional, expert, yet conversational (Professional-Casual). No robotic academic tone.
- PERPLEXITY: Use unconventional but grammatically correct sentence structures. Mix short, blunt sentences with complex, thought-provoking ones.
- BURSTINESS: Avoid the 'perfect rhythm' of AI. Alternate sentence lengths radically.
- ZERO AI MARKERS: Do NOT use words like 'vibrant,' 'tapestry,' 'unleash,' 'delve,' 'complexities,' or 'moreover.'
- HUMAN TRANSITIONS: Use natural human transitions like 'Basically,', 'Look,', 'Here's why this matters:', 'To be fair,', 'Wait, it gets better.'
- CONTEXTUAL FLOW: Ensure this piece fits perfectly after the following section:
---
PREVIOUS CONTEXT (Match this style):
{prev_text if prev_text else "None"}
---

CRITICAL INSTRUCTION: Output ONLY a valid JSON object. Do NOT include any preamble or notes.
The JSON must follow this exact schema:
{{"humanized_text": "[your expert rewrite here]"}}"""
        
        raw_json = await self._ai_call(system_prompt, f"TEXT TO REWRITE:\n{text}")
        try:
            return json.loads(raw_json).get("humanized_text", raw_json).strip()
        except:
            return raw_json

    async def _empathy_pass(self, text: str, prev_text: str = "") -> str:
        print("  [Stage 2] Empathy & Flow (Human Connection)...")
        system_prompt = f"""You are a warm, knowledgeable human expert. Polish this text to add emotional resonance, better flow, and 'Human Connective Tissue.'

PERSONA CONSTRAINTS:
- VOICE: Professional-Casual. Expert yet accessible.
- NO GRAMMAR ERRORS: Maintain full, solid English grammar rules.
- HUMAN QUIRKS: Use rhetorical questions or occasional expert anecdotes.
- TRANSITION TRANSFORMER: Transform formal transitions into professional-casual alternatives (e.g., 'At the end of the day,', 'Basically,', 'Here's the deal:').
- FLOW: Ensure the text reads like a smooth, coherent train of thought, following this context:
---
{prev_text if prev_text else "None"}
---

CRITICAL: Output ONLY a valid JSON object with the key "humanized_text"."""

        raw_json = await self._ai_call(system_prompt, f"TEXT TO REFINE:\n{text}", temperature=0.9)
        try:
            return json.loads(raw_json).get("humanized_text", raw_json).strip()
        except:
            return raw_json

    async def _seo_pass(self, text: str, keywords: list[str], prev_text: str = "") -> str:
        print("  [Stage 3] SEO Invisible Embedding...")
        kw_list = ", ".join(keywords) if keywords else "None"
        system_prompt = f"""You are a master SEO strategist. Naturally weave in these keywords into the humanized text below without breaking the high-quality flow:
TARGET KEYWORDS: {kw_list}

CONSTRAINTS:
- NO GRAMMAR ERRORS: Maintain perfect professional grammar.
- KEYWORD CLOAKING: Keywords must be placed naturally. Do NOT force them in.
- VOICE RETENTION: Maintain the Expert-Yet-Accessible tone.
- ZERO PLAGIARISM: Ensure the 0% plagiarism score is preserved.

CRITICAL: Output ONLY a valid JSON object with the key "humanized_text"."""

        raw_json = await self._ai_call(system_prompt, f"TEXT TO POLISH:\n{text}", temperature=0.7)
        try:
            return json.loads(raw_json).get("humanized_text", raw_json).strip()
        except:
            return raw_json

    async def _global_review_pass(self, text: str) -> str:
        """Final safety net pass to ensure the entire blog feels human and coherent."""
        if len(text.split()) > 4000:
            print("  [Stage 5] Skipping Global Pass (Text too long).")
            return text
            
        print("  [Stage 5] Final Global Review (Collective Check)...")
        system_prompt = """You are a senior editor for a premium lifestyle and tech magazine. 
Review the entire blog post below. Your goal is to identify any robotic patterns or 'Collective AI' structures that give away the text's origin.

FINAL POLISH CONSTRAINTS:
- COHERENCE: Ensure the transitions between paragraphs are professional-casual and smooth.
- REPETITION: Remove any phrases or words that appear repeatedly across different sections.
- HUMAN VIBE: Ensure the entire piece feels like it was written by one expert person in one sitting.

CRITICAL: Output ONLY a valid JSON object with the key "humanized_text"."""

        raw_json = await self._ai_call(system_prompt, f"FULL BLOG TEXT:\n{text}", temperature=0.7)
        try:
            return json.loads(raw_json).get("humanized_text", raw_json).strip()
        except:
            return raw_json

    async def humanize(self, raw_text: str, keywords: list[str] = []) -> dict:
        """Full Overhauled Pipeline with Contextual Chunking."""
        print(f"\n[*] Humanizing {len(raw_text.split())} words with Contextual Memory...")
        
        chunks = [c.strip() for c in raw_text.split("\n\n") if c.strip()]
        final_chunks = []
        last_human_chunk = "" # Contextual Buffer
        
        for i, chunk in enumerate(chunks):
            print(f"  [Chunk {i+1}/{len(chunks)}] Processing...")
            try:
                # Stage 1: Structural Rewrite
                s1 = await self._llama_structure_pass(chunk, prev_text=last_human_chunk)
                
                # Stage 2: Stealth Syntax Injection
                s2 = self.stealth.apply_stealth_layer(s1)
                
                # Stage 3: Empathy & Resonance
                s3 = await self._empathy_pass(s2, prev_text=last_human_chunk)
                
                # Stage 4: SEO Keyword Lock
                s4 = await self._seo_pass(s3, keywords or [], prev_text=last_human_chunk)
                
                final_chunks.append(s4)
                
                # Update Context (Take last 120 words for continuity)
                words = s4.split()
                last_human_chunk = " ".join(words[-120:]) if words else ""
                
            except Exception as e:
                print(f"  [!] Chunk {i+1} failed: {str(e)}")
                final_chunks.append(f"\n[Error at Chunk {i+1}: {str(e)}]\n")
        
        # FINAL STAGE 5: Global Review Pass
        combined_text = "\n\n".join(final_chunks)
        try:
            final_text = await self._global_review_pass(combined_text)
        except Exception as e:
            print(f"  [!] Global Pass failed: {str(e)}")
            final_text = combined_text
            
        return {
            "original": raw_text,
            "final": final_text
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
