from pydantic import BaseModel, ConfigDict


class PlaceInfo(BaseModel):
    name: str
    category: str
    neighborhood: str
    genre_type: str
    rating: float | None = None
    budget_level: str | None = None
    budget_range_min: int | None = None
    budget_range_max: int | None = None
    phone: str | None = None
    notes: str | None = None
    work_hours: str | None = None


class AskRequest(BaseModel):
    question: str
    user_id: str | None = None


class AskResponse(BaseModel):
    answer: str
    conversation_id: str
    places_found: int
    places: list[PlaceInfo] = []


class FeedbackRequest(BaseModel):
    conversation_id: str
    rating: int
    corrected_answer: str | None = None


class StatsResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    total_places: int
    total_conversations: int
    model_path: str


class PreferencesCheckResponse(BaseModel):
    has_preferences: bool
    questions: list[dict] | None = None


class PreferencesSaveRequest(BaseModel):
    user_id: str
    answers: dict
