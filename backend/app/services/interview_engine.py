"""
Interview Engine
----------------
Orchestrates the full AI/ML pipeline for a single interview turn:

  Context Construction -> Knowledge Retrieval (RAG) -> Question Generation

and, on the answer side:

  Answer Evaluation -> Adaptive difficulty adjustment -> Final report synthesis
"""
import json
import random
import logging
from typing import Dict, List, Optional

from app.config import settings
from app.services import rag_engine
from app.services.llm_client import generate_json, generate_text

logger = logging.getLogger("interview_engine")


# ---------------------------------------------------------------------------
# Context Construction
# ---------------------------------------------------------------------------
def build_topic_queue(role_key: str, candidate: Dict) -> List[str]:
    """
    Merge role-core topics with candidate-specific skills/technologies to
    produce a prioritized list of topics to probe. Candidate-specific
    technologies are interleaved with core topics so the interview
    reflects both the role's expectations and the candidate's background.
    """
    role_cfg = settings.ROLE_CONFIG[role_key]
    core_topics = list(role_cfg["core_topics"])
    candidate_topics = list(dict.fromkeys(candidate.get("technologies", []) + candidate.get("skills", [])))

    random.shuffle(candidate_topics)
    queue: List[str] = []
    ci, ti = 0, 0
    while len(queue) < settings.MAX_QUESTIONS and (ci < len(core_topics) or ti < len(candidate_topics)):
        if ci < len(core_topics):
            queue.append(core_topics[ci])
            ci += 1
        if len(queue) < settings.MAX_QUESTIONS and ti < len(candidate_topics):
            queue.append(candidate_topics[ti])
            ti += 1
    return queue[: settings.MAX_QUESTIONS]


def build_retrieval_query(topic: str, role_label: str, candidate: Dict) -> str:
    """Generate a meaningful, grounded query to hit the knowledge base with."""
    skill_hint = ", ".join(candidate.get("technologies", [])[:3])
    return f"{topic} in the context of a {role_label} role, relevant to experience with {skill_hint}"


# ---------------------------------------------------------------------------
# Question Generation
# ---------------------------------------------------------------------------
QUESTION_PROMPT = """You are a senior technical interviewer conducting a live interview for the role of {role_label}.

Candidate background:
- Skills: {skills}
- Technologies: {technologies}
- Domain exposure: {domains}

Topic to probe: "{topic}"
Difficulty level to target: {difficulty}

Grounding reference material (retrieved from a role-specific knowledge base):
---
{context}
---

Write ONE interview question that:
- Is clearly relevant to the "{topic}" topic and the {role_label} role
- Is calibrated to the "{difficulty}" difficulty level
- Where natural, connects to the candidate's stated background
- Tests conceptual understanding and/or applied/practical judgment (not just a definition)
- Is answerable in a few sentences (not a multi-part essay)

Return ONLY JSON: {{"question": "..."}}
"""

FALLBACK_QUESTIONS = {
    "easy": "Can you explain, in your own words, what {topic} means and why it matters for a {role_label}?",
    "medium": "Describe a situation where you'd apply {topic} in a real {role_label} project. What trade-offs would you consider?",
    "hard": "Walk me through how you would design around a failure or limitation related to {topic} in a production {role_label} system.",
}


def generate_question(role_key: str, topic: str, difficulty: str, candidate: Dict) -> Dict:
    role_label = settings.ROLE_CONFIG[role_key]["label"]
    query = build_retrieval_query(topic, role_label, candidate)
    context_chunks = rag_engine.retrieve_context(role_key, query)
    context_text = "\n\n".join(context_chunks) if context_chunks else "(no additional reference material retrieved)"

    llm_result = generate_json(
        QUESTION_PROMPT.format(
            role_label=role_label,
            skills=", ".join(candidate.get("skills", [])) or "n/a",
            technologies=", ".join(candidate.get("technologies", [])) or "n/a",
            domains=", ".join(candidate.get("domains", [])) or "n/a",
            topic=topic,
            difficulty=difficulty,
            context=context_text[:3000],
        )
    )

    if llm_result and llm_result.get("question"):
        question_text = llm_result["question"].strip()
    else:
        question_text = FALLBACK_QUESTIONS[difficulty].format(topic=topic, role_label=role_label)

    return {
        "question_text": question_text,
        "topic": topic,
        "difficulty": difficulty,
        "retrieved_context": context_chunks,
    }


# ---------------------------------------------------------------------------
# Answer Evaluation + Adaptivity
# ---------------------------------------------------------------------------
EVAL_PROMPT = """You are grading a candidate's interview answer for a {role_label} position.

Question: {question}
Candidate's answer: {answer}

Reference material the question was grounded in:
---
{context}
---

Score the answer from 0 to 10 on correctness, depth, and clarity.
Also give 1-2 sentences of constructive feedback.

Return ONLY JSON: {{"score": <number 0-10>, "feedback": "..."}}
"""


def evaluate_answer(role_key: str, question_text: str, answer_text: str, context_chunks: List[str]) -> Dict:
    role_label = settings.ROLE_CONFIG[role_key]["label"]
    context_text = "\n\n".join(context_chunks) if context_chunks else "(none)"

    llm_result = generate_json(
        EVAL_PROMPT.format(
            role_label=role_label,
            question=question_text,
            answer=answer_text,
            context=context_text[:3000],
        )
    )

    if llm_result and "score" in llm_result:
        try:
            score = max(0.0, min(10.0, float(llm_result["score"])))
        except (TypeError, ValueError):
            score = 5.0
        feedback = str(llm_result.get("feedback", "")).strip() or "No specific feedback generated."
    else:
        # Deterministic, honest fallback if the LLM is unreachable.
        score = 5.0 if len(answer_text.split()) > 15 else 2.5
        feedback = "Automated fallback scoring used (LLM unavailable) — based on response length/effort only."

    return {"score": score, "feedback": feedback}


def next_difficulty(current_difficulty: str, last_score: Optional[float]) -> str:
    """Simple adaptive rule: strong answers escalate difficulty, weak ones ease off."""
    if last_score is None:
        return "medium"
    order = ["easy", "medium", "hard"]
    idx = order.index(current_difficulty) if current_difficulty in order else 1
    if last_score >= 7.5 and idx < 2:
        idx += 1
    elif last_score < 4.0 and idx > 0:
        idx -= 1
    return order[idx]


# ---------------------------------------------------------------------------
# Final Report Synthesis
# ---------------------------------------------------------------------------
REPORT_PROMPT = """You are summarizing a completed technical interview for a {role_label} candidate.

Here is the full question/answer/score transcript:
{transcript}

Produce a structured assessment. Return ONLY JSON with keys:
{{
  "strengths": ["...", "..."],
  "weaknesses": ["...", "..."],
  "summary_text": "2-4 sentence overall narrative summary"
}}
"""


def synthesize_report(role_key: str, qa_pairs: List[Dict]) -> Dict:
    role_label = settings.ROLE_CONFIG[role_key]["label"]
    transcript_lines = []
    scores = []
    topics_covered = []
    for qa in qa_pairs:
        transcript_lines.append(
            f"Q ({qa['topic']}, {qa['difficulty']}): {qa['question_text']}\n"
            f"A: {qa['answer_text']}\nScore: {qa['evaluation_score']}\n"
        )
        if qa.get("evaluation_score") is not None:
            scores.append(qa["evaluation_score"])
        if qa.get("topic"):
            topics_covered.append(qa["topic"])

    overall_score = round(sum(scores) / len(scores), 2) if scores else None
    transcript_text = "\n".join(transcript_lines)

    llm_result = generate_json(
        REPORT_PROMPT.format(role_label=role_label, transcript=transcript_text[:6000])
    )

    if llm_result:
        strengths = llm_result.get("strengths", [])
        weaknesses = llm_result.get("weaknesses", [])
        summary_text = llm_result.get("summary_text", "")
    else:
        strengths = [t for qa, t in zip(qa_pairs, topics_covered) if (qa.get("evaluation_score") or 0) >= 6]
        weaknesses = [t for qa, t in zip(qa_pairs, topics_covered) if (qa.get("evaluation_score") or 0) < 6]
        summary_text = (
            f"Candidate answered {len(qa_pairs)} questions for the {role_label} role "
            f"with an average score of {overall_score if overall_score is not None else 'N/A'}/10. "
            "(Generated via fallback summarizer — LLM unavailable.)"
        )

    return {
        "overall_score": overall_score,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "topic_coverage": list(dict.fromkeys(topics_covered)),
        "summary_text": summary_text,
    }
