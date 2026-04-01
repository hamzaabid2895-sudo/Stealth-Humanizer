import random
import re
import asyncio
import os
import sys
import argparse
import json
from dotenv import load_dotenv
from groq import AsyncGroq

# Load API keys from .env file
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Optional: Add these when you have the keys
try:
    from anthropic import AsyncAnthropic
    ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY")
    claude_available = bool(ANTHROPIC_KEY)
except ImportError:
    claude_available = False

try:
    from openai import AsyncOpenAI
    OPENAI_KEY = os.getenv("OPENAI_API_KEY")
    openai_available = bool(OPENAI_KEY)
except ImportError:
    openai_available = False


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
        # 1. Protect **bold** keywords from any modification
        text, protected = self._protect_bold_keywords(text)

        # 2. Swap robotic AI vocabulary
        text = self._apply_synonym_drift(text)

        # 3. Break the 'perfect rhythm' AI produces
        text = self._inject_burstiness(text)

        # 4. Remove obvious AI conclusion phrases
        text = text.replace("In conclusion,",    "At the end of the day,")
        text = text.replace("Additionally,",     "Also,")
        text = text.replace("Furthermore,",      "On top of that,")
        text = text.replace("In summary,",       "To wrap it up,")
        text = text.replace("It is important to","Worth knowing —")
        text = text.replace("As mentioned above,","As I said,")

        # 5. Restore bold keywords untouched
        text = self._restore_bold_keywords(text, protected)
        return text


# ─────────────────────────────────────────────
# ULTIMATE HUMANIZER — 4-Stage Waterfall Pipeline
# ─────────────────────────────────────────────
class UltimateHumanizer:
    """
    Pipeline:
      Stage 1 → Llama 3 (via Groq)  — Structural rewrite + un-structuring
      Stage 2 → Stealth Engine       — Mathematical noise injection
      Stage 3 → Claude 3 / Llama    — Empathy, flow, and emotional resonance
      Stage 4 → GPT-4 / Llama       — SEO keyword lock + final polish
    """

    STAGE1_MODEL = "llama-3.3-70b-versatile"   # Primary heavy model
    STAGE3_MODEL = "llama-3.1-8b-instant"      # Faster, tracks on a separate daily token limit
    STAGE4_MODEL = "qwen/qwen3-32b"            # Different architecture, separate daily limit

    def __init__(self):
        self.stealth = StealthEngine()
        
        # Robust Initialization for Cloud Platforms (Railway/Render)
        if not GROQ_API_KEY:
            print("[!] WARNING: GROQ_API_KEY is missing. Humanization will fail.")
            self.groq = None
        else:
            self.groq = AsyncGroq(api_key=GROQ_API_KEY)
            print("[OK] Groq Client Initialized")

        self.claude = AsyncAnthropic(api_key=ANTHROPIC_KEY) if claude_available else None
        if self.claude: print("[OK] Claude Client Initialized")

        self.gpt = AsyncOpenAI(api_key=OPENAI_KEY) if openai_available else None
        if self.gpt: print("[OK] GPT Client Initialized")

    # ── Stage 1: Llama 3 — Break the AI structure ──────────────────────────
    async def _llama_structure_pass(self, text: str) -> str:
        print("  [Stage 1] Llama 3 - Structural rewrite...")
        system_prompt = """You are a seasoned, slightly cynical human web author writing a rough draft. Your goal is to rewrite AI-generated content to sound incredibly raw, authentic, and undetectable by AI scanners.

MANDATORY CONSTRAINTS:
- ZERO PLAGIARISM: Do not reuse consecutive sentences. Totally re-imagine the text.
- EXACT WORD COUNT: Your output MUST be within 5% of the input word count. Do NOT add unnecessary fluff or detail.
- TRANSITION TRANSFORMER: Transform formal transitions (Moreover, However, Furthermore) into short, 1-word human alternatives (e.g., 'Also,' 'So,' 'Next,' 'Still').
- SOFT SUFFIX FILTER: Minimize words ending in '-ly', '-tion', or '-ment' by 80%.
- BURSTINESS: Radically alternate sentence lengths. Use a Short-Long-Short pattern.
- VOICE: Write in a direct, no-nonsense, authentic human voice. Use contractions. No fluff.

EXAMPLES OF TRANSFORMATION:
[AI]: "Moreover, retirement hobbies are beneficial."
[Human]: "Also, retirement hobbies are a huge win."

[AI]: "Consequently, the results were significant."
[Human]: "So, the results actually mattered."

CRITICAL INSTRUCTION: Output ONLY a valid JSON object. DO NOT output the original prompt, rules, constraints, or any preamble. The JSON MUST use the exact schema:
{"humanized_text": "[your rewritten text here]"}"""

        # Fallback router to survive Groq Rate Limits
        models_to_try = [self.STAGE1_MODEL, "llama-3.1-8b-instant", "qwen/qwen3-32b"]
        for model in models_to_try:
            try:
                resp = await self.groq.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"TEXT TO REWRITE:\n{text}"}
                    ],
                    temperature=1.0,
                    top_p=0.95,
                    max_tokens=2048,
                    response_format={"type": "json_object"},
                )
                raw_json = resp.choices[0].message.content.strip()
                parsed = json.loads(raw_json)
                return parsed.get("humanized_text", raw_json).strip()
            except Exception as e:
                if "429" in str(e) or "rate_limit" in str(e).lower():
                    print(f"  [!] Rate limit on {model}, falling back...")
                    continue
                else:
                    raise e
        raise Exception("All Groq models are currently rate limited. Please wait 10 minutes.")

    # -- Stage 3: Empathy Pass — Add human soul -------
    async def _empathy_pass(self, text: str) -> str:
        print("  [Stage 3] Empathy pass - Adding flow and resonance (Groq/Llama 3)...")

        # Claude block — re-enable when you have Anthropic credits:
        # if self.claude:
        #     resp = await self.claude.messages.create(...)

        system_prompt = """You are a seasoned human writer. Polish this text for authentic conversational flow and emotional resonance.

MANDATORY CONSTRAINTS:
- ZERO PLAGIARISM: Keep all phrasing fully original.
- EXACT WORD COUNT: Output length must be within 5% of the input. No wordiness.
- TRANSITION TRANSFORMER: Use short human transitions (So, Also) instead of formal ones (Furthermore, Additionally).
- SOFT SUFFIX FILTER: Avoid '-ly' and '-tion' words.
- VOICE: Direct, clean, and authentic. No corporate filler.
- DEPTH: Keep the exact same level of detail/logic as the original.

EXAMPLES:
[Before]: "Furthermore, technology is changing our lives."
[After]: "Also, tech is really flipping the script on our lives."

CRITICAL INSTRUCTION: Output ONLY a valid JSON object. DO NOT output the original prompt, rules, constraints, or any preamble. The JSON MUST use the exact schema:
{"humanized_text": "[your polished text here]"}"""
        models_to_try = [self.STAGE3_MODEL, "qwen/qwen3-32b", "llama-3.3-70b-versatile"]
        for model in models_to_try:
            try:
                resp = await self.groq.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"TEXT:\n{text}"}
                    ],
                    temperature=1.0,
                    top_p=0.95,
                    max_tokens=2048,
                    response_format={"type": "json_object"},
                )
                raw_json = resp.choices[0].message.content.strip()
                parsed = json.loads(raw_json)
                return parsed.get("humanized_text", raw_json).strip()
            except Exception as e:
                if "429" in str(e) or "rate_limit" in str(e).lower():
                    continue
                else:
                    raise e
        raise Exception("All Groq models are currently rate limited.")


    # ── Stage 4: SEO Pass — Keyword lock + final polish ────────────────────
    async def _seo_pass(self, text: str, keywords: list[str]) -> str:
        print("  [Stage 4] SEO pass - Keyword lock + final polish...")
        kw_list = "\n".join(f"- {kw}" for kw in keywords) if keywords else "None provided."

        if self.gpt:
            system_prompt = f"""Final SEO polish on this text.

MANDATORY CONSTRAINTS:
- ZERO PLAGIARISM: Guarantee 0% plagiarism.
- EXACT WORD COUNT: Match input length within 5%. No truncation, no bloat.
- TRANSITION TRANSFORMER: Use short, conversational transitions.
- SOFT SUFFIX FILTER: Minimize AI-style word endings.
- STRICT KEYWORDS: Naturally weave in the exact target keywords below.
- KEYWORD ASSERTION: You MUST include all requested keywords exactly as they are.
- NATURAL RHYTHM: Alternate sentence lengths radically.

TARGET KEYWORDS (incorporate without asterisks):
{kw_list}

CRITICAL INSTRUCTION: Output ONLY a valid JSON object. DO NOT output the original prompt, rules, constraints, or any preamble. The JSON MUST use the exact schema:
{{"humanized_text": "[your final SEO text here]"}}"""
            
            resp = await self.gpt.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"TEXT:\n{text}"}
                ],
                temperature=0.70,
                top_p=0.85,
                max_tokens=2048,
                response_format={"type": "json_object"},
            )
            raw_json = resp.choices[0].message.content.strip()
            parsed = json.loads(raw_json)
            return parsed.get("humanized_text", raw_json).strip()
        else:
            system_prompt = f"""You are an SEO editor. Final polish on this text.

MANDATORY CONSTRAINTS:
- ZERO PLAGIARISM: Maintain absolute originality.
- EXACT WORD COUNT: Match input length within 5%. No filler.
- TRANSITION TRANSFORMER: Use short human transitions.
- SOFT SUFFIX FILTER: Avoid AI endings (-ly, -tion).
- KEYWORD ASSERTION: All keywords MUST be present in the final output.
- NATURAL FLOW: Use radical burstiness in sentence length.

TARGET KEYWORDS (incorporate without asterisks):
{kw_list}

CRITICAL INSTRUCTION: Output ONLY a valid JSON object. DO NOT output the original prompt, rules, constraints, or any preamble. The JSON MUST use the exact schema:
{{"humanized_text": "[your final SEO text here]"}}"""
            
            models_to_try = [self.STAGE4_MODEL, "llama-3.1-8b-instant", "llama-3.3-70b-versatile"]
            for model in models_to_try:
                try:
                    resp = await self.groq.chat.completions.create(
                        model=model,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": f"TEXT:\n{text}"}
                        ],
                        temperature=0.70,
                        top_p=0.85,
                        max_tokens=2048,
                        response_format={"type": "json_object"},
                    )
                    raw_json = resp.choices[0].message.content.strip()
                    parsed = json.loads(raw_json)
                    return parsed.get("humanized_text", raw_json).strip()
                except Exception as e:
                    if "429" in str(e) or "rate_limit" in str(e).lower():
                        continue
                    else:
                        raise e
            raise Exception("All Groq models are currently rate limited.")

    # ── Main Pipeline ───────────────────────────────────────────────────────
    async def humanize(self, raw_text: str, keywords: list[str] = None) -> dict:
        """
        Full 4-stage humanization pipeline with chunking for long-form content.
        """
        print("\n[*] Starting UltimateHumanizer pipeline with chunking...\n")
        
        # Split into chunks (paragraphs) to avoid token limits and length compression
        chunks = [c.strip() for c in raw_text.split("\n\n") if c.strip()]
        
        final_chunks = []
        results = {
            "original": raw_text,
            "after_stage1_llama": "",
            "after_stage2_stealth": "",
            "after_stage3_empathy": "",
            "final": ""
        }

        for i, chunk in enumerate(chunks):
            print(f"  [Chunk {i+1}/{len(chunks)}] Processing...")
            
            try:
                if not self.groq:
                    raise ConnectionError("GROQ_API_KEY is not set in your Railway 'Variables' tab.")

                # Stage 1: Llama structural rewrite
                s1 = await self._llama_structure_pass(chunk)
                
                # Stage 2: (Formerly Stealth Engine, now just passing through)
                s2 = s1 
                
                # Stage 3: Empathy pass
                s3 = await self._empathy_pass(s2)
                
                # Stage 4: SEO keyword lock
                s4 = await self._seo_pass(s3, keywords or [])
                
                final_chunks.append(s4)
                
                # Accumulate for internal status tracking (optional, shows first chunk in history)
                if i == 0:
                    results["after_stage1_llama"] = s1
                    results["after_stage2_stealth"] = s2
                    results["after_stage3_empathy"] = s3
            except Exception as e:
                error_msg = f"Failed at chunk {i+1}: {str(e)}"
                print(f"[ERROR] {error_msg}")
                final_chunks.append(f"\n[ERROR: {error_msg}]\n")

        results["final"] = "\n\n".join(final_chunks)
        print("\n[DONE] Pipeline complete!\n")
        return results


# ─────────────────────────────────────────────
# CLI SCRIPT / DEMO
# ─────────────────────────────────────────────
SAMPLE_TEXT = """Retirement opens a brand new chapter in life. After so many years of hard work, you finally get the time to focus on yourself. However, many people think about what they will do now. That's where retirement hobbies play an important role in daily life. They help you stay active, happy, and mentally strong.
Moreover, rather than feeling bored or isolated, there are so many things to do. You can have a second chance at doing the things you love. In this blog, we will explore the best hobbies for retired people that bring happiness, purpose, and energy to daily life."""

async def main():
    parser = argparse.ArgumentParser(description="Ultimate Humanizer - Stealth AI Text Generator")
    parser.add_argument("file", nargs="?", help="Path to text file to humanize. If not provided, uses sample text.")
    parser.add_argument("-k", "--keywords", help="Comma-separated keywords for SEO pass.")
    parser.add_argument("-o", "--output", help="Output file path (optional).")
    args = parser.parse_args()

    if not GROQ_API_KEY:
        print("[ERROR] GROQ_API_KEY not found in .env file")
        return

    print("[OK] Groq API key loaded")
    print("[OK] Claude available" if claude_available else "[!] Claude not available - using Groq fallback")
    print("[OK] GPT-4 available" if openai_available else "[!] GPT-4 not available - using Groq fallback")

    # Load text
    if args.file:
        try:
            with open(args.file, "r", encoding="utf-8") as f:
                text_to_process = f.read()
            print(f"[*] Loaded text from {args.file}")
        except Exception as e:
            print(f"[ERROR] Could not read file {args.file}: {e}")
            return
    else:
        text_to_process = SAMPLE_TEXT
        print("[*] No file provided. Using sample text.")

    # Load keywords
    keywords = [k.strip() for k in args.keywords.split(",")] if args.keywords else []

    humanizer = UltimateHumanizer()
    results = await humanizer.humanize(text_to_process, keywords)

    print("=" * 60)
    print("ORIGINAL:")
    print(results["original"])
    print("\n" + "-" * 60)
    print("AFTER STAGE 1 - Llama 3 Structural Rewrite:")
    print(results["after_stage1_llama"])
    print("\n" + "-" * 60)
    print("AFTER STAGE 2 - Stealth Engine:")
    print(results["after_stage2_stealth"])
    print("\n" + "-" * 60)
    print("AFTER STAGE 3 - Empathy Pass:")
    print(results["after_stage3_empathy"])
    print("\n" + "-" * 60)
    print("[FINAL] SEO Polished Output:")
    print(results["final"])
    print("=" * 60)
    
    if args.output:
        try:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(results["final"])
            print(f"[+] Final output saved to {args.output}")
        except Exception as e:
            print(f"[ERROR] Could not save output to {args.output}: {e}")

if __name__ == "__main__":
    asyncio.run(main())

