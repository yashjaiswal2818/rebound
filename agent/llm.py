"""
Rebound LLM Interface
Supports Google Gemini (including Flash-Lite and 2.0 Flash) with zero external SDKs.
Enforces strict JSON schema validation, anti-hallucination sanitization,
and instant graceful fallback to the deterministic policy engine.
"""

import json
import logging
import os
from typing import Dict, List, Optional, Tuple

import httpx
from dotenv import load_dotenv

load_dotenv()

from agent.models import FlightOffer, TravelerProfile
from agent.policy import fallback_rank_offers
from agent.prompts import (
    RANKING_SYSTEM_PROMPT,
    format_ranking_user_prompt,
    parse_ranking_response,
)

logger = logging.getLogger("rebound.llm")


def call_gemini_ranking(
    survivors: List[FlightOffer],
    profile: TravelerProfile,
    deadline_iso: str,
    original_order_total: float,
) -> Tuple[List[FlightOffer], Dict[str, str]]:
    """
    Calls Google Gemini (e.g. gemini-2.0-flash-lite or gemini-2.0-flash) to rank flight options.
    If GEMINI_API_KEY is not configured or if any error/timeout occurs,
    gracefully falls back to the deterministic heuristic sorter.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        fallback_sorted = fallback_rank_offers(survivors, profile, original_order_total)
        fallback_reasons = {
            o.id: f"Deterministic policy rank: arrives {o.arrives_at.strftime('%H:%M')}, delta +${o.total_amount - original_order_total:.2f}"
            for o in fallback_sorted
        }
        return (fallback_sorted, fallback_reasons)

    model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-lite")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

    user_prompt = format_ranking_user_prompt(
        survivors=survivors,
        profile=profile,
        deadline_iso=deadline_iso,
        original_order_total=original_order_total,
    )

    payload = {
        "system_instruction": {
            "parts": [{"text": RANKING_SYSTEM_PROMPT}]
        },
        "contents": [
            {
                "role": "user",
                "parts": [{"text": user_prompt}]
            }
        ],
        "generationConfig": {
            "temperature": 0.1,
            "responseMimeType": "application/json",
        },
    }

    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": api_key,
    }
    if api_key.startswith("AQ.") or api_key.startswith("ya29."):
        headers["Authorization"] = f"Bearer {api_key}"

    try:
        with httpx.Client(timeout=8.0) as client:
            resp = client.post(url, headers=headers, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                candidates = data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts:
                        raw_text = parts[0].get("text", "")
                        logger.info("Successfully ranked offers using Google Gemini (%s)", model)
                        return parse_ranking_response(
                            raw_response=raw_text,
                            survivors=survivors,
                            profile=profile,
                            original_order_total=original_order_total,
                        )
            else:
                logger.warning("Gemini HTTP %d: %s. Degrading to deterministic policy.", resp.status_code, resp.text)
    except Exception as e:
        logger.warning("Gemini call exception: %s. Degrading to deterministic policy.", e)

    # Fallback if Gemini unavailable or returned non-200
    fallback_sorted = fallback_rank_offers(survivors, profile, original_order_total)
    fallback_reasons = {
        o.id: f"Deterministic fallback: arrives {o.arrives_at.strftime('%H:%M')}, delta +${o.total_amount - original_order_total:.2f}"
        for o in fallback_sorted
    }
    return (fallback_sorted, fallback_reasons)

