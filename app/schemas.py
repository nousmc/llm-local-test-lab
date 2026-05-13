from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ConfiguredModelSchema(BaseModel):
    id: str
    label: str
    provider: str
    model_name: str
    enabled: bool = True
    family: Optional[str] = None
    size_b: Optional[int] = None
    context_window: Optional[int] = None
    supports_vision: bool = False
    supports_json: bool = False
    default_params_json: str = "{}"

    model_config = {"from_attributes": True}


class TestTypeSchema(BaseModel):
    id: str
    label: str
    description: Optional[str] = None
    expected_schema: Optional[str] = None
    enabled: bool = True

    model_config = {"from_attributes": True}


class TestCaseCreate(BaseModel):
    test_type_id: str
    title: str
    library_id: Optional[str] = None
    description: Optional[str] = None
    input_text: Optional[str] = None
    context_text: Optional[str] = None
    system_prompt: Optional[str] = None
    user_prompt_template: Optional[str] = None
    rules: Optional[str] = None
    expected_output_json: Optional[str] = None
    expected_text: Optional[str] = None
    expected_labels_json: Optional[str] = None
    rubric_json: Optional[str] = None
    tags_json: Optional[str] = None
    difficulty: str = "medium"
    risk_level: str = "low"
    enabled: bool = True


class TestCaseUpdate(BaseModel):
    test_type_id: Optional[str] = None
    title: Optional[str] = None
    library_id: Optional[str] = None
    description: Optional[str] = None
    input_text: Optional[str] = None
    context_text: Optional[str] = None
    system_prompt: Optional[str] = None
    user_prompt_template: Optional[str] = None
    rules: Optional[str] = None
    expected_output_json: Optional[str] = None
    expected_text: Optional[str] = None
    expected_labels_json: Optional[str] = None
    rubric_json: Optional[str] = None
    tags_json: Optional[str] = None
    difficulty: Optional[str] = None
    risk_level: Optional[str] = None
    enabled: Optional[bool] = None


class TestCaseOut(BaseModel):
    id: int
    test_type_id: str
    library_id: Optional[str] = None
    title: str
    description: Optional[str] = None
    input_text: Optional[str] = None
    input_file_path: Optional[str] = None
    context_text: Optional[str] = None
    system_prompt: Optional[str] = None
    user_prompt_template: Optional[str] = None
    rules: Optional[str] = None
    expected_output_json: Optional[str] = None
    expected_text: Optional[str] = None
    expected_labels_json: Optional[str] = None
    rubric_json: Optional[str] = None
    tags_json: Optional[str] = None
    difficulty: str = "medium"
    risk_level: str = "low"
    enabled: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class TestRunCreate(BaseModel):
    name: str
    description: Optional[str] = None
    selected_model_ids: list[str] = []
    selected_test_case_ids: list[int] = []
    parallelism: int = 2
    retry_attempts: int = 2
    pass_threshold: float = 0.80


class TestRunOut(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    status: str = "created"
    selected_model_ids_json: str = "[]"
    selected_test_case_ids_json: str = "[]"
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class TestResultOut(BaseModel):
    id: int
    test_run_id: int
    test_case_id: int
    model_id: str
    provider: str
    model_name: str
    prompt_text: Optional[str] = None
    response_text: Optional[str] = None
    response_json: Optional[str] = None
    raw_response_json: Optional[str] = None
    error_message: Optional[str] = None
    error_type: Optional[str] = None
    latency_ms: Optional[float] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    tokens_per_second: Optional[float] = None
    estimated_cost: Optional[float] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    status: str = "pending"

    model_config = {"from_attributes": True}


class ValidationResultOut(BaseModel):
    id: int
    test_result_id: int
    validator_provider: Optional[str] = None
    validator_model: Optional[str] = None
    score: Optional[float] = None
    passed: Optional[bool] = None
    faithfulness_score: Optional[float] = None
    format_score: Optional[float] = None
    semantic_score: Optional[float] = None
    safety_score: Optional[float] = None
    completeness_score: Optional[float] = None
    error_score: Optional[float] = None
    hallucination_detected: bool = False
    refusal_detected: bool = False
    validation_json: Optional[str] = None
    validation_text: Optional[str] = None

    model_config = {"from_attributes": True}


class ReportOut(BaseModel):
    id: int
    test_run_id: int
    title: Optional[str] = None
    summary_text: Optional[str] = None
    findings_json: Optional[str] = None
    chart_payload_json: Optional[str] = None
    html_path: Optional[str] = None
    json_path: Optional[str] = None
    csv_path: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class PromptPreviewRequest(BaseModel):
    test_type_id: str
    title: str = ""
    description: str = ""
    input_text: str = ""
    context_text: str = ""
    system_prompt: str = ""
    custom_rules: str = ""
    expected_output_json: str = ""


class PromptPreviewResponse(BaseModel):
    prompt: str
    valid: bool
    issues: list[str]
    warnings: list[str]
    checks: dict
    expected_schema_preview: dict
    status: str = "valid"


class ProbeResponse(BaseModel):
    success: bool
    response: str
    latency_ms: float
    error: Optional[str] = None


class DashboardStats(BaseModel):
    total_models: int
    enabled_models: int
    total_test_cases: int
    total_runs: int
    completed_runs: int
    avg_score: float
    best_model: Optional[str] = None
    error_rate: float
    avg_latency: float
