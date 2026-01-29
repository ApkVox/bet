"""
=============================================
GROQ AGENT - AI Validation for Ladder System
=============================================
Uses the free Groq API (Llama-3 models) to:
1. Validate bets by checking for injuries/news
2. Analyze risk factors
3. Provide reasoning for ticket selection
"""

import os
import time
from typing import Literal, Optional
from dataclasses import dataclass
from groq import Groq

# Type aliases
SafetyVerdict = Literal["SAFE", "RISK", "UNKNOWN"]


@dataclass
class GroqValidationResult:
    """Result of a Groq safety check."""
    match_id: str
    verdict: SafetyVerdict
    reasoning: str
    latency_ms: int
    raw_response: str


class GroqAgent:
    """
    Zero-cost AI validation agent using Groq's free tier.
    Implements rate limiting and error handling.
    """
    
    def __init__(self, api_key: Optional[str] = None, model: str = "llama-3.3-70b-versatile"):
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("GROQ_API_KEY not found. Set it in environment or pass directly.")
        
        self.client = Groq(api_key=self.api_key)
        self.model = model
        self.last_call_time = 0
        self.min_delay_ms = 500  # Respect rate limits
    
    def _rate_limit(self):
        """Ensure we don't exceed Groq's rate limits."""
        elapsed = (time.time() - self.last_call_time) * 1000
        if elapsed < self.min_delay_ms:
            time.sleep((self.min_delay_ms - elapsed) / 1000)
        self.last_call_time = time.time()
    
    def sanity_check(self, home_team: str, away_team: str) -> GroqValidationResult:
        """
        Perform a safety check on a match by querying Groq for recent news.
        
        Args:
            home_team: Name of the home team
            away_team: Name of the away team
            
        Returns:
            GroqValidationResult with SAFE/RISK verdict
        """
        match_id = f"{home_team}:{away_team}"
        
        prompt = f"""You are a sports betting analyst. Analyze the upcoming NBA match:
**{home_team} vs {away_team}**

Based on your knowledge (training data up to early 2024), consider:
1. Are there typically injury-prone star players on either team?
2. Is this a back-to-back game scenario that could affect performance?
3. Any known rivalry or motivation factors?

IMPORTANT: You must respond with EXACTLY one of these two words as your first word:
- "SAFE" - if this seems like a normal, predictable matchup
- "RISK" - if there are red flags that could cause an upset

After your verdict, provide a brief 1-2 sentence explanation.

Example response: "SAFE - Both teams are healthy and playing at home is a clear advantage for the Lakers."
"""
        
        self._rate_limit()
        start_time = time.time()
        
        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a concise sports analyst. Always start with SAFE or RISK."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=150,
                temperature=0.3
            )
            
            response_text = completion.choices[0].message.content.strip() if completion.choices else ""
            latency = int((time.time() - start_time) * 1000)
            
            # Parse verdict
            if response_text.upper().startswith("SAFE"):
                verdict: SafetyVerdict = "SAFE"
            elif response_text.upper().startswith("RISK"):
                verdict = "RISK"
            else:
                verdict = "UNKNOWN"
            
            return GroqValidationResult(
                match_id=match_id,
                verdict=verdict,
                reasoning=response_text,
                latency_ms=latency,
                raw_response=response_text
            )
            
        except Exception as e:
            return GroqValidationResult(
                match_id=match_id,
                verdict="UNKNOWN",
                reasoning=f"Error: {str(e)}",
                latency_ms=0,
                raw_response=""
            )
    
    def select_optimal_parlay(
        self,
        candidates: list[dict],
        current_capital: float,
        bad_beats: list[str],
        strategy: str = "FENIX"
    ) -> dict:
        """
        Use Groq to intelligently select the best parlay from candidates.
        
        Args:
            candidates: List of match predictions with probabilities
            current_capital: Current bankroll
            bad_beats: List of past losing notes for context
            strategy: 'SAFE', 'FENIX', or 'AGGRESSIVE'
            
        Returns:
            dict with selected events and reasoning
        """
        # Format candidates for the prompt
        candidates_text = "\n".join([
            f"ID {i}: {c['home_team']} vs {c['away_team']} | Pick: {c['winner']} ({c['probability']}%) | Odds: {c['decimal_odds']:.2f}"
            for i, c in enumerate(candidates)
        ])
        
        bad_beats_text = "\n".join([f"- {note}" for note in bad_beats[:5]]) if bad_beats else "No recent losses."
        
        # Strategy-specific instructions
        strategy_rules = {
            "SAFE": "Select EXACTLY 2 games with probability > 70% each. Prioritize favorites.",
            "FENIX": "Select EXACTLY 3 games with probability > 60% each. Balance risk and reward.",
            "AGGRESSIVE": "Select EXACTLY 4 games with probability > 55% each. Accept higher variance."
        }
        
        prompt = f"""SYSTEM PHOENIX - SURVIVAL MODE
Capital: {current_capital:,.0f} COP
Strategy: {strategy}

PAST MISTAKES (DO NOT REPEAT):
{bad_beats_text}

AVAILABLE MATCHES:
{candidates_text}

TASK: {strategy_rules.get(strategy, strategy_rules['FENIX'])}

Respond in this EXACT JSON format:
{{
  "selected_ids": [0, 2, 5],
  "reasoning": "Brief explanation of why these picks",
  "combined_probability": 45.5,
  "phoenix_note": "Motivational one-liner"
}}
"""
        
        self._rate_limit()
        
        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are PHOENIX, a betting survival AI. Respond ONLY with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=300,
                temperature=0.5
            )
            
            response_text = completion.choices[0].message.content.strip() if completion.choices else "{}"
            
            # Parse JSON from response
            import json
            import re
            
            # Find JSON in response
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if json_match:
                result = json.loads(json_match.group())
                return result
            else:
                return {"error": "No JSON found", "raw": response_text}
                
        except Exception as e:
            return {"error": str(e)}
    
    def analyze_loss(self, match_id: str, predicted: str, actual: str, probability: float) -> str:
        """
        Analyze a losing bet to extract learning.
        
        Args:
            match_id: The match identifier
            predicted: Team/outcome we predicted
            actual: Actual winner/outcome
            probability: Our confidence level
            
        Returns:
            A learning note for the bad beats memory
        """
        prompt = f"""A prediction failed:
- Match: {match_id}
- We predicted: {predicted} (confidence: {probability}%)
- Actual result: {actual}

In ONE sentence, what pattern might explain this loss? Focus on actionable lessons.
Example: "Back-to-back games often cause favorites to underperform."
"""
        
        self._rate_limit()
        
        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=100,
                temperature=0.7
            )
            
            return completion.choices[0].message.content.strip() if completion.choices else "Unknown pattern"
            
        except Exception:
            return "Analysis unavailable"


# Singleton instance for easy import
_agent_instance: Optional[GroqAgent] = None

def get_groq_agent() -> GroqAgent:
    """Get or create the singleton GroqAgent instance."""
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = GroqAgent()
    return _agent_instance


if __name__ == "__main__":
    # Quick test
    agent = GroqAgent()
    result = agent.sanity_check("Los Angeles Lakers", "Golden State Warriors")
    print(f"Match: {result.match_id}")
    print(f"Verdict: {result.verdict}")
    print(f"Reasoning: {result.reasoning}")
    print(f"Latency: {result.latency_ms}ms")
