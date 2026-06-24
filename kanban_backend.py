"""
AI Kanban Board - Flask Backend
Provides AI-powered task analysis, categorization, and productivity insights.
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import os
import anthropic
from datetime import datetime, timedelta
import random

# Load .env locally if python-dotenv is available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

app = Flask(__name__)
CORS(app, origins=["*", "http://127.0.0.1:7000"])

api_key = "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"
if not api_key:
    raise RuntimeError("ANTHROPIC_API_KEY environment variable is not set.")

client = anthropic.Anthropic(api_key=api_key)

# ─── In-memory store (replace with DB in production) ─────────────────────────
_store = {
    "columns": [
        {"id": "backlog",     "title": "Backlog",      "color": "#7F77DD"},
        {"id": "todo",        "title": "To Do",        "color": "#1D9E75"},
        {"id": "in_progress", "title": "In Progress",  "color": "#BA7517"},
        {"id": "review",      "title": "Review",       "color": "#378ADD"},
        {"id": "done",        "title": "Done",         "color": "#639922"},
    ],
    "tasks": [
        {
            "id": "t1", "column": "todo", "title": "Design system tokens",
            "description": "Create unified color and spacing tokens for the design system",
            "priority": "high", "category": "Design", "assignee": "AO",
            "estimate_hours": 4, "created_at": "2025-01-20",
            "sentiment": "neutral", "tags": ["design", "frontend"]
        },
        {
            "id": "t2", "column": "in_progress", "title": "API rate limiting",
            "description": "Implement rate limiting middleware for all public endpoints",
            "priority": "critical", "category": "Backend", "assignee": "MK",
            "estimate_hours": 6, "created_at": "2025-01-19",
            "sentiment": "urgent", "tags": ["backend", "security"]
        },
        {
            "id": "t3", "column": "review", "title": "User onboarding flow",
            "description": "Build step-by-step onboarding wizard for new users",
            "priority": "medium", "category": "Product", "assignee": "SL",
            "estimate_hours": 8, "created_at": "2025-01-18",
            "sentiment": "positive", "tags": ["ux", "onboarding"]
        },
        {
            "id": "t4", "column": "backlog", "title": "Mobile push notifications",
            "description": "Add push notification support for mobile app",
            "priority": "low", "category": "Mobile", "assignee": "",
            "estimate_hours": 12, "created_at": "2025-01-17",
            "sentiment": "neutral", "tags": ["mobile"]
        },
        {
            "id": "t5", "column": "done", "title": "Database indexing",
            "description": "Add indexes to frequently queried columns",
            "priority": "high", "category": "Backend", "assignee": "AO",
            "estimate_hours": 3, "created_at": "2025-01-16",
            "sentiment": "positive", "tags": ["database", "performance"]
        },
        {
            "id": "t6", "column": "todo", "title": "Accessibility audit",
            "description": "Run WCAG 2.1 audit and fix all level A/AA violations",
            "priority": "medium", "category": "Quality", "assignee": "SL",
            "estimate_hours": 5, "created_at": "2025-01-20",
            "sentiment": "neutral", "tags": ["a11y", "frontend"]
        },
    ]
}

# ─── Routes ──────────────────────────────────────────────────────────────────

@app.route("/api/board", methods=["GET"])
def get_board():
    """Return full board state."""
    return jsonify(_store)


@app.route("/api/tasks", methods=["POST"])
def create_task():
    """Create a new task."""
    data = request.json
    task_id = f"t{len(_store['tasks']) + 1}_{random.randint(100,999)}"
    task = {
        "id": task_id,
        "column": data.get("column", "backlog"),
        "title": data.get("title", "Untitled"),
        "description": data.get("description", ""),
        "priority": data.get("priority", "medium"),
        "category": data.get("category", "General"),
        "assignee": data.get("assignee", ""),
        "estimate_hours": data.get("estimate_hours", 0),
        "created_at": datetime.now().strftime("%Y-%m-%d"),
        "sentiment": "neutral",
        "tags": data.get("tags", [])
    }
    _store["tasks"].append(task)
    return jsonify(task), 201


@app.route("/api/tasks/<task_id>", methods=["PATCH"])
def update_task(task_id):
    """Update a task (including column for drag-and-drop)."""
    data = request.json
    for task in _store["tasks"]:
        if task["id"] == task_id:
            task.update(data)
            return jsonify(task)
    return jsonify({"error": "Task not found"}), 404


@app.route("/api/tasks/<task_id>", methods=["DELETE"])
def delete_task(task_id):
    """Delete a task."""
    before = len(_store["tasks"])
    _store["tasks"] = [t for t in _store["tasks"] if t["id"] != task_id]
    if len(_store["tasks"]) < before:
        return jsonify({"deleted": task_id})
    return jsonify({"error": "Task not found"}), 404


@app.route("/api/ai/analyze", methods=["POST"])
def ai_analyze_task():
    """
    AI-powered task analysis:
    - Category detection
    - Priority suggestion
    - Estimated completion time
    - Sentiment analysis
    - Smart tags
    """
    data = request.json
    title = data.get("title", "")
    description = data.get("description", "")

    prompt = f"""Analyze this software project task and respond ONLY with a JSON object (no markdown, no explanation):

Task title: {title}
Task description: {description}

Return exactly this JSON structure:
{{
  "category": "one of: Frontend, Backend, Mobile, Design, DevOps, QA, Product, Data, Security, Documentation",
  "priority": "one of: low, medium, high, critical",
  "estimate_hours": <integer 1-40>,
  "sentiment": "one of: positive, neutral, urgent, blocked, unclear",
  "confidence": <float 0.0-1.0>,
  "tags": ["tag1", "tag2"],
  "reasoning": "one sentence explanation",
  "risks": "one sentence about main risk or empty string",
  "suggested_assignee_role": "e.g. Frontend Engineer, Backend Engineer, Designer"
}}"""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}]
        )
        text = response.content[0].text.strip()
        # Strip any markdown fences
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        result = json.loads(text)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/ai/insights", methods=["GET"])
def ai_insights():
    """
    Generate productivity insights for the whole board.
    """
    tasks = _store["tasks"]
    columns = _store["columns"]

    # Build summary stats
    col_counts = {c["id"]: 0 for c in columns}
    priority_counts = {"low": 0, "medium": 0, "high": 0, "critical": 0}
    category_counts = {}
    total_hours = 0
    blocked_tasks = []

    for t in tasks:
        col_counts[t["column"]] = col_counts.get(t["column"], 0) + 1
        priority_counts[t.get("priority", "medium")] = priority_counts.get(t.get("priority", "medium"), 0) + 1
        cat = t.get("category", "General")
        category_counts[cat] = category_counts.get(cat, 0) + 1
        total_hours += t.get("estimate_hours", 0)
        if t.get("sentiment") in ("blocked", "urgent"):
            blocked_tasks.append(t["title"])

    board_summary = f"""
Board snapshot:
- {len(tasks)} total tasks across {len(columns)} columns
- Column distribution: {json.dumps(col_counts)}
- Priority distribution: {json.dumps(priority_counts)}
- Category distribution: {json.dumps(category_counts)}
- Total estimated hours: {total_hours}
- Urgent/blocked tasks: {blocked_tasks}
- WIP (in_progress) count: {col_counts.get('in_progress', 0)}
"""

    prompt = f"""You are a project management AI. Analyze this Kanban board and provide actionable insights.

{board_summary}

Respond ONLY with a JSON object (no markdown):
{{
  "health_score": <integer 0-100>,
  "health_label": "one of: Critical, At Risk, Fair, Good, Excellent",
  "velocity_estimate": <integer hours per week the team can handle>,
  "bottleneck": "one sentence identifying the biggest bottleneck",
  "top_recommendation": "one concrete action to take today",
  "recommendations": ["rec1", "rec2", "rec3"],
  "wip_warning": true or false,
  "predicted_completion_days": <integer days to clear current backlog>,
  "team_utilization": <integer 0-100>,
  "focus_area": "the category needing most attention"
}}"""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}]
        )
        text = response.content[0].text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        result = json.loads(text)
        # Attach raw stats for the frontend charts
        result["stats"] = {
            "col_counts": col_counts,
            "priority_counts": priority_counts,
            "category_counts": category_counts,
            "total_hours": total_hours,
            "total_tasks": len(tasks)
        }
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/ai/chat", methods=["POST"])
def ai_chat():
    """General AI chat about the board."""
    data = request.json
    message = data.get("message", "")
    tasks = _store["tasks"]

    task_summary = "\n".join(
        f"- [{t['column']}] {t['title']} ({t.get('priority','?')} priority, {t.get('category','?')})"
        for t in tasks
    )

    prompt = f"""You are an AI assistant for a Kanban project management board. 
Current board tasks:
{task_summary}

User question: {message}

Give a concise, helpful response (2-4 sentences max). Focus on actionable advice."""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}]
        )
        return jsonify({"reply": response.content[0].text.strip()})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    print("🚀 AI Kanban Backend running on http://localhost:5000")
    app.run(debug=True, port=5000)
