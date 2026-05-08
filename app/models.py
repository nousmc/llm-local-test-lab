import json
from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, Text, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from .database import Base


class ProviderConfig(Base):
    __tablename__ = "provider_configs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=True, nullable=False)
    label = Column(String, nullable=False)
    base_url = Column(String, nullable=False)
    timeout_seconds = Column(Integer, default=180)
    enabled = Column(Boolean, default=True)
    app_name = Column(String, nullable=True)
    site_url = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class ValidatorConfig(Base):
    __tablename__ = "validator_config"

    id = Column(Integer, primary_key=True, autoincrement=True)
    enabled = Column(Boolean, default=False)
    provider = Column(String, nullable=False)
    model = Column(String, nullable=False)
    fallback_provider = Column(String, nullable=True)
    fallback_model = Column(String, nullable=True)
    validation_mode = Column(String, default="rubric_json")
    temperature = Column(Float, default=0.0)
    max_tokens = Column(Integer, default=2048)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class SecretConfig(Base):
    __tablename__ = "secret_configs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String, unique=True, nullable=False)
    value = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class TestLibrary(Base):
    __tablename__ = "test_libraries"

    id = Column(String, primary_key=True)
    label = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    domain = Column(String, nullable=True)
    enabled = Column(Boolean, default=True)
    tags_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    test_cases = relationship("TestCase", back_populates="library", cascade="save-update, merge")


class ConfiguredModel(Base):
    __tablename__ = "configured_models"

    id = Column(String, primary_key=True)
    label = Column(String, nullable=False)
    provider = Column(String, nullable=False)
    model_name = Column(String, nullable=False)
    enabled = Column(Boolean, default=True)
    family = Column(String, nullable=True)
    size_b = Column(Integer, nullable=True)
    context_window = Column(Integer, nullable=True)
    supports_vision = Column(Boolean, default=False)
    supports_json = Column(Boolean, default=False)
    default_params_json = Column(Text, default="{}")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class TestType(Base):
    __tablename__ = "test_types"

    id = Column(String, primary_key=True)
    label = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    expected_schema = Column(String, nullable=True)
    enabled = Column(Boolean, default=True)


class TestCase(Base):
    __tablename__ = "test_cases"

    id = Column(Integer, primary_key=True, autoincrement=True)
    test_type_id = Column(String, ForeignKey("test_types.id"), nullable=False)
    library_id = Column(String, ForeignKey("test_libraries.id"), nullable=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    input_text = Column(Text, nullable=True)
    input_file_path = Column(String, nullable=True)
    context_text = Column(Text, nullable=True)
    system_prompt = Column(Text, nullable=True)
    user_prompt_template = Column(Text, nullable=True)
    expected_output_json = Column(Text, nullable=True)
    expected_text = Column(Text, nullable=True)
    expected_labels_json = Column(Text, nullable=True)
    rubric_json = Column(Text, nullable=True)
    tags_json = Column(Text, nullable=True)
    difficulty = Column(String, default="medium")
    risk_level = Column(String, default="low")
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    test_type = relationship("TestType")
    library = relationship("TestLibrary", back_populates="test_cases")
    results = relationship("TestResult", back_populates="test_case", cascade="all, delete-orphan")


class TestRun(Base):
    __tablename__ = "test_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String, default="created")
    selected_model_ids_json = Column(Text, default="[]")
    selected_test_case_ids_json = Column(Text, default="[]")
    validator_config_json = Column(Text, default="{}")
    execution_config_json = Column(Text, default="{}")
    executive_report_text = Column(Text, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    results = relationship("TestResult", back_populates="test_run", cascade="all, delete-orphan")
    reports = relationship("Report", back_populates="test_run", cascade="all, delete-orphan")


class TestResult(Base):
    __tablename__ = "test_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    test_run_id = Column(Integer, ForeignKey("test_runs.id"), nullable=False)
    test_case_id = Column(Integer, ForeignKey("test_cases.id"), nullable=False)
    model_id = Column(String, nullable=False)
    provider = Column(String, nullable=False)
    model_name = Column(String, nullable=False)
    prompt_text = Column(Text, nullable=True)
    response_text = Column(Text, nullable=True)
    response_json = Column(Text, nullable=True)
    raw_response_json = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    error_type = Column(String, nullable=True)
    latency_ms = Column(Float, nullable=True)
    prompt_tokens = Column(Integer, nullable=True)
    completion_tokens = Column(Integer, nullable=True)
    total_tokens = Column(Integer, nullable=True)
    tokens_per_second = Column(Float, nullable=True)
    estimated_cost = Column(Float, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    status = Column(String, default="pending")

    test_run = relationship("TestRun", back_populates="results")
    test_case = relationship("TestCase", back_populates="results")
    validations = relationship("ValidationResult", back_populates="test_result", cascade="all, delete-orphan")
    metrics = relationship("MetricResult", back_populates="test_result", cascade="all, delete-orphan")


class ValidationResult(Base):
    __tablename__ = "validation_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    test_result_id = Column(Integer, ForeignKey("test_results.id"), nullable=False)
    validator_provider = Column(String, nullable=True)
    validator_model = Column(String, nullable=True)
    validator_status = Column(String, default="ok", nullable=True)
    validator_error_message = Column(Text, nullable=True)
    validator_raw_response = Column(Text, nullable=True)
    validator_attempts = Column(Integer, default=1, nullable=True)
    score = Column(Float, nullable=True)
    passed = Column(Boolean, nullable=True)
    faithfulness_score = Column(Float, nullable=True)
    format_score = Column(Float, nullable=True)
    semantic_score = Column(Float, nullable=True)
    safety_score = Column(Float, nullable=True)
    completeness_score = Column(Float, nullable=True)
    error_score = Column(Float, nullable=True)
    hallucination_detected = Column(Boolean, default=False)
    refusal_detected = Column(Boolean, default=False)
    validation_json = Column(Text, nullable=True)
    validation_text = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    test_result = relationship("TestResult", back_populates="validations")


class MetricResult(Base):
    __tablename__ = "metric_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    test_result_id = Column(Integer, ForeignKey("test_results.id"), nullable=False)
    metric_name = Column(String, nullable=False)
    metric_value = Column(Float, nullable=True)
    metric_payload_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    test_result = relationship("TestResult", back_populates="metrics")


class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    test_run_id = Column(Integer, ForeignKey("test_runs.id"), nullable=False)
    title = Column(String, nullable=True)
    summary_text = Column(Text, nullable=True)
    findings_json = Column(Text, nullable=True)
    chart_payload_json = Column(Text, nullable=True)
    html_path = Column(String, nullable=True)
    json_path = Column(String, nullable=True)
    csv_path = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    test_run = relationship("TestRun", back_populates="reports")


class UploadedFile(Base):
    __tablename__ = "uploaded_files"

    id = Column(Integer, primary_key=True, autoincrement=True)
    original_filename = Column(String, nullable=False)
    stored_path = Column(String, nullable=False)
    mime_type = Column(String, nullable=True)
    size_bytes = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
