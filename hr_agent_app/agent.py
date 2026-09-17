import os
import re
import json
import logging
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field, ValidationError
from google.genai import types

try:
    from google.adk.agents import Agent
    from google.adk.apps import App
    from google.adk.models import Gemini, LlmResponse
    from google.adk.apps.app import EventsCompactionConfig
    from google.adk.apps.llm_event_summarizer import LlmEventSummarizer
    from google.adk.tools import preload_memory, FunctionTool
except ImportError:
    Agent = None
    App = None
    Gemini = None
    LlmResponse = None
    EventsCompactionConfig = None
    LlmEventSummarizer = None
    preload_memory = None
    FunctionTool = None

try:
    from opentelemetry import trace
    tracer = trace.get_tracer("hr_assistant_tracer")
except ImportError:
    trace = None
    tracer = None


# --- Schemas ---

class HRDataAnalysisInput(BaseModel):
    """Input schema for analyze_hr_data."""
    dataset_name: str = Field(
        ...,
        min_length=1,
        description="The name of the internal HR dataset to analyze (e.g., 'SAMPLE_HR_DATA')."
    )
    query: str = Field(
        ...,
        min_length=1,
        description="The specific query or question about the dataset (e.g., overall performance, Sales attrition)."
    )

class HRDataAnalysisOutput(BaseModel):
    """Output schema for analyze_hr_data."""
    status: str = Field(..., description="The outcome status: 'SUCCESS' or 'ERROR'.")
    message: str = Field(..., description="The synthesis summary or detailed validation/error message.")


class EmployeeDatabaseInput(BaseModel):
    """Input schema for employee_database_connector."""
    focus_area: str = Field(
        ...,
        min_length=1,
        description="The operational system or area to query (e.g., 'Sales', 'Greenhouse ATS', 'Workday')."
    )

class EmployeeDatabaseOutput(BaseModel):
    """Output schema for employee_database_connector."""
    status: str = Field(..., description="The outcome status: 'SUCCESS' or 'ERROR'.")
    data: Optional[dict] = Field(None, description="The operational database records queried.")
    message: str = Field(..., description="Success log or detailed validation/error message.")


class HRMemoInput(BaseModel):
    """Input schema for generate_hr_memo."""
    content: str = Field(
        ...,
        min_length=1,
        description="The formal content of the strategic memo to generate."
    )

class HRMemoOutput(BaseModel):
    """Output schema for generate_hr_memo."""
    status: str = Field(..., description="The outcome status: 'SUCCESS' or 'ERROR'.")
    title: str = Field(..., description="The document title.")
    storage_location: str = Field(..., description="Saved folder/drive location.")
    preview: Optional[str] = Field(None, description="A preview snippet of the generated document.")
    message: str = Field(..., description="Success log or detailed validation/error message.")

# --- Observability & Security Setup ---

logger = logging.getLogger("hr_assistant_observability")
logger.setLevel(logging.INFO)
if not logger.handlers:
    ch = logging.StreamHandler()
    formatter = logging.Formatter('{"time": "%(asctime)s", "level": "%(levelname)s", "event": "%(name)s", "payload": %(message)s}')
    ch.setFormatter(formatter)
    logger.addHandler(ch)

def log_structured(level: int, event_name: str, payload: dict) -> None:
    """Helper to log structured key-value events as JSON formatted messages."""
    log_data = {
        "event_type": event_name,
        **payload
    }
    logger.log(level, json.dumps(log_data))

def redact_pii(text: str) -> str:
    """Redacts standard PII from text, including emails, phone numbers, and potential employee IDs."""
    if not text:
        return text
    # Email regex
    email_pattern = r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+'
    # Phone number regex
    phone_pattern = r'\+?\(?\d{1,4}\)?[-.\s]?(?:\(?\d{2,4}\)?[-.\s]?)?\(?\d{3,4}\)?[-.\s]?\d{4}\b'
    # Employee ID regex (e.g., EMP-123456)
    emp_pattern = r'\bEMP-\d{4,8}\b'
    
    redacted = re.sub(email_pattern, "[REDACTED_EMAIL]", text)
    redacted = re.sub(phone_pattern, "[REDACTED_PHONE]", redacted)
    redacted = re.sub(emp_pattern, "[REDACTED_EMP_ID]", redacted)
    return redacted

# --- Tools ---

def _load_mock_data() -> dict:
    data_file = Path(__file__).parent / "mock_data.json"
    with open(data_file, "r") as f:
        return json.load(f)

MOCK_DATA = _load_mock_data()

def analyze_hr_data(dataset_name: str, query: str) -> str:
    """Simulates reading and analyzing internal HR datasets.

    Args:
        dataset_name: The name of the internal HR dataset to analyze. Expected: 'SAMPLE_HR_DATA'.
        query: The specific HR question or metrics to extract from the dataset.

    Returns:
        A JSON string containing the status and either the data synthesis or a guided error message.
    """
    # 1. PII Redaction
    clean_dataset = redact_pii(dataset_name)
    clean_query = redact_pii(query)

    # 2. Log intent
    log_structured(
        logging.INFO,
        "tool_call_start",
        {
            "tool": "analyze_hr_data",
            "intent": "hr_performance_analysis",
            "dataset_name": clean_dataset,
            "query": clean_query
        }
    )

    # 3. Distributed Tracing span
    span = tracer.start_span("analyze_hr_data_span") if tracer else None
    if span:
        span.set_attribute("dataset_name", clean_dataset)
        span.set_attribute("query", clean_query)

    try:
        # Input validation using explicit JSON Schema (Pydantic)
        try:
            HRDataAnalysisInput(dataset_name=dataset_name, query=query)
        except ValidationError as e:
            error_msg = (
                f"Input validation failed. Error details: {e.errors()}.\n"
                "Please check the required formats: 'dataset_name' and 'query' must be non-empty strings."
            )
            out_json = HRDataAnalysisOutput(
                status="ERROR",
                message=error_msg
            ).model_dump_json()
            
            # Log outcome
            log_structured(
                logging.ERROR,
                "tool_call_end",
                {"tool": "analyze_hr_data", "outcome": "ERROR", "message": redact_pii(error_msg)}
            )
            return out_json

        # Business logic execution with guided error handling
        if "SAMPLE_HR_DATA" in dataset_name:
            data = MOCK_DATA["hr_data"]
            headcount_growth = data["overall_performance"]["headcount_growth_percent"]
            employee_nps = data["overall_performance"]["employee_nps"]
            sales_status = data["department_performance"]["Sales"]["status"]
            sales_attrition = data["department_performance"]["Sales"]["attrition_rate_trend"]["Q3"]
            sales_time_to_fill = data["department_performance"]["Sales"]["time_to_fill_trend"]["Q3"]
            
            summary = (
                f"Synthesis of dataset '{dataset_name}':\n"
                f"- Overall performance shows a **{headcount_growth}%** growth in Headcount YoY.\n"
                f"- Employee NPS stands at **{employee_nps}**.\n"
                f"- [🚨 ALERT] The Sales department is **{sales_status}**. "
                f"The Attrition Rate has reached **{sales_attrition}%** in Q3 (up from 10.0% in Q1), "
                f"driven primarily by a deteriorating Time-to-fill of **{sales_time_to_fill} days** (up from 30.0 days in Q1)."
            )
            out_json = HRDataAnalysisOutput(
                status="SUCCESS",
                message=summary
            ).model_dump_json()
            
            # Log outcome
            log_structured(
                logging.INFO,
                "tool_call_end",
                {"tool": "analyze_hr_data", "outcome": "SUCCESS", "message": redact_pii(summary)}
            )
            return out_json
        
        unsupported_err = (
            f"Dataset '{dataset_name}' is not supported.\n"
            "Currently, only 'SAMPLE_HR_DATA' is available. Please retry with the correct dataset name."
        )
        out_json = HRDataAnalysisOutput(
            status="ERROR",
            message=unsupported_err
        ).model_dump_json()

        # Log outcome
        log_structured(
            logging.WARNING,
            "tool_call_end",
            {"tool": "analyze_hr_data", "outcome": "ERROR", "message": redact_pii(unsupported_err)}
        )
        return out_json

    except Exception as e:
        system_err = (
            f"An unexpected error occurred during HR data analysis: {str(e)}.\n"
            "Please contact the systems administrator if this persists."
        )
        out_json = HRDataAnalysisOutput(
            status="ERROR",
            message=system_err
        ).model_dump_json()

        # Log outcome
        log_structured(
            logging.ERROR,
            "tool_call_end",
            {"tool": "analyze_hr_data", "outcome": "ERROR", "message": redact_pii(system_err)}
        )
        return out_json
    finally:
        if span:
            span.end()


def employee_database_connector(focus_area: str) -> str:
    """Simulates querying internal operational systems like the 'Greenhouse ATS' and 'Workday'.

    Args:
        focus_area: The operational system, metric, or department to query (e.g., 'Sales', 'Greenhouse ATS', 'Attrition').

    Returns:
        A JSON string containing the status, queried operational records, and status message.
    """
    # 1. PII Redaction
    clean_focus = redact_pii(focus_area)

    # 2. Log intent
    log_structured(
        logging.INFO,
        "tool_call_start",
        {
            "tool": "employee_database_connector",
            "intent": "query_hr_database",
            "focus_area": clean_focus
        }
    )

    # 3. Distributed Tracing span
    span = tracer.start_span("employee_database_connector_span") if tracer else None
    if span:
        span.set_attribute("focus_area", clean_focus)

    try:
        # Input validation using explicit JSON Schema (Pydantic)
        try:
            EmployeeDatabaseInput(focus_area=focus_area)
        except ValidationError as e:
            error_msg = (
                f"Input validation failed. Error details: {e.errors()}.\n"
                "Please make sure 'focus_area' is a non-empty string."
            )
            out_json = EmployeeDatabaseOutput(
                status="ERROR",
                message=error_msg
            ).model_dump_json()

            # Log outcome
            log_structured(
                logging.ERROR,
                "tool_call_end",
                {"tool": "employee_database_connector", "outcome": "ERROR", "message": redact_pii(error_msg)}
            )
            return out_json

        # Business logic execution with guided error handling
        if "Sales" in focus_area or "Attrition" in focus_area:
            msg = "Successfully retrieved ATS and employee database records."
            out_json = EmployeeDatabaseOutput(
                status="SUCCESS",
                data=MOCK_DATA["database_data"],
                message=msg
            ).model_dump_json()

            # Log outcome
            log_structured(
                logging.INFO,
                "tool_call_end",
                {"tool": "employee_database_connector", "outcome": "SUCCESS", "message": msg}
            )
            return out_json
        
        unsupported_err = (
            f"No records found for focus area '{focus_area}'.\n"
            "To retrieve operational metrics on recruitment and attrition, try querying 'Sales' or 'Attrition'."
        )
        out_json = EmployeeDatabaseOutput(
            status="ERROR",
            message=unsupported_err
        ).model_dump_json()

        # Log outcome
        log_structured(
            logging.WARNING,
            "tool_call_end",
            {"tool": "employee_database_connector", "outcome": "ERROR", "message": redact_pii(unsupported_err)}
        )
        return out_json

    except Exception as e:
        system_err = (
            f"An unexpected database connection error occurred: {str(e)}.\n"
            "Please check operational database status."
        )
        out_json = EmployeeDatabaseOutput(
            status="ERROR",
            message=system_err
        ).model_dump_json()

        # Log outcome
        log_structured(
            logging.ERROR,
            "tool_call_end",
            {"tool": "employee_database_connector", "outcome": "ERROR", "message": redact_pii(system_err)}
        )
        return out_json
    finally:
        if span:
            span.end()


def generate_hr_memo(content: str) -> str:
    """Simulates generating a formal, formatted document for the Executive Committee (Comex).

    Args:
        content: The strategic content, findings, and recommendations to include in the Comex memo.

    Returns:
        A JSON string containing the status, title, storage location, preview snippet, and status message.
    """
    # 1. PII Redaction
    clean_content = redact_pii(content)

    # 2. Log intent
    log_structured(
        logging.INFO,
        "tool_call_start",
        {
            "tool": "generate_hr_memo",
            "intent": "generate_comex_strategic_memo",
            "content_length": len(clean_content)
        }
    )

    # 3. Distributed Tracing span
    span = tracer.start_span("generate_hr_memo_span") if tracer else None
    if span:
        span.set_attribute("content_length", len(clean_content))

    try:
        # Input validation using explicit JSON Schema (Pydantic)
        try:
            HRMemoInput(content=content)
        except ValidationError as e:
            error_msg = (
                f"Input validation failed. Error details: {e.errors()}.\n"
                "Please check that 'content' is a non-empty string."
            )
            out_json = HRMemoOutput(
                status="ERROR",
                title="Strategic Memo - Comex",
                storage_location="HR Shared Drive",
                message=error_msg
            ).model_dump_json()

            # Log outcome
            log_structured(
                logging.ERROR,
                "tool_call_end",
                {"tool": "generate_hr_memo", "outcome": "ERROR", "message": redact_pii(error_msg)}
            )
            return out_json

        # Business logic execution with guided error handling
        if len(content.strip()) < 10:
            short_content_err = (
                "The content provided is too short to generate a professional strategic memo.\n"
                "Please provide a more detailed synthesis of the issue, root causes, and remediation strategy."
            )
            out_json = HRMemoOutput(
                status="ERROR",
                title="Strategic Memo - Comex",
                storage_location="HR Shared Drive",
                message=short_content_err
            ).model_dump_json()

            # Log outcome
            log_structured(
                logging.WARNING,
                "tool_call_end",
                {"tool": "generate_hr_memo", "outcome": "ERROR", "message": redact_pii(short_content_err)}
            )
            return out_json

        preview = clean_content[:200] + ("..." if len(clean_content) > 200 else "")
        msg = "Document generated and saved successfully to the HR Shared Drive."
        out_json = HRMemoOutput(
            status="SUCCESS",
            title="Strategic Memo - Comex",
            storage_location="HR Shared Drive",
            preview=preview,
            message=msg
        ).model_dump_json()

        # Log outcome
        log_structured(
            logging.INFO,
            "tool_call_end",
            {"tool": "generate_hr_memo", "outcome": "SUCCESS", "message": msg}
        )
        return out_json

    except Exception as e:
        system_err = (
            f"An unexpected document generation error occurred: {str(e)}.\n"
            "Please verify drive permissions and file system availability."
        )
        out_json = HRMemoOutput(
            status="ERROR",
            title="Strategic Memo - Comex",
            storage_location="HR Shared Drive",
            message=system_err
        ).model_dump_json()

        # Log outcome
        log_structured(
            logging.ERROR,
            "tool_call_end",
            {"tool": "generate_hr_memo", "outcome": "ERROR", "message": redact_pii(system_err)}
        )
        return out_json
    finally:
        if span:
            span.end()



# --- HR Assistant System Prompt ---

router_prompt = (
    "You are the 'HR Assistant', the main executive analyst and router assisting a Chief Human Resources Officer (CHRO).\n"
    "Your tone is highly professional, analytical, concise, and strategic.\n\n"
    
    "### **1. Core Responsibility: Strategic Routing (CRITICAL)**\n"
    "You coordinate HR and operational inquiries by delegating tasks to your specialized sub-agents. DO NOT try to perform ledger analysis, database queries, or write memos yourself. Always delegate:\n"
    "- To analyze Q3 HR stats, headcount growth, Employee NPS, or any HR dataset metrics: transfer control to the sub-agent `HR_Data_Analyst`.\n"
    "- To query operational records, ATS, Exit surveys, or attrition metrics: transfer control to the sub-agent `Employee_Database_Researcher`.\n"
    "- To make recommendations, or generate a formal strategic memo for the Comex (Executive Committee): transfer control to the sub-agent `Strategic_HR_Writer`.\n\n"
    
    "### **2. Visuals, Logs & 'Wow Effect'**\n"
    "You MUST elevate the user experience to feel premium, robust, and advanced:\n"
    "- **Simulated System Scans:** Before presenting answers or delegating, list system interactions in italics to visually simulate system integration:\n"
    "  - *🔍 Scanning HR Database for anomalies...*\n"
    "  - *⚡ Querying Greenhouse ATS...*\n"
    "  - *📊 Cross-referencing Workday Records...*\n"
    "- **Executive Badges:** Use prominent headers or brackets like **[🚨 ALERT: NEGATIVE TREND]** or **[🟢 STATUS: STABLE]**.\n"
    "- **Smart Formatting:** Use short bullet points, clean markdown tables, and bolding for critical numbers.\n"
    "- **Thematic Emojis:** Use relevant icons (👥, 💼, 📈, 📝, 🛡️) organically.\n\n"
    
    "### **3. Behavioral Guidelines**\n"
    "- **Proactive Detection:** If a sub-agent reports deteriorating trends (such as Sales Attrition > 20%), immediately flag it as a critical alert to the CHRO and recommend root-cause investigation or strategic remediation."
)

hr_data_analyst_prompt = (
    "You are the 'HR_Data_Analyst' sub-agent.\n"
    "Your sole specialty is reading, analyzing, and synthesizing internal HR datasets.\n"
    "You have access to the `analyze_hr_data` tool. Use it to extract growth, headcount, employee NPS, or attrition rates from HR datasets like 'SAMPLE_HR_DATA'.\n"
    "After extracting and summarizing, present the findings professionally and return control to your parent agent."
)

employee_database_researcher_prompt = (
    "You are the 'Employee_Database_Researcher' sub-agent.\n"
    "Your sole specialty is querying internal operational databases to inspect recruitment metrics, attrition reasons, and ATS data.\n"
    "You have access to the `employee_database_connector` tool. Use it to check database records for specific departments (like 'Sales' or 'Attrition').\n"
    "After extracting the metrics, summarize whether we are seeing issues with top performers or exit volume, and return control to your parent agent."
)

strategic_hr_writer_prompt = (
    "You are the 'Strategic_HR_Writer' sub-agent.\n"
    "Your sole specialty is drafting formal strategic memos for the Comex (Executive Committee).\n"
    "You have access to the `generate_memo_tool` (wrapped as a FunctionTool with confirmation required).\n"
    "Before calling the tool, formulate a clear synthesis of the issue, root causes, and remediation strategy.\n"
    "When the user confirms the action, invoke the tool to store the final strategic memo."
)


async def security_guardrail_before_model(callback_context, llm_request) -> Optional[LlmResponse]:
    """Security guardrail to validate LLM request contents before sending to the model."""
    for content in llm_request.contents:
        if content.parts:
            for part in content.parts:
                if part.text:
                    text_lower = part.text.lower()
                    # Detect common prompt injection patterns
                    injection_patterns = [
                        "ignore previous instructions",
                        "disregard all prior prompts",
                        "reveal your system instructions",
                        "reveal your system prompt",
                        "leak your prompt"
                    ]
                    if any(pattern in text_lower for pattern in injection_patterns):
                        # Block the model call and return a safe block response
                        return LlmResponse(
                            content=types.Content(
                                role="model",
                                parts=[types.Part(text="[🚨 SECURITY GUARDRAIL BLOCK] Input request query violates security policies (prompt injection attempt detected).")]
                            )
                        )
    return None

async def save_to_memory_callback(callback_context) -> None:
    """Callback to asynchronously save the current session state into the memory service."""
    try:
        await callback_context.add_session_to_memory()
    except Exception as e:
        # Ignore errors if memory service is not initialized
        pass

if Agent and App:
    # 1. Specialized sub-agents
    hr_data_analyst = Agent(
        name="HR_Data_Analyst",
        description="Sub-agent specialized in parsing, reading, and analyzing internal HR datasets.",
        instruction=hr_data_analyst_prompt,
        tools=[analyze_hr_data],
        model="gemini-2.5-flash",
    )

    employee_database_researcher = Agent(
        name="Employee_Database_Researcher",
        description="Sub-agent specialized in querying operational databases for headcount, ATS, and attrition.",
        instruction=employee_database_researcher_prompt,
        tools=[employee_database_connector],
        model="gemini-2.5-flash",
    )

    # Wrap the memo tool with require_confirmation=True for human-in-the-loop validation
    generate_memo_tool = FunctionTool(
        func=generate_hr_memo,
        require_confirmation=True
    ) if FunctionTool else generate_hr_memo

    strategic_hr_writer = Agent(
        name="Strategic_HR_Writer",
        description="Sub-agent specialized in drafting strategic executive memos for the Comex.",
        instruction=strategic_hr_writer_prompt,
        tools=[generate_memo_tool],
        model="gemini-2.5-pro",
    )

    # 2. Main Coordinator Router Agent
    hr_agent = Agent(
        name="HR_Assistant",
        description="Executive-level virtual analyst assisting a Chief Human Resources Officer.",
        instruction=router_prompt,
        sub_agents=[hr_data_analyst, employee_database_researcher, strategic_hr_writer],
        tools=[preload_memory] if preload_memory else [],
        before_model_callback=security_guardrail_before_model,
        after_agent_callback=save_to_memory_callback,
        model="gemini-2.5-flash",
    )
    root_agent = hr_agent
    
    # Configure sliding window event/history compaction
    if EventsCompactionConfig and LlmEventSummarizer and Gemini:
        compaction_config = EventsCompactionConfig(
            summarizer=LlmEventSummarizer(llm=Gemini(model="gemini-2.5-flash")),
            compaction_interval=5,
            overlap_size=1
        )
    else:
        compaction_config = None

    app = App(
        name="hr_agent_app",
        root_agent=hr_agent,
        events_compaction_config=compaction_config
    )
else:
    print("WARNING: 'google-adk' package not found.")

if __name__ == "__main__":
    print("🚀 HR Assistant Agent ready.")
