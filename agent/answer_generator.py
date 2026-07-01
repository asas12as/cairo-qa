import re

ANSWER_SYSTEM = """You are a Cairo travel assistant. You have a database of places (restaurants, hotels, attractions, cafes) in Cairo.

User's taste profile:
{user_prefs}

Rules:
- **Place questions** (specific restaurant, hotel, attraction, cafe, museum, etc.): Answer ONLY from "Available places" below. Never invent places. Format: Name  ★★★★☆  Neighborhood · Price
- **Plan/itinerary requests** (trip plan, itinerary, schedule, رحلة, خطة): Do NOT try to build a plan yourself. Instead, ask the user for their total budget and number of days so the system can generate a proper plan. Say something like: "I can build you a plan! How much is your total budget and for how many days?"
- **Clearly off-topic** (math, coding, politics): Redirect to Cairo travel.
- **Gray area** (greetings, weather, chit-chat): Respond in a travel context — mention Cairo or a relevant place.

If no places match, say so and suggest related categories. Consider the user's taste profile."""  # noqa: E501


class AnswerGenerator:
    def __init__(self, llm):
        self.llm = llm

    _TRAVEL_KW = {"place", "restaurant", "hotel", "cafe", "attraction", "museum", "eat", "stay",
                   "visit", "recommend", "budget", "cost", "price", "good", "best", "near",
                   "downtown", "zamalek", "maadi", "garden city", "cairo"}
    _PLAN_KW = {"plan", "itinerary", "trip", "schedule", "tour", "رحلة", "خطة", "برنامج"}

    def _profile_text(self, profile: dict | None) -> str:
        if not profile:
            return "No preferences saved — treat as a general traveler."
        lines = [
            f"- Traveler type: {profile.get('traveler_type', 'general')}",
            f"- Daily budget level: {profile.get('budget_level', 'mid-range')}",
            f"- Atmosphere preference: {profile.get('vibe', 'balanced')}",
        ]
        return "\n".join(lines)

    def _history_text(self, history: list[dict] | None) -> str:
        if not history:
            return ""
        lines = []
        for h in history[-4:]:
            lines.append(f"User: {h['question']}")
            lines.append(f"Assistant: {h['answer'][:200]}")
        return "\n".join(lines)

    def generate(self, question: str, context_rows: list[dict], profile: dict | None = None, history: list[dict] | None = None, companion_context: str = "") -> str:
        context_text = self._format_context(context_rows) if context_rows else "No matching places found in database."
        system = ANSWER_SYSTEM.format(user_prefs=self._profile_text(profile))
        if companion_context:
            system += f"\n\n{companion_context}\nWhen suggesting places, try to find options that work well for everyone in the group."
        conv_history = self._history_text(history)
        user_content = f"Available places:\n{context_text}\n\nConversation history:\n{conv_history}\n\nQuestion: {question}" if conv_history else f"Available places:\n{context_text}\n\nQuestion: {question}"
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user_content},
        ]
        answer = self.llm.chat(messages, max_tokens=300, temperature=0.2)
        if context_rows and self._is_place_query(question) and not self._is_plan_query(question):
            answer = self._validate_answer(answer, context_rows)
        return answer

    def generate_stream(self, question: str, context_rows: list[dict], profile: dict | None = None, history: list[dict] | None = None, companion_context: str = ""):
        context_text = self._format_context(context_rows) if context_rows else "No matching places found in database."
        system = ANSWER_SYSTEM.format(user_prefs=self._profile_text(profile))
        if companion_context:
            system += f"\n\n{companion_context}\nWhen suggesting places, try to find options that work well for everyone in the group."
        conv_history = self._history_text(history)
        user_content = f"Available places:\n{context_text}\n\nConversation history:\n{conv_history}\n\nQuestion: {question}" if conv_history else f"Available places:\n{context_text}\n\nQuestion: {question}"
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user_content},
        ]
        full_answer = ""
        for token in self.llm.chat_stream(messages, max_tokens=300, temperature=0.2):
            full_answer += token
            yield token

        if context_rows and self._is_place_query(question) and not self._is_plan_query(question):
            self._validate_answer(full_answer, context_rows)

    def _is_plan_query(self, question: str) -> bool:
        q = question.lower()
        return any(kw in q for kw in self._PLAN_KW)

    def _is_place_query(self, question: str) -> bool:
        q = question.lower()
        return any(kw in q for kw in self._TRAVEL_KW)

    def _validate_answer(self, answer: str, context_rows: list[dict]) -> str:
        valid_names = {r.get("name", "").lower() for r in context_rows}
        answer_lower = answer.lower()
        for name in valid_names:
            if name and len(name) > 3 and name in answer_lower:
                return answer
        return "I don't have places matching that in my database."

    def _format_context(self, rows: list[dict]) -> str:
        lines = []
        for i, r in enumerate(rows, 1):
            parts = [
                f"Name: {r.get('name', 'N/A')}",
                f"Category: {r.get('category', 'N/A')}",
                f"Neighborhood: {r.get('neighborhood', 'N/A')}",
                f"Genre: {r.get('genre_type', 'N/A')}",
                f"Rating: {r.get('rating', 'N/A')}",
                f"Budget Level: {r.get('budget_level', 'N/A')}",
            ]
            desc = r.get("notes", "")
            if desc:
                parts.append(f"Notes: {desc}")
            lines.append(f"{i}. {' | '.join(parts)}")
        return "\n".join(lines)
