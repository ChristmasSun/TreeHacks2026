"""
Quiz Generator Service
Generates quiz questions from lecture concepts using GPT-5.2/Cerebras.
Maps questions to corresponding Manim explainer videos.
"""
import os
import json
import re
import uuid
import logging
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field
from datetime import datetime
import httpx

logger = logging.getLogger(__name__)

# Prompt template path
PROMPTS_DIR = Path(__file__).parent.parent.parent / "prompts"


@dataclass
class QuizQuestion:
    """A single quiz question"""
    id: str
    concept: str
    question_text: str
    options: list[str]
    correct_answer: str  # "A", "B", "C", or "D"
    explanation: str
    video_path: Optional[str] = None


@dataclass
class Quiz:
    """A complete quiz with multiple questions"""
    id: str
    topic: str
    questions: list[QuizQuestion]
    created_at: datetime = field(default_factory=datetime.utcnow)


def read_prompt(filename: str) -> str:
    """Read a prompt template file."""
    return (PROMPTS_DIR / filename).read_text(encoding="utf-8")


async def call_llm_for_quiz(prompt: str, temperature: float = 0.4) -> str:
    """
    Call LLM for quiz generation.
    Tries Cerebras first (fast), then falls back to OpenAI.
    """
    # Try Cerebras first
    cerebras_key = os.getenv("CEREBRAS_API_KEY")
    if cerebras_key:
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "https://api.cerebras.ai/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {cerebras_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "llama-3.3-70b",
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": 500,
                        "temperature": temperature
                    }
                )
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"]
        except Exception as e:
            logger.warning(f"Cerebras failed, trying OpenAI: {e}")

    # Fall back to OpenAI
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {openai_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "gpt-4-turbo-preview",
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": 500,
                        "temperature": temperature
                    }
                )
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"OpenAI also failed: {e}")
            raise

    raise ValueError("No LLM API key available (CEREBRAS_API_KEY or OPENAI_API_KEY)")


async def generate_single_question(
    concept: str,
    description: str,
    video_path: Optional[str] = None
) -> QuizQuestion:
    """
    Generate a single quiz question for a concept.

    Args:
        concept: The concept name
        description: Description of the concept
        video_path: Optional path to the explainer video

    Returns:
        A QuizQuestion object
    """
    template = read_prompt("generate_quiz.txt")
    prompt = template.format(concept=concept, description=description)

    response = await call_llm_for_quiz(prompt)

    # Parse JSON from response
    json_match = re.search(r"\{.*\}", response, re.DOTALL)
    if not json_match:
        raise ValueError(f"Failed to parse quiz question JSON from LLM response: {response[:200]}")

    try:
        data = json.loads(json_match.group(0))
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in LLM response: {e}")

    question_id = str(uuid.uuid4())[:8]

    return QuizQuestion(
        id=question_id,
        concept=concept,
        question_text=data["question"],
        options=data["options"],
        correct_answer=data["correct_answer"].upper(),
        explanation=data["explanation"],
        video_path=video_path
    )


def load_concept_video_mapping(output_dir: str) -> dict[str, dict]:
    """
    Load concept-to-video mapping from render results.

    Args:
        output_dir: Directory containing scene_plan.json and render_results.json

    Returns:
        Dict mapping concept name to {description, video_path}
    """
    output_path = Path(output_dir)

    scene_plan_path = output_path / "scene_plan.json"
    render_results_path = output_path / "render_results.json"

    if not scene_plan_path.exists():
        logger.warning(f"scene_plan.json not found in {output_dir}")
        return {}

    with open(scene_plan_path) as f:
        scene_plan = json.load(f)

    # Load render results if available
    video_paths = {}
    if render_results_path.exists():
        with open(render_results_path) as f:
            results = json.load(f)
            for result in results:
                if result.get("success"):
                    idx = result.get("index", 0)
                    video_paths[idx] = result.get("path") or result.get("silent_path")

    # Build mapping
    mapping = {}
    for idx, scene in enumerate(scene_plan):
        concept = scene.get("concept", f"Concept {idx + 1}")
        mapping[concept] = {
            "description": scene.get("description", ""),
            "transcript_excerpt": scene.get("transcript_excerpt", ""),
            "video_path": video_paths.get(idx)
        }

    return mapping


async def generate_quiz_from_concepts(
    concepts: list[dict],
    num_questions: Optional[int] = None,
    topic: str = "Lecture Quiz"
) -> Quiz:
    """
    Generate a quiz from a list of concepts.

    Args:
        concepts: List of dicts with {concept, description, video_path?}
        num_questions: Number of questions to generate (defaults to len(concepts))
        topic: Quiz topic name

    Returns:
        A Quiz object with generated questions
    """
    if num_questions is None:
        num_questions = min(len(concepts), 5)  # Default max 5 questions

    # Select concepts for questions
    selected = concepts[:num_questions]

    questions = []
    for concept_data in selected:
        try:
            question = await generate_single_question(
                concept=concept_data.get("concept", "Unknown"),
                description=concept_data.get("description", ""),
                video_path=concept_data.get("video_path")
            )
            questions.append(question)
            logger.info(f"Generated question for concept: {concept_data.get('concept')}")
        except Exception as e:
            logger.error(f"Failed to generate question for {concept_data.get('concept')}: {e}")

    if not questions:
        raise ValueError("Failed to generate any quiz questions")

    return Quiz(
        id=str(uuid.uuid4())[:8],
        topic=topic,
        questions=questions
    )


async def generate_quiz_from_output_dir(
    output_dir: str,
    num_questions: Optional[int] = None,
    topic: Optional[str] = None
) -> Quiz:
    """
    Generate a quiz from Manim pipeline output directory.

    Args:
        output_dir: Path to pipeline output (containing scene_plan.json)
        num_questions: Number of questions to generate
        topic: Quiz topic (defaults to directory name)

    Returns:
        A Quiz object
    """
    mapping = load_concept_video_mapping(output_dir)

    if not mapping:
        raise ValueError(f"No concepts found in {output_dir}")

    concepts = [
        {
            "concept": name,
            "description": data["description"],
            "video_path": data.get("video_path")
        }
        for name, data in mapping.items()
    ]

    if topic is None:
        topic = Path(output_dir).name

    return await generate_quiz_from_concepts(
        concepts=concepts,
        num_questions=num_questions,
        topic=topic
    )


async def generate_follow_up_question(
    concept: str,
    description: str,
    previous_question: str,
    video_path: Optional[str] = None
) -> QuizQuestion:
    """
    Generate a follow-up question after student watched explainer video.

    Args:
        concept: The concept to test again
        description: Concept description
        previous_question: The question they got wrong
        video_path: Path to video (for reference)

    Returns:
        A new QuizQuestion
    """
    prompt = f"""You are an expert educational quiz designer. The student just watched an explainer video about a concept they struggled with. Generate a follow-up question to verify their understanding.

CONCEPT: {concept}
DESCRIPTION: {description}
PREVIOUS QUESTION THEY GOT WRONG: {previous_question}

Create ONE new multiple-choice question that:
- Tests the SAME concept but from a different angle
- Is slightly easier than the original question
- Focuses on the core understanding

Respond with ONLY valid JSON (no markdown, no code fences):
{{
    "question": "Your follow-up question here?",
    "options": [
        "A) First option",
        "B) Second option",
        "C) Third option",
        "D) Fourth option"
    ],
    "correct_answer": "A",
    "explanation": "Brief explanation of why this is correct"
}}"""

    response = await call_llm_for_quiz(prompt)

    json_match = re.search(r"\{.*\}", response, re.DOTALL)
    if not json_match:
        raise ValueError(f"Failed to parse follow-up question JSON: {response[:200]}")

    data = json.loads(json_match.group(0))
    question_id = str(uuid.uuid4())[:8]

    return QuizQuestion(
        id=question_id,
        concept=concept,
        question_text=data["question"],
        options=data["options"],
        correct_answer=data["correct_answer"].upper(),
        explanation=data["explanation"],
        video_path=video_path
    )
