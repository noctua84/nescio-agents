import sys
from typing import TypedDict

from sqlalchemy import func, select

from src.clients.embedding import get_embedding, to_vector
from src.db import session_scope
from src.models import ReferenceLibrary


class SeedExample(TypedDict):
    prompt: str
    tier: int
    confidence: float
    source: str


# Seed examples
seed_examples: list[SeedExample] = [
    # Tier 1: Simple
    {"prompt": "Write a regex to match email addresses", "tier": 1, "confidence": 0.95, "source": "curated"},
    {"prompt": "Create a Python function to calculate factorial", "tier": 1, "confidence": 0.95, "source": "curated"},
    {"prompt": "Explain what a hash map is in one sentence", "tier": 1, "confidence": 0.90, "source": "curated"},
    {"prompt": "Generate a UUID in JavaScript", "tier": 1, "confidence": 0.95, "source": "curated"},
    {
        "prompt": "Write a bash command to list all running Docker containers",
        "tier": 1,
        "confidence": 0.90,
        "source": "curated",
    },
    # Tier 2: Medium
    {
        "prompt": "Refactor this function to use async/await instead of callbacks",
        "tier": 2,
        "confidence": 0.90,
        "source": "curated",
    },
    {
        "prompt": "Debug this stack trace and explain what's causing the error",
        "tier": 2,
        "confidence": 0.85,
        "source": "curated",
    },
    {"prompt": "Write unit tests for this authentication module", "tier": 2, "confidence": 0.85, "source": "curated"},
    {"prompt": "Optimize this SQL query that's running slowly", "tier": 2, "confidence": 0.85, "source": "curated"},
    {
        "prompt": "Convert this synchronous code to use proper error handling",
        "tier": 2,
        "confidence": 0.80,
        "source": "curated",
    },
    # Tier 3: Complex
    {
        "prompt": "Analyze these three files and suggest an architectural refactor to improve separation of concerns",
        "tier": 3,
        "confidence": 0.95,
        "source": "curated",
    },
    {
        "prompt": "Design a caching strategy for this distributed system that handles cache invalidation correctly",
        "tier": 3,
        "confidence": 0.95,
        "source": "curated",
    },
    {
        "prompt": "Migrate this codebase from REST to GraphQL while maintaining backward compatibility",
        "tier": 3,
        "confidence": 0.90,
        "source": "curated",
    },
    {
        "prompt": "Implement a custom authentication system with JWT tokens and refresh token rotation",
        "tier": 3,
        "confidence": 0.90,
        "source": "curated",
    },
    {
        "prompt": "Design a database schema for a multi-tenant SaaS application with proper isolation",
        "tier": 3,
        "confidence": 0.95,
        "source": "curated",
    },
]


def seed_database() -> None:
    with session_scope() as db:
        existing = db.scalar(
            select(func.count()).select_from(ReferenceLibrary).where(ReferenceLibrary.source == "curated")
        )

        if existing:
            print(f"Aborting: {existing} curated rows already present. Clear them first if you mean to re-seed.")
            sys.exit(1)

        curated = [e for e in seed_examples if e["source"] == "curated"]
        embeddings = [get_embedding(e["prompt"]) for e in curated]

        db.add_all(
            [
                ReferenceLibrary(
                    prompt_text=ex["prompt"],
                    embedding=to_vector(e),
                    tier=ex["tier"],
                    source=ex["source"],
                    confidence=ex["confidence"],
                )
                for ex, e in zip(curated, embeddings, strict=True)
            ]
        )

        print(f"Successfully seeded {len(curated)} examples")


if __name__ == "__main__":
    seed_database()
