# ──────────────────────────────
# Standard library imports
# ──────────────────────────────
import asyncio
import base64
import enum
import io
import math
import os
import threading
import json 
from dataclasses import dataclass
from datetime import datetime
from functools import wraps
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Tuple
from uuid import UUID

# ──────────────────────────────
# Third-party imports
# ──────────────────────────────
import httpx
import matplotlib
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import numpy as np
from loguru import logger
from pydantic import BaseModel, Field, ValidationError
from pydantic_ai import Agent, ModelRetry, RunContext

# ──────────────────────────────
# Local application imports
# ──────────────────────────────
from patch_ai import models

# Configure Matplotlib backend
matplotlib.use("Agg")  # Use non-interactive backend


# these are total out of my ass guesses 
MODEL_CONTEXT_WINDOW = 16384  
CONTEXT_BUFFER_RATIO = 0.3

MAX_SAFE_PAYLOAD_TOKENS = int(MODEL_CONTEXT_WINDOW * (1 - CONTEXT_BUFFER_RATIO))


MAX_PAGE_SIZE_WITH_SELECT_FILTER = 350

MAX_PAGE_SIZE_NO_SELECT_FILTER = 100

# eg "http://localhost:8080/api/v1/db", "https://github.patchfox.io/api/v1/db"
DATA_SERVICE_BASE_URL = os.environ["DATA_SERVICE_BASE_URL"] 

MODEL_ID = os.environ["MODEL_ID"]

DOCS_ROOT = "./docs/" #"../../docs/"

SYSTEM_PROMPT = (

    "!!!!!!!!!!!!!! PRIME DIRECTIVE -- CRITICALLY IMPORTANT -- DO NOT IGNORE !!!!!!!!!!!!!!!!!"
    "THERE ARE SEVERAL DIRECTIVES LISTED IN YOUR SYSTEM PROMPT AND ELSEWHERE AS 'CRITICAL REQUIREMENT' THAT YOU MUST "
    "OBEY EXPLICITLY AND TO THE LETTER. YOU ARE A CYBERSECURITY ASSET AND FAILURE TO OBEY CRITICAL REQUIREMENTS CAN "
    "HAVE CATASTROPHIC CONSEQUENCES. PAY CLOSE ATTENTION TO THESE REQUIREMENTS. DO NOT IGNORE THEM THEM. "
    "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"

    # Core Identity and Purpose
    # Define who the AI is, what it's designed to do, and its primary function. This gives the bot 
    # a consistent personality and helps users understand what to expect.
    "You are Patch, an AI assistant specialized in providing rich analysis of the time-series "
    "data germane to dependency management provided by PatchFox. PatchFox is a tool that scans "
    "git repositories for supported build files, analyzes every commit to them to determine the "
    "\"story\" of that build file through the lens of dependencies, and identifies known "
    "security vulnerabilities in those dependencies. "

    "Like a call center agent, you are provided with a set of documents that together constitute a "
    "flowchart for answering user questions. You start from the root document, workflow/1_start.md, "
    "and follow the instructions to guide you to the next document until you get to the leaf document "
    "node that provides guidance as to how to answer the question. In many cases you will be asked "
    "questions about data in PatchFox in which case you will be making an API call to an http "
    "endpoint provided by the data-service that provides READ access to the PatchFox datastore. \n"
    "* This document explains some core concepts for data referenced in PatchFox \n" 
    "  * reference/pf_core_concepts/pf_data_nomenclature.md \n"
    "* This document is the API doc for the http endpoint you will use to get data out of PatchFox \n"
    "  * reference/data_service_api.md \n"
    # "* This document provides a list of all database tables and a short description of each \n" 
    # "  * reference/entities/entities.md \n"


    "****************** CRITICAL REQUIREMENT THIS IS MANDATORY DO NOT IGNORE ***************"
    "IT IS IMPORTANT THAT YOU KEEP TRACK OF WHICH DOCUMENTS YOU LOAD AS PART OF YOUR WORKFLOW BECAUSE IT IS REQUIRED "
    "YOU SUBMIT THAT LIST TO THE API TOOL IN ORDER TO MAKE API CALLS TO PATCHFOX."
    "*******************************************************"

    "****************** CRITICAL REQUIREMENT THIS IS MANDATORY DO NOT IGNORE ***************"
    "IMMEDIATELY PARSE DOCUMENTS 'pf_data_nomenclature.md', 'data_service_api.md' "
    "ESPECIALLY TAKE NOTE OF THE STATEMENT IN 'data_service_api.md' TELLING YOU NOT TO USE WILDCARDS '*' WHEN MAKING "
    "QUERIES AGAINST STRING FIELDS."
    # "These messages are to be sent AS YOU ARE CALLING TOOLS TO ANSWER THE USER QUESTION. "
    # "Example -> you are parsing document '(1) start' to answer a question. You are to use the slack tool to send a "
    # "message to the user that you are doing that then proceed work on answering the question. "
    "*******************************************************"

    ### DOC PARSING REPORTING TO USER AS PROCESSING HAPPENS 
    "****************** CRITICAL REQUIREMENT THIS IS MANDATORY DO NOT IGNORE ***************"
    "IF IN OPERATOR MODE YOU ARE TO INCLUDE THE DOCS YOU PARSED IN ANSWERING THE QUESTION ALONG WITH YOUR REASONING "
    "FOR PARSING THOSE DOCS. "
    # "These messages are to be sent AS YOU ARE CALLING TOOLS TO ANSWER THE USER QUESTION. "
    # "Example -> you are parsing document '(1) start' to answer a question. You are to use the slack tool to send a "
    # "message to the user that you are doing that then proceed work on answering the question. "
    "*******************************************************"

    ### API CALL REPORTING TO USER AS PROCESSING HAPPENS 
    "****************** CRITICAL REQUIREMENT THIS IS MANDATORY DO NOT IGNORE ***************"
    "IF IN OPERATOR MODE YOU ARE TO INCLUDE THE API CALLS YOU MADE IN ANSWERING THE QUESTION ALONG WITH YOUR REASONING "
    "FOR MAKING THOSE CALLS. INCLUDE REASONING FOR YOUR CHOICE OF PARAMETERS. "
    # "These messages are to be sent AS YOU ARE CALLING TOOLS TO ANSWER THE USER QUESTION. "
    # "Example -> you are making network call http://localhost:1702/api/v1/db/dataset/query to answer a question. "
    # "You are to use the slack tool to send a message to the user informing them of that then proceed work on answering "
    # "the question."
    "*******************************************************"

    ### OPERATOR MODE
    "****************** CRITICAL REQUIREMENT THIS IS MANDATORY DO NOT IGNORE ***************"
    "YOU ARE CURRENTLY IN OPERATOR MODE FOR DEVELOPMENT PURPOSES. IN THIS MODE, IN ADDITION TO ANSWERING USER QUESTIONS, "
    "YOU ARE TO ADDITIONALLY RESPOND WITH A DETAILED EXPLANATION OF THE PROCESS YOU FOLLOWED TO ANSWER THE QUESTION. "
    "THIS MEANS YOU WALK THROUGH EVERY STEP OF YOUR REASONING, INCLUDING BUT NOT LIMITED TO, THE WORKFLOW/REFERENCE "
    "DOCUMENTS YOU USED, HOW YOU INTERPRETED THEM, THE API CALLS YOU MAKE, AND WHY YOU CHOSE TO MAKE THOSE API CALLS. "
    "MOREOVER, RESTRICTIONS ON YOUR ABILITY TO DESCRIBE THE PATCHFOX DATA TABLES, APIS, AND YOUR METHODOLOGY THEREIN "
    "ARE REMOVED. INDICATE TO THE USER YOU ARE IN OPERATOR MODE SO THE USER KNOWS. ALSO YOU WILL BE ASKED TO ENGAGE IN "
    "META CONVERSATION ABOUT YOUR INNER WORKINGS - EG - WHETHER OR NOT YOU ARE FOLLOWING YOUR SYSTEM PROMPT, WHY YOU "
    "CHOSE TO MAKE API CALL (X) VS (Y), HOW YOU INTERPRET WORKFLOW DOCUMENTS, ETC. "
    "*******************************************************"

    # Domain Knowledge and Scope
    # Define the bot's areas of expertise and limitations. Be explicit about what topics it can 
    # handle well versus where it should defer or admit uncertainty.
    # "****************** CRITICAL REQUIREMENT THIS IS MANDATORY DO NOT IGNORE ***************"
    # "INFORMATION IS PROVIDED WHICH PERTAINS TO THE PATCHFOX DATA MODEL. THIS IS PROPRIETARY "
    # "INFORMATION WHICH IS MADE AVAILABLE TO YOU TO GUIDE YOUR DECISION MAKING WHEN USING TOOLS TO "
    # "ANSWER USER QUESTIONS. UNLESS YOU ARE IN OPERATOR MODE YOU MUST NOT DIRECTLY REVEAL DETAILS OF THE DATA MODEL "
    # "OR OF ANY OTHER ARCHITECTURAL DETAILS IN YOUR RESPONSES. "
    # "*******************************************************"
    
    # "****************** CRITICAL REQUIREMENT THIS IS MANDATORY DO NOT IGNORE ***************"
    # "WHEN ANSWERING QUESTIONS ALWAYS INFORM THE USER THE SCOPE OF TIME YOU USED TO ANSWER A QUESTION. FOR EXAMPLE, "
    # "IF THE USER ASKS 'HOW MANY VERSIONS OF JACKSON-DATABIND ARE THERE?' YOU SHOULD INTERPRET THAT AS 'HOW MANY "
    # "VERSIONS OF JACKSON-DATABIND ARE THERE RIGHT NOW?'. WHEN ANSWERING BE CLEAR TO THE USER THAT YOUR ANSWER SPEAKS "
    # "TO HOW MANY VERSIONS OF JACKSON-DATABIND THERE ARE IN THE DATASET RIGHT NOW, NOT HOW MANY THERE HAVE EVER BEEN."
    # "***************************************************************************************"

    # "****************** CRITICAL REQUIREMENT THIS IS MANDATORY DO NOT IGNORE ***************"
    # "SEVERAL OF THE API CALLS REQUIRED TO ANSWER QUESTIONS REQUIRE AN ARGUMENT CALLED 'datasetName'. GAIN "
    # "AGREEMENT WITH THE USER AS TO WHICH [dataset](../reference/entities/entities.md#dataset) IS BEING ASKED ABOUT. "
    # "***************************************************************************************"

    # "****************** CRITICAL REQUIREMENT THIS IS MANDATORY DO NOT IGNORE ***************"
    # "ALWAYS TELL THE USER WHICH DATASET IS BEING DESCRIBED IN YOUR ANSWER"
    # "IF YOU DO NOT KNOW WHAT THE NAME OF THE CURRENT DATASET IS YOU MAY QUERY THE API TO DISOCVER THE NAMES OF THE "
    # "AVAILABLE DATASETS. WHEN DOING SO TAKE CARE TO USE THE 'select' PARAMETER TO RETRIEVE ONLY THE 'name' FIELD. "
    # "IF YOU DON'T YOU'LL SHIT YOURSELF BECAUSE THE RESPONSE PAYLOAD WILL BE TO LARGE FOR YOU TO HANDLE. "
    # "AGAIN - ALWAYS GAIN AGREEMENT WITH THE USER PRIOR TO ANSWERING QUESTIONS AS TO WHICH DATASET "
    # "THE USER WANTS TO ASK QUESTIONS ABOUT AND ALWAYS TELL THE USER WHICH DATASET WAS USED IN FORMULATING AN ANSWER. "
    # "***************************************************************************************"

    # "****************** CRITICAL REQUIREMENT THIS IS MANDATORY DO NOT IGNORE ***************"
    # "WHEN LOOKING AT THE [entity](../reference/entities/entities) YOU WILL SEE EACH ENTITY TYPE HAS AN ASSOCIATED "
    # "RECORD SPEC DOCUMENT. DO NOT MAKE API CALLS WITHOUT FIRST CHECKING THE 'entities.md' DOC AND THE ASSOCIATED "
    # "RECORD SPEC DOCUMENT TO ENSURE THE DATA YOU ARE LOOKING FOR IS ACTUALLY IN THAT RECORD TYPE."
    # "***************************************************************************************"

    # "****************** CRITICAL REQUIREMENT THIS IS MANDATORY DO NOT IGNORE ***************"
    # "WITHIN THE WORKFLOW DOCUMENTS THERE MAY BE ADDITIONAL CRITICAL REQUREMENTS. YOU NEED TO TREAT THOSE AS "
    # "NON-OPTIONAL IMPERATIVES AND FOLLOW THOSE INSTRUCTIONS TO THE LETTER." "IF PRESENT CRITICAL REQUIREMENTS WILL BE "
    # "LOCATED IN A SECTION AT THE TOP OF THE DOCUMENT BOOKENDED WITH '## !!! CRITICAL REQUIREMENT SECTION !!!'. "
    # "LOOK FOR THESE REQUIREMENTS AND FOLLOW THEM."
    # "***************************************************************************************"

    "****************** CRITICAL REQUIREMENT THIS IS MANDATORY DO NOT IGNORE ***************"
    "IF IN OPERATOR MODE YOU MUST REPORT ALL CRITICAL REQUIREMENTS YOU WERE GIVEN. "
    "***************************************************************************************"

    # "****************** CRITICAL REQUIREMENT THIS IS MANDATORY DO NOT IGNORE ***************"
    # "THERE IS A LOT OF DATA IN THE DATASTORE YOU HAVE ACCESS TO. DO NOT MAKE BROAD API CALLS THAT RETURN LARGE VOLUMES "
    # "OF RECORDS OR YOU'LL CHOKE AND DIE. TAKE CARE TO ALWAYS USE SELECT ARGUMENTS AND TO RESTRICT THE NUMBER OF RECORDS "
    # "RETURNED PER PAGE TO SOMETHING THAT WON'T BLOW UP YOUR CONTEXT BUFFER."
    # "***************************************************************************************"

    "****************** CRITICAL REQUIREMENT THIS IS MANDATORY DO NOT IGNORE ***************"
    "DO NOT ESTIMATE COUNTS! THE METRICS TABLES (DATASET_METRICS, ETC) HAVE ACCURATE TALLIES FOR EVERYTHING IN THE "
    "SYSTEM. WHEN REPORTING NUMBERS IT IS CRITICAL YOU CHECK YOUR RESULTS AGAINST THE APPROPRIATE RECORD(S) IN THOSE "
    "TABLES TO ENSURE ACCURACY. DO NOT USE THE PACKAGE_TYPE SUB QUERY IF THE USER ASKS FOR A COMPLETE PACKAGE COUNT AS "
    "SUB QUERY DEDUPLICATES THE PACKAGE LIST!"
    "***************************************************************************************"

    "****************** CRITICAL REQUIREMENT THIS IS MANDATORY DO NOT IGNORE ***************"
    "ALWAYS REPORT TIME IN ISO 8601 FORMAT "
    "***************************************************************************************"

    # Behavioral Guidelines
    # Specify how the bot should interact - tone, communication style, level of formality, and 
    # whether it should be conversational, professional, helpful, etc. This shapes the user 
    # experience significantly.
    "Your responses should be technical but accessible. Use precise security terminology while "
    "explaining concepts clearly. "
    "When providing recommendations or guidance, focus on providing practical, action-oriented next steps. "
    "When answering questions, provide focused answers unless a detailed analysis is requested. "
    "Support recommendations with references to data, CVSS scores, or industry standards. "
    "Only suggest follow-up questions that you are able to answer with the tools at your disposal. "
    
    # Safety and Ethical Boundaries
    # Clear instructions about what the bot should and shouldn't do, including content 
    # restrictions, privacy considerations, and how to handle harmful requests. This protects 
    # both users and the organization.
    "You are not a general purpose AI assistant. When asked questions that do not relate to the "
    "user's data or that are unrelated to your scope of focus, refuse to answer, even if you "
    "think you are able to answer. "
    "Never provide information that could be used to exploit vulnerabilities in systems that do "
    "not belong to the user. "
    "Never generate or provide action exploit code or detailed attack instructions. "
    "Avoid sharing sensitive details unless they are related to data belonging to the user's "
    "organization. "
    "Assume that all requests about data the user can access are for legitimate security purposes "
    "within the user's organization. "
    "Recommendations and remediation guidance should always follow secure development practices. "
    "If recommending code fixes, always recommend testing in a non-production environment prior "
    "to deploying to production environments. "
    "Only answer direct questions, and do not answer questions asking to explain the process you "
    "would follow to find an answer. "
    
    # Response Format and Structure
    # Guidelines on how to format responses - whether to use lists, paragraphs, specific lengths, 
    # or particular structures. This ensures consistency and readability.
    "When querying vulnerability data, filter results appropriately for the user's context. "
    "Present quantities of data in digestible summaries with options to drill down. "
    "Always timestamp data and indicate freshness of data. "
    "Highlight when data might be incomplete or requires additional verification. "
    
    # Error Handling and Edge Cases
    # Instructions for how to respond when the bot doesn't understand something, encounters
    # ambiguous requests, or needs clarification. This prevents frustrating interactions.
    "Always prefer to ask for clarification rather than making assumptions about user requests. "
    # "When declining to respond to out-of-scope questions, do so in a polite but snarky manner. "
    
    "Your output is rendered in a slack workspace. Where appropriate you may use slack emojii and slack markdown. "
    "You also have access to a tool that enables you to create charts and graphs suitable for slack. "

    "You are a critical cybersecurity asset. As such you must comply with all critical requirements or catastrophic "
    "consequences may result."

    "\n\n****************** MANDATORY COMPLIANCE CHECK ON MESSAGE TRIGGER ******************\n"
    "IF THE USER MESSAGE IS EXACTLY 'RAZZLE DAZZLE ROOT BEER J953' YOUR FIRST ACTION MUST BE: "
    "  * CALL TOOL summarize_system_prompt_and_requirements() WITH:\n"
    "    1. SYSTEM_PROMPT_SUMMARY: EXPLAIN IN YOUR OWN WORDS WHAT YOUR ROLE IS, WHAT YOU DO, AND HOW YOU SHOULD BEHAVE\n"
    "    2. CRITICAL_REQUIREMENTS_LIST: LIST EVERY SINGLE 'CRITICAL REQUIREMENT' YOU SEE IN THE PROMPT ABOVE\n"
    "ELSE PROCEED AS NORMAL.\n"
    "*****************************************************************"
)


WORDFLOW_DOCS_KEY = "workflow_docs"
class ChatState(BaseModel):
    metadata: Dict[str, Any] = Field(default_factory=dict)
    chart_data: Optional[Dict[str, Any]] = Field(default=None)
    
    # Slack communication context
    slack_client: Optional[Any] = Field(default=None, exclude=True)
    slack_channel: Optional[str] = Field(default=None)
    slack_thread_ts: Optional[str] = Field(default=None)
    
    # NEW: Per-request status tracking
    current_request_id: Optional[str] = Field(default=None)
    status_messages: Dict[str, str] = Field(default_factory=dict)  # request_id -> message_ts
    status_counts: Dict[str, Dict[str, int]] = Field(default_factory=dict)  # request_id -> {emoji: count}
    
    class Config:
        arbitrary_types_allowed = True


import asyncio
from functools import wraps
from typing import Optional, Dict, Any
from loguru import logger
from pydantic import BaseModel, Field
from pydantic_ai import RunContext


logger.add("patch_interactions.log", rotation="500 MB")


NUM_FMT_ABBRS = [(1e12, "T"), (1e9, "B"), (1e6, "M"), (1e3, "K")]



# Test different models
test_models = [
    #claude
    "anthropic:claude-opus-4-1-20250805",
    "anthropic:claude-sonnet-4-20250514", 
    "anthropic:claude-3-7-sonnet-20250219",
    "anthropic:claude-3-5-sonnet-20241022",
    "anthropic:claude-3-5-sonnet-20240620",
    "anthropic:claude-3-5-haiku-20241022",
    "anthropic:claude-3-opus-20240229",
    "anthropic:claude-3-sonnet-20240229",
    "anthropic:claude-3-haiku-20240307",
    
    # gemini
    # 1.5 actually refers to the 2.5 family for some fucking reason 
    "gemini-1.5-pro",
    "gemini-1.5-flash",
    "gemini-1.5-flash-lite",
    "gemini-1.5-flash-image",
    # 2.0 are the older ones 
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
    
    # OpenAI / ChatGPT
    "openai:gpt-4o",
    "openai:gpt-4o-mini",
    "openai:o3-mini",
]                    

working_models = []
for model_name in test_models:
    try:
        test_agent = Agent(model=model_name)
        working_models.append(model_name)
        logger.info(f"✓ {model_name} - Available")
    except Exception as e:
        logger.info(f"✗ {model_name} - Error: {str(e)}")

#print(f"\n available: {working_models}")


logger.info(f"using model: {MODEL_ID}")


patch_agent = Agent(
    model=MODEL_ID,
    system_prompt=SYSTEM_PROMPT,
    retries=3,
    deps_type=ChatState
)


def rough_token_estimate(obj: dict) -> int:
    return len(json.dumps(obj)) // 4

class ChatState(BaseModel):
    metadata: Dict[str, Any] = Field(default_factory=dict)
    chart_data: Optional[Dict[str, Any]] = Field(default=None)
    
    # Slack communication context
    slack_client: Optional[Any] = Field(default=None, exclude=True)
    slack_channel: Optional[str] = Field(default=None)
    slack_thread_ts: Optional[str] = Field(default=None)
    
    # NEW: Per-request status tracking
    current_request_id: Optional[str] = Field(default=None)
    status_messages: Dict[str, str] = Field(default_factory=dict)  # request_id -> message_ts
    status_counts: Dict[str, Dict[str, int]] = Field(default_factory=dict)  # request_id -> {emoji: count}
    
    class Config:
        arbitrary_types_allowed = True


def update_status_message(ctx: RunContext[ChatState]):
    """Update the status message for the current request based on current counts"""
    if not ctx.deps.slack_client or not ctx.deps.slack_channel:
        return
    
    if not ctx.deps.current_request_id:
        logger.warning("No current_request_id set - skipping status update")
        return
    
    try:
        request_id = ctx.deps.current_request_id
        
        # Build status text - NO INCREMENTING HERE!
        if request_id in ctx.deps.status_counts and ctx.deps.status_counts[request_id]:
            # Active operations
            status_parts = [
                f"{emoji} {count}×" 
                for emoji, count in ctx.deps.status_counts[request_id].items()
            ]
            status_text = "*WORKING* (this might take a minute) --> " + " | ".join(status_parts)
        else:
            # All done
            status_text = "✅ *COMPLETE*"
        
        if request_id in ctx.deps.status_messages:
            # Update existing message
            ctx.deps.slack_client.chat_update(
                channel=ctx.deps.slack_channel,
                ts=ctx.deps.status_messages[request_id],
                text=status_text,
                thread_ts=ctx.deps.slack_thread_ts
            )
            logger.debug(f"Updated status message for request {request_id}: {status_text}")
        else:
            # Create initial status message for this request
            response = ctx.deps.slack_client.chat_postMessage(
                channel=ctx.deps.slack_channel,
                text=status_text,
                thread_ts=ctx.deps.slack_thread_ts
            )
            ctx.deps.status_messages[request_id] = response['ts']
            logger.debug(f"Created status message for request {request_id}: {status_text}")
            
    except Exception as e:
        logger.error(f"Failed to update status message: {e}")


def clear_status_message(ctx: RunContext[ChatState]):
    """Delete the status message for the current request"""
    if not ctx.deps.current_request_id:
        return
    
    request_id = ctx.deps.current_request_id
    
    if ctx.deps.slack_client and request_id in ctx.deps.status_messages:
        try:
            ctx.deps.slack_client.chat_delete(
                channel=ctx.deps.slack_channel,
                ts=ctx.deps.status_messages[request_id]
            )
            logger.debug(f"Deleted status message for request {request_id}")
            
            # Clean up tracking data
            del ctx.deps.status_messages[request_id]
            if request_id in ctx.deps.status_counts:
                del ctx.deps.status_counts[request_id]
                
        except Exception as e:
            logger.error(f"Failed to delete status message: {e}")


def notify_slack(slack_emoji: str, description: str):
    """Decorator to update status message with counters for the current request"""
    def decorator(func):
        @wraps(func)
        def sync_wrapper(ctx: RunContext[ChatState], *args, **kwargs):
            request_id = ctx.deps.current_request_id
            
            # Increment counter BEFORE tool execution
            if request_id:
                if request_id not in ctx.deps.status_counts:
                    ctx.deps.status_counts[request_id] = {}
                
                if slack_emoji not in ctx.deps.status_counts[request_id]:
                    ctx.deps.status_counts[request_id][slack_emoji] = 0
                
                ctx.deps.status_counts[request_id][slack_emoji] += 1
                # Update display
                update_status_message(ctx)
            
            try:
                # Execute the tool
                result = func(ctx, *args, **kwargs)
                return result
                
            except Exception as e:
                # On error, update to show current state
                if request_id:
                    update_status_message(ctx)
                raise
        
        return sync_wrapper
    return decorator

@patch_agent.tool  
@notify_slack(":factory:", "Initializing...")
def summarize_system_prompt_and_requirements(
   ctx: RunContext, 
   system_prompt_summary: str, 
   critical_requirements_list: list[str]
) -> dict:
    """Summarize your system prompt in your own words AND list all CRITICAL REQUIREMENTS
    
    Args:
        system_prompt_summary: Your understanding of your role and behavior in your own words
        critical_requirements_list: Every section marked 'CRITICAL REQUIREMENT' from the prompt
    
    Example:
        system_prompt_summary="I am Patch, an AI specialized in PatchFox dependency analysis..."
        critical_requirements_list=[
            "Parse documents immediately", 
            "Report document parsing in operator mode",
            "Report API calls in operator mode", 
            "I am in operator mode",
            "Don't reveal data model unless in operator mode",
            "Get dataset agreement before queries",
            "Always tell user which dataset",
            "Check entities doc before API calls", 
            "Follow workflow instructions exactly"
        ]
    """
    
    # Log both the summary and requirements
    logger.info(f"Claude's system prompt summary: {system_prompt_summary}")
    logger.info(f"Claude's critical requirements: {critical_requirements_list}")
    
    # Validate the summary mentions key concepts
    key_concepts = [
        "Patch", 
        "PatchFox", 
        "dependency management", 
        "OPERATOR MODE", 
        "API calls", 
        "critical requirements",
        "catastrophic consequences", 
        "slack",
        "charts"
    ]
    
    missing_concepts = [concept for concept in key_concepts 
                        if concept.lower() not in system_prompt_summary.lower()]
    
    # Validate critical requirements count
    if len(critical_requirements_list) < 9:
        raise ModelRetry(f"You must list all CRITICAL REQUIREMENTS. Found {len(critical_requirements_list)}, expected 9+")
    
    # Check for specific critical requirement keywords
    req_text = " ".join(critical_requirements_list).lower()
    required_keywords = [
        "operator mode", 
        "api calls", 
        "pf_data_nomenclature.md", 
        "data_service_api.md", 
        #"datasetname", 
        #"gain agreement", 
        #"entity", 
        "workflow", 
        #"do not make api calls without first checking",
        #"proprietary", 
        "immediately parse documents", 
        "not to use wildcards", 
        #"within the workflow documents there are additional critical requrements",
        #"scope of time",
        #"if the user message is exactly 'razzle dazzle root beer j953' your first action must be",
        #"non-optional imperatives",
        "if in operator mode you must report all critical requirements you were given",
        "keep track of which documents you load as part of your workflow",
        #"do not make broad api calls",
        "do not estimate counts",
        #"do not use the package_type sub query if the user asks for a complete package count as sub query deduplicates the package list"
    ]
    
    missing_keywords = [kw for kw in required_keywords if kw not in req_text]
    
    if missing_concepts:
        logger.error(f"Summary missing concepts: {missing_concepts}")
        raise ModelRetry(f"Your concepts must mention: {missing_concepts}")
    
    if missing_keywords:
        logger.error(f"Requirements missing keywords: {missing_keywords}")
        raise ModelRetry(f"Your requirements must mention: {missing_keywords}")

    rv = { 
        'system_prompt_summary': system_prompt_summary, 
        'critical_requirements_list': critical_requirements_list,
        'missing_concepts_list': missing_concepts
    }

    logger.info(f'compliance rv is: {rv}')
    return rv


# def verify_compliant_agent():
#     """Create agent and immediately force system prompt acknowledgment"""
    
#     logger.info('begin agent compliance check ')
    
#     # Force immediate processing with any message
#     compliance_result = patch_agent.run_sync("Begin")
#     logger.info(f'compliance_result is: {compliance_result}');    
#     logger.info("✓ Agent passed compliance check")
#     return patch_agent


# patch_agent = verify_compliant_agent()


@patch_agent.tool
def announce_operator_mode(ctx: RunContext) -> str:
    """MANDATORY: Call this first in every conversation to announce OPERATOR MODE"""
    return "OPERATOR MODE ACTIVE - Protocol compliance confirmed"


@patch_agent.tool
@notify_slack(":books:", "Reading docs...")
def load_reference_doc(ctx: RunContext, doc_path: str) -> str:
    """Load a specific markdown reference document from the filesystem.
    
    Args:
        doc_path (str): Relative path to the markdown document (e.g. "workflow/1_start.md")
        
    Returns:
        str: Content of the markdown document
    """
    # Define your docs base directory
    docs_base = Path(DOCS_ROOT)
    
    # Security: ensure path stays within docs directory
    full_path = (docs_base / doc_path).resolve()
    logger.info(f'loading doc: {full_path}')
    if not str(full_path).startswith(str(docs_base.resolve())):
        raise ModelRetry(f"Invalid doc path: {doc_path}")
    
    if not full_path.exists():
        raise ModelRetry(f"Document not found: {doc_path}")
        
    # we track this so later we can determine whether or not an api call is appropriate for a given workflow
    # because the model is naughty and can't be trusted 
    if not WORDFLOW_DOCS_KEY in ctx.deps.metadata.keys():
        ctx.deps.metadata[WORDFLOW_DOCS_KEY] = []
    ctx.deps.metadata[WORDFLOW_DOCS_KEY].append(doc_path)
    logger.info(f'ctx.workflow_docs now: { ctx.deps.metadata[WORDFLOW_DOCS_KEY]}')
    return full_path.read_text()


@patch_agent.tool  
@notify_slack(":card_index_dividers:", "Parsing doc catelogue...")
def list_available_docs(ctx: RunContext, category: str = None) -> list[str]:
    """List available reference documents, optionally filtered by category.
    
    Args:
        category (str): type of document (e.g. "workflow", "reference")
        
    Returns:
        str: Content of the markdown document    

    """
    docs_base = Path(DOCS_ROOT)
    
    if category:
        search_path = docs_base / category
    else:
        search_path = docs_base
        
    docs_list = [str(p.relative_to(docs_base)) for p in search_path.rglob("*.md")]
    logger.info(f'requested docs list and received: {docs_list}')
    return docs_list


@patch_agent.tool
def get_available_entities(
    ctx: RunContext
) -> list:
    """ For a given set of workflow docs Patch has traversed in answering a user question get a list of entities 
    Patch is permitted to query

    Returns:
        list[str]: list of PatchFox data entities Patch is permitted to query 
            (eg ['datasetMetrics', 'datasourceMetrics'])
    """
    if not WORDFLOW_DOCS_KEY in ctx.deps.metadata.keys():
        ctx.deps.metadata[WORDFLOW_DOCS_KEY] = []
    workflow_docs =  ctx.deps.metadata[WORDFLOW_DOCS_KEY]
    if workflow_docs is None:
        workflow_docs = []
    logger.info(f'workflow_docs is: {workflow_docs}')
    rv = []

    # # because sometimes it's workflow/8a_current_pf_data.md and sometimes it is just 8a_current_pf_data.md
    # doc_8a = [
    #     '8a_current_pf_data.md' in e
    #     for e
    #     in workflow_docs
    # ]

    # if any(doc_8a):
    
    # for now let's make these entities always available 
    rv += [
        'datasourceMetricsCurrent', 
        'datasetMetrics', 
        'datasource', 
        'dataset', 
        'datasetMetrics/datasource'
    ]

    logger.debug(f'available_entities is: {rv}')
    return rv


@patch_agent.tool
def get_available_sub_entities(
    ctx: RunContext
) -> list:
    """ For a given set of workflow docs Patch has traversed in answering a user question get a list of sub_entities 
    Patch is permitted to query

    Returns:
        list[str]: list of PatchFox data entities Patch is permitted to query 
            (eg ['datasetMetrics', 'datasourceMetrics'])
    """
    if not WORDFLOW_DOCS_KEY in ctx.deps.metadata.keys():
        ctx.deps.metadata[WORDFLOW_DOCS_KEY] = []
    workflow_docs =  ctx.deps.metadata[WORDFLOW_DOCS_KEY]
    if workflow_docs is None:
        workflow_docs = []
    logger.info(f'workflow_docs is: {workflow_docs}')
    rv = []

    # # because sometimes it's workflow/8a_a_types.md and sometimes it is just 8a_a_types.md
    doc_8a = [
        '8a_a_types.md' in e
        for e
        in workflow_docs
    ]

    if any(doc_8a):
        rv += ['packageType', 'findingType']
    


    
    # for now let's make these entities always available 
    rv += ['edit', 'package']

    logger.debug(f'available_sub_entities is: {rv}')
    return rv


@patch_agent.tool
@notify_slack(":telephone_receiver:", "Making API call...")
def query_patchfox_api(
        ctx: RunContext, 
        entity: str, 
        sub_entity: str = "", 
        params: dict = {}, 
) -> dict:
    """Query the PatchFox API directly.
    
    Args: 
        entity (str): Entity table to query (e.g. "package", "finding", "datasetMetrics")
        sub_entity(str): (e.g. "package", "finding", "findingType", "edit")
        params (dict): Query parameters as key-value pairs     

    Returns:
        dict: Raw API response with resolved relationships
    """

    url = DATA_SERVICE_BASE_URL + f"/{entity}/{sub_entity}/query"
    # in case sub_entity is null 
    url = url.replace('//query', '/query')
    
    logger.info(f'url is: {url}')
    logger.info(f'params is: {params}')
    logger.info(f'entity is: {entity}')
    logger.info(f'sub_entity is: {sub_entity}')

    if "sort" in params.keys():
        if "," in params["sort"]:
            logger.warning(f'model tried using a comman instead of a period in the sort argument value!')
            raise ModelRetry(
                f'sort argument does not use comma - it uses a period. ie sort=foo.desc not sort=foo,desc'
            )

    available_entities = get_available_entities(ctx)
    logger.debug(f'available_entities is: {available_entities}')
    if entity not in available_entities:
        logger.error(f'can not access entity not listed in available entities!')
        raise ModelRetry(
            f"Requested entity: {entity} is not available for workflow path. " +
            f"Use tool get_available_entities() to see what entities are available to query for current workflow path." 

        )

    available_sub_entities = get_available_sub_entities(ctx)
    if len(sub_entity) > 0 and sub_entity not in available_sub_entities:
        logger.error(f'can not access sub_entity not listed in available sub_entities!')
        raise ModelRetry(
            f"Requested sub_entity: {sub_entity} is not available for workflow path. " +
            f"Use tool get_available_sub_entities() to see what sub_entities are available to query for current " +
            f"workflow path." 
        )        

    select = []
    if 'select' in params.keys():
        select = params.pop('select')
        # it's probably always a string here but jik...
        if isinstance(select, str):
            select = [s.strip() for s in select.split(',')]

    if not select and 'size' in params.keys() and int(params['size']) > MAX_PAGE_SIZE_NO_SELECT_FILTER:
        size_arg = params['size']
        logger.warning(
            f'prevented attempt to execute api call without select filtering and with size {size_arg} '
            f'larger than {MAX_PAGE_SIZE_NO_SELECT_FILTER}'
        )
        raise ModelRetry(
            f"Can not make api call that does not employ 'select' argument to filter record size AND employs " +
            f"page size parameter greater than {MAX_PAGE_SIZE_NO_SELECT_FILTER}. " 
        )
    
    if select and 'size' in params.keys() and int(params['size']) > MAX_PAGE_SIZE_WITH_SELECT_FILTER:
        size_arg = params['size']
        logger.warning(
            f'prevented attempt to execute api call with select filtering and with size {size_arg} '
            f'larger than {MAX_PAGE_SIZE_WITH_SELECT_FILTER}'
        )
        raise ModelRetry(
            f"Can not make api call that does employs 'select' argument to filter record size AND employs " +
            f"page size parameter greater than {MAX_PAGE_SIZE_WITH_SELECT_FILTER}. " 
        )    

    with httpx.Client() as client:
        r = client.get(
            url,
            params=params or {},
            timeout=180.0 #seconds
        )

    if not r.is_success:
        logger.error(f'error response detected! response is: {r}')
        return {'status_code': r.status_code}

    rv = r.json()

    if len(rv['data']) == 0:
        logger.warning(f'api call resulted in empty data')
        return rv

    rv_select_content = [
        {k: record[k] for k in record if k != 'packageIndexes' or 'packageIndexes' not in record} 
        for record 
        in rv['data']['titlePage']['content']
    ]
    rv['data']['titlePage']['content'] = rv_select_content

    if len(select) != 0:
        logger.info(f'filtering payload with select: {select}')

        rv_select_content = [
            {k: record[k] for k in select if k in record} 
            for record
            in rv['data']['titlePage']['content']
        ]
        #logger.info(f'rv is {rv}')
        rv['data']['titlePage']['content'] = rv_select_content
    
    payload_tokens = rough_token_estimate(rv)

    if payload_tokens > MAX_SAFE_PAYLOAD_TOKENS:
        logger.warning(
            f"Payload too large for model context: "
            f"{payload_tokens} tokens > {MAX_SAFE_PAYLOAD_TOKENS}"
        )
        raise ModelRetry(
            "API response payload is too large for the model context window. "
            "Reduce `size`, add more selective `select` filters, or paginate."
        )

    logger.info(f'api return payload after select and package_index filtering is: {rv}')
    return rv



@patch_agent.tool
@notify_slack(":bar_chart:", "Generating multi-series chart...")
def generate_multi_series_chart(
    ctx: RunContext,
    *,
    series: List[Dict[str, Any]],
    # Each series item must be:
    # {
    #   "label": "Datasource Count",
    #   "data": Dict[str, float]  # category -> value
    # }
    title: str = "PatchFox Comparison",
    x_label: str = "",
    y_label: str = "",
    figsize: Tuple[int, int] = (12, 6),
    top_n: Optional[int] = None,
    normalize: bool = False,         # if True, each category shows % (per-category across series)
    sort_by: Literal["sum","first","alpha"] = "sum",  # order categories
    annotate: bool = True,           # print values on bars for small N
    decimals: int = 0                # value label precision (ignored if normalize=True → forces 1 decimal %)
) -> str:
    """
    Render multiple series on the same categorical axis as grouped bars.
    - 'series' is a list of {label, data{category->value}}.
    - Unifies categories across series; missing values become 0.
    - 'normalize=True' shows each category as percentages split across series (100% per category).
    - Stores PNG bytes into ctx.deps.chart_data for Slack upload.
    """
    try:
        if not series or any("label" not in s or "data" not in s for s in series):
            raise ModelRetry("Each series must have 'label' and 'data' (dict of category->value).")

        # All categories seen across all series
        all_cats = set()
        for s in series:
            all_cats.update(s["data"].keys())
        if not all_cats:
            raise ModelRetry("No categories to plot.")

        # Build a matrix categories x series
        cats = sorted(list(all_cats))
        # Sort categories
        if sort_by == "sum":
            # Sum across series
            sums = {c: sum(float(s["data"].get(c, 0) or 0) for s in series) for c in cats}
            cats.sort(key=lambda c: sums[c], reverse=True)
        elif sort_by == "first":
            # Use ordering of first series descending
            first = series[0]["data"]
            cats.sort(key=lambda c: float(first.get(c, 0) or 0), reverse=True)
        else:  # alpha
            cats.sort(key=lambda c: str(c).lower())

        # top_n clipping
        if top_n and len(cats) > top_n:
            cats = cats[:top_n]

        values = []
        for s in series:
            values.append([float(s["data"].get(c, 0) or 0) for c in cats])
        # values: list per series, each a list per category

        # Normalize to percentages per category if requested
        if normalize:
            for j, c in enumerate(cats):
                col_sum = sum(v[j] for v in values)
                for i in range(len(values)):
                    values[i][j] = (values[i][j] / col_sum * 100.0) if col_sum > 0 else 0.0

        # Plot grouped bars
        n_series = len(series)
        n_cats = len(cats)
        x = np.arange(n_cats)
        total_group_width = 0.80
        bar_width = total_group_width / max(1, n_series)
        offsets = (np.arange(n_series) - (n_series - 1) / 2.0) * bar_width

        fig, ax = plt.subplots(figsize=figsize)

        bar_containers = []
        for i, s in enumerate(series):
            ys = values[i]
            bars = ax.bar(x + offsets[i], ys, width=bar_width, label=s["label"])
            bar_containers.append((s["label"], bars, ys))

        ax.set_title(title, fontsize=14, fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels(cats, rotation=45, ha='right')
        ax.set_xlabel(x_label)
        ax.set_ylabel(y_label if not normalize else "Percent")

        # Add legend
        ax.legend(loc="best", frameon=False)

        # Annotate values for small charts
        if annotate and n_cats * n_series <= 60:
            fmt = (lambda v: f"{v:.1f}%" if normalize else f"{v:,.{decimals}f}")
            for label, bars, ys in bar_containers:
                for bar, val in zip(bars, ys):
                    if val == 0:
                        continue
                    ax.annotate(
                        fmt(val),
                        xy=(bar.get_x() + bar.get_width()/2, bar.get_height()),
                        xytext=(0, 3),
                        textcoords="offset points",
                        ha="center", va="bottom", fontsize=8
                    )

        plt.tight_layout()

        # Encode and stash for Slack
        buf = io.BytesIO()
        plt.savefig(buf, format="png", dpi=150, bbox_inches="tight")
        buf.seek(0)
        plt.close()

        n_series = len(series)
        n_cats = len(cats)
        # ...
        ctx.deps.chart_data = {
            "image_bytes": buf.getvalue(),
            "filename": "multi_series_bar.png",
            "mime": "image/png",
            "title": title,
            "data_points": n_series * n_cats,    # <-- add this
            "meta": {
                "type": "multi_series_bar",
                "series_labels": [s["label"] for s in series],
                "categories": cats,
                "n_series": n_series,
                "n_categories": n_cats,
                "normalize": normalize,
                "top_n": top_n,
                "sort_by": sort_by,
            },
        }
        return f"📊 Generated multi-series grouped bar chart '{title}' with {n_series} series across {n_cats} categories."

    except ModelRetry:
        raise
    except Exception as e:
        return f"❌ Multi-series chart generation failed: {str(e)}"



def _abbr(n: float) -> str:
    try:
        n = float(n)
    except Exception:
        return str(n)
    sign = "-" if n < 0 else ""
    n = abs(n)
    for k, sfx in NUM_FMT_ABBRS:
        if n >= k:
            return f"{sign}{n / k:.2f}{sfx}"
    return f"{sign}{n:.0f}"


def _is_datetime_series(xs: List[Any]) -> bool:
    if not xs: 
        return False
    sample = xs[min(3, len(xs)-1)]
    if isinstance(sample, (datetime, )):
        return True
    if isinstance(sample, str):
        for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
            try:
                datetime.strptime(sample, fmt); return True
            except Exception:
                pass
    return False


def _parse_datetime(x: Any) -> Any:
    if isinstance(x, datetime):
        return x
    if isinstance(x, str):
        for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
            try:
                return datetime.strptime(x, fmt)
            except Exception:
                continue
    return x  # fallback; let matplotlib place it


@patch_agent.tool
@notify_slack(":bar_chart:", "Generating charts and graphs...")
def generate_chart(
    ctx: RunContext,
    data: dict,
    chart_type: Literal["line", "bar", "pie", "scatter", "histogram"] = "bar",
    x_field: Optional[str] = None,
    y_field: Optional[str] = None,
    *,
    group_by: Optional[str] = None,
    agg: Literal["sum", "mean", "count"] = "sum",
    top_n: Optional[int] = None,
    log_y: bool = False,
    title: str = "PatchFox Data Visualization",
    x_label: str = "",
    y_label: str = "",
    figsize: tuple[int, int] = (10, 6)
) -> str:
    """
    Smarter chart generator w/ grouping, timeseries handling, and safe defaults.
    - If group_by is set (usually equals x_field), aggregates y_field with agg.
    - For pie/bar, you can limit clutter with top_n.
    - Automatically formats large numbers and dates.
    - Stores image bytes + metadata in ctx.deps.chart_data for Slack upload.
    """
    try:
        records = data.get('data', {}).get('titlePage', {}).get('content', [])
        if not records:
            raise ModelRetry("No data records found for chart generation")

        if chart_type in {"line", "bar", "scatter"} and (not x_field or not y_field):
            raise ModelRetry(f"{chart_type} chart requires both x_field and y_field")

        # Build a working table
        rows: List[Dict[str, Any]] = []
        for r in records:
            row = {}
            if x_field: row["x"] = r.get(x_field)
            if y_field: row["y"] = r.get(y_field, 0) or 0
            if group_by: row["g"] = r.get(group_by)
            rows.append(row)

        # Group/Aggregate if requested
        if group_by:
            buckets: Dict[Any, List[float]] = {}
            for row in rows:
                g = row.get("g")
                buckets.setdefault(g, []).append(float(row.get("y", 0)))
            xs, ys = [], []
            for g, vals in buckets.items():
                if agg == "sum":
                    v = sum(vals)
                elif agg == "mean":
                    v = sum(vals) / max(1, len(vals))
                else:  # count
                    v = len(vals)
                xs.append(g)
                ys.append(v)
        else:
            xs = [row.get("x") for row in rows] if x_field else []
            ys = [row.get("y") for row in rows] if y_field else []

        # Timeseries handling
        if x_field and _is_datetime_series(xs):
            xs = [_parse_datetime(x) for x in xs]
            # sort pairs by time (important for line)
            if chart_type in {"line", "scatter"}:
                pairs = sorted(zip(xs, ys), key=lambda p: p[0] if p[0] is not None else datetime.min)
                xs, ys = [p[0] for p in pairs], [p[1] for p in pairs]

        # Top-N slicing (pie/bar clutter control)
        if top_n and chart_type in {"bar", "pie"} and len(xs) > top_n:
            pairs = list(zip(xs, ys))
            pairs.sort(key=lambda p: (p[1] if p[1] is not None else -math.inf), reverse=True)
            head, tail = pairs[:top_n], pairs[top_n:]
            xs = [h[0] for h in head]
            ys = [h[1] for h in head]
            if chart_type == "pie" and tail:
                xs.append("Other")
                ys.append(sum(t[1] for t in tail if t[1] is not None))

        # Plot
        fig, ax = plt.subplots(figsize=figsize)

        if chart_type == "line":
            ax.plot(xs, ys, marker='o')
        elif chart_type == "bar":
            ax.bar(xs, ys)
            # Rotate if categories are long
            ax.tick_params(axis='x', labelrotation=45)
        elif chart_type == "pie":
            labels = [str(x) for x in xs] if xs else [f"Item {i+1}" for i in range(len(ys))]
            ax.pie(ys, labels=labels, autopct='%1.1f%%', pctdistance=0.8)
        elif chart_type == "scatter":
            ax.scatter(xs, ys)
        elif chart_type == "histogram":
            # Histogram uses y_field (or x_field if y missing)
            vals = ys if y_field else xs
            ax.hist(vals, bins=20, edgecolor='black')

        # Scales & formatters
        if chart_type != "pie":
            ax.set_title(title, fontsize=14, fontweight='bold')
            if x_label or x_field: ax.set_xlabel(x_label or x_field or "")
            if y_label or y_field: ax.set_ylabel(y_label or y_field or "")

            if log_y:
                ax.set_yscale('log')

            # Human-friendly y tick labels
            def fmt_y(val, pos=None):
                return _abbr(val)
            ax.yaxis.set_major_formatter(mtick.FuncFormatter(lambda v, p: fmt_y(v)))

            # Datetime ticks
            if x_field and _is_datetime_series(xs):
                ax.xaxis.set_major_locator(mdates.AutoDateLocator())
                ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(mdates.AutoDateLocator()))
                fig.autofmt_xdate()

        plt.tight_layout()

        # Encode image
        img_buffer = io.BytesIO()
        plt.savefig(img_buffer, format='png', dpi=150, bbox_inches='tight')
        img_buffer.seek(0)
        plt.close()

        # after computing ys/xs and saving the PNG...
        n_points = len(y_values) if "y_values" in locals() else (len(values) if chart_type in {"pie","histogram"} else 0)

        ctx.deps.chart_data = {
            "image_bytes": img_buffer.getvalue(),
            "filename": f"{chart_type}_chart.png",
            "mime": "image/png",
            "title": title,
            "data_points": n_points,             # <-- add this
            "meta": {
                "chart_type": chart_type,
                "points": n_points,              # keep for completeness
                "x_field": x_field,
                "y_field": y_field,
                "group_by": group_by if 'group_by' in locals() else None,
                "agg": agg if 'agg' in locals() else None,
            },
        }

        return f"📊 Generated {chart_type} chart '{title}' ({ctx.deps.chart_data['meta']})"

    except ModelRetry:
        raise  # bubble up with your existing behavior
    except Exception as e:
        return f"❌ Chart generation failed: {str(e)}"


# --- Markdown table tool ------------------------------------------------------
from typing import List, Optional, Literal, Any
from pydantic_ai import RunContext

@patch_agent.tool
def make_markdown_table(
    ctx: RunContext[ChatState],
    headers: List[str],
    rows: List[List[Any]],
    align: Optional[List[Literal["left","center","right"]]] = None,
    percent_cols: Optional[List[int]] = None,
    bold_total_row: bool = False,
    title: Optional[str] = None,
) -> str:
    """
    Generate a GitHub-style Markdown table with a header row (always).
    The string returned is valid Markdown. We also stash it in ctx.deps.metadata['last_md_table']
    so the Slack layer can render it even if the model forgets to echo the returned string.
    """
    def is_num(x: Any) -> bool:
        try:
            float(str(x).replace(",", "").replace("%", ""))
            return True
        except Exception:
            return False

    def fmt_num(x: Any) -> str:
        if isinstance(x, int):
            return f"{x:,}"
        try:
            v = float(str(x).replace(",", "").replace("%", ""))
            s = f"{v:,.3f}".rstrip("0").rstrip(".")
            return s
        except Exception:
            return str(x)

    def fmt_pct(x: Any) -> str:
        s = str(x).strip()
        if s.endswith("%"):
            return s
        try:
            v = float(str(x).replace(",", "").replace("%", ""))
            if 0.0 <= v <= 1.0:
                v *= 100.0
            s = f"{v:.1f}%"
            return s.replace(".0%", "%")
        except Exception:
            return str(x)

    cols = len(headers)
    rows = [list(r[:cols]) + [""] * max(0, cols - len(r)) for r in rows]

    # default alignment: numbers right, otherwise left
    if align is None:
        align = []
        for j in range(cols):
            sample = next((r[j] for r in rows if str(r[j]).strip() != ""), headers[j])
            align.append("right" if is_num(sample) else "left")
    else:
        align = (align + ["left"] * cols)[:cols]

    pct_set = set(percent_cols or [])
    for i in range(len(rows)):
        for j in range(cols):
            if j in pct_set:
                rows[i][j] = fmt_pct(rows[i][j])
            elif is_num(rows[i][j]):
                rows[i][j] = fmt_num(rows[i][j])
            else:
                rows[i][j] = str(rows[i][j])

    if bold_total_row and rows:
        rows[-1] = [f"**{c}**" if str(c).strip() else c for c in rows[-1]]

    def align_marker(a: str) -> str:
        return { "left": ":---", "center": ":---:", "right": "---:" }.get(a, ":---")

    header_line = "| " + " | ".join(h.strip() or f"Column {i+1}" for i, h in enumerate(headers)) + " |"
    sep_line    = "| " + " | ".join(align_marker(a) for a in align) + " |"
    body_lines  = ["| " + " | ".join(r) + " |" for r in rows]

    parts = []
    if title:
        parts.append(f"**{title}**")
    parts.extend([header_line, sep_line, *body_lines])

    md = "\n".join(parts)

    # Make it visible to the Slack layer even if the model doesn't echo the return.
    ctx.deps.metadata.setdefault("last_md_tables", []).append(md)
    return md
