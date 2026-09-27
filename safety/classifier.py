import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import torch
from transformers import pipeline
from typing import Dict, Any
from config import SAFETY_MODEL
from safety.policy import evaluate_scores

_moderator = None


def get_safety_classifier():
    """
    Initializes and caches the safety classification pipeline.
    Runs once and reuses the instance across all calls.
    """
    global _moderator
    if _moderator is None:
        device = 0 if torch.cuda.is_available() else -1
        device_name = "CUDA" if torch.cuda.is_available() else "CPU"
        print(f"Loading safety classifier '{SAFETY_MODEL}' on {device_name}...")
        try:
            _moderator = pipeline(
                "text-classification",
                model=SAFETY_MODEL,
                tokenizer=SAFETY_MODEL,
                device=device,
                top_k=None,
            )
            print("✅ Safety classifier loaded successfully")
        except Exception as e:
            print(f"❌ Failed to load safety classifier '{SAFETY_MODEL}': {e}")
            raise e
    return _moderator


def safety_gate(text: str) -> Dict[str, Any]:
    """
    Runs text through the safety moderation classifier and evaluates scores against safety policies.
    """
    if not text or not str(text).strip():
        return {
            "decision": "ALLOW",
            "category": None,
            "score": 0.0,
            "ok_score": 1.0,
        }

    moderator = get_safety_classifier()
    results = moderator(text)[0]

    scores = {
        item["label"]: item["score"]
        for item in results
    }

    result = evaluate_scores(scores)

    result["ok_score"] = round(
        scores.get("OK", 0.0),
        4
    )

    return result
