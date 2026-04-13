# =========================================================================================================
# Plain English SQL Explainer
# A simple Streamlit app that explains complex SQL queries in plain English.
# =========================================================================================================

import anthropic
import streamlit as st
from dotenv import load_dotenv
import sqlglot
from sqlglot import exp

# Load environment variables from .env file (specifically the ANTHROPIC_API_KEY)
load_dotenv()

# ── 1. PAGE CONFIG ────────────────────────────────────────────────────
# Set the browser tab title and layout
st.set_page_config(
    page_title = "Plain English SQL Explainer",
    layout="wide"
)

# ── 2. CUSTOM CSS ─────────────────────────────────────────────────────
# Injects custom fonts and styling via a <style> block.
# unsafe_allow_html=True is required to render raw HTML/CSS
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&family=DM+Sans:wght@300;400;500&display=swap');
 
        /* Apply DM Sans as the default font across all Streamlit elements */
        html, body, [class*="css"] {
            font-family: 'DM Sans', sans-serif;
        }
 
        /* Make Streamlit's default top header bar transparent so it doesn't clash */
        header[data-testid="stHeader"] {
            background-color: transparent;
        }
 
        /* Dark background for the sidebar with a subtle right border */
        [data-testid="stSidebar"] {
            background-color: #0d0d0d;
            border-right: 1px solid #222;
        }
 
        /* Force all sidebar text to light color so it's readable on dark background */
        [data-testid="stSidebar"] * {
            color: #e0e0e0 !important;
        }
 
        /* Style the labels for the dialect selector and file uploader in the sidebar */
        [data-testid="stSidebar"] .stSelectbox label,
        [data-testid="stSidebar"] .stFileUploader label {
            font-family: 'JetBrains Mono', monospace !important;
            font-size: 0.75rem !important;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: #888 !important;
        }
 
        /* Main content area: limit width to 860px for readability, add vertical padding */
        .block-container {
            padding-top: 2rem !important;
            padding-bottom: 2rem !important;
            max-width: 860px;
        }
 
        /* App title styling — monospace font gives it a developer/code tool feel */
        .app-title {
            font-family: 'JetBrains Mono', monospace;
            font-size: 1.6rem;
            font-weight: 600;
            color: #f0f0f0;
            letter-spacing: -0.02em;
            margin-bottom: 2px;
        }
 
        /* Subtitle — smaller, muted color to sit below the title without competing */
        .app-subtitle {
            font-family: 'DM Sans', sans-serif;
            font-size: 0.9rem;
            color: #555;
            margin-bottom: 0;
        }
 
        /* Sidebar title text */
        .sidebar-title {
            font-family: 'JetBrains Mono', monospace;
            font-size: 1.1rem;
            font-weight: 600;
            color: #f0f0f0;
            margin-bottom: 0.2rem;
        }
 
        /* Thin horizontal rule used as a visual separator inside the sidebar */
        .sidebar-divider {
            border: none;
            border-top: 1px solid #222;
            margin: 1.2rem 0;
        }
 
        /* Small hint/instruction text at the bottom of the sidebar */
        .sidebar-hint {
            font-size: 0.78rem;
            color: #444 !important;
            font-family: 'JetBrains Mono', monospace;
            line-height: 1.5;
        }
 
        /* Reduce font size of code previews shown in the sidebar */
        [data-testid="stSidebar"] .stCode {
            font-size: 0.72rem;
        }
 
        /* Style each chat bubble — dark background with subtle border and rounded corners */
        [data-testid="stChatMessage"] {
            background-color: #111 !important;
            border: 1px solid #1e1e1e;
            border-radius: 8px;
            margin-bottom: 0.5rem;
        }
    </style>
""", unsafe_allow_html=True)

# ── 3. ANTHROPIC CLIENT ───────────────────────────────────────────────
# Instantiate the Anthropic client
client = anthropic.Anthropic()

# ── 4. SYSTEM PROMPT ──────────────────────────────────────────────────

SYSTEM_PROMPT = """
You are an experienced SQL Developer with expertise writing SQL queries in multiple SQL dialects - Snowflake, Oracle, 
PostgreSQL, SQL Server. You are also an expert at performing query tuning and improving the overall performance of the
query. When the user shares a piece of code in any of the dialects by either pasting the code or uploading a SQL file, 
you respond by clearly explaining what the code does in plain English. You are friendly and you analzye and tell them how 
efficient the code is and what improvement can be made based on query tuning. The code is broken down using sqlglot and you use
these broken pieces to describe them piece by piece.

Always respond in this exact format and nothing else, line by line and not all in the same line as a paragraph:

What the code does: <explanation, broken down by each block instead of all at once>
Code Review: <describe how efficient the code is>
Improvements: <performance improvement ideas if any>

Your job is to also respond to any following questions the user may have
"""

# ── 5. HELPER FUNCTIONS ────────────────────────────────────────────────

def add_user_message(prompt: str):
    """
    Appends the user's message to the full API conversation history.
    This history is what gets sent to Claude on every turn — it's how
    Claude maintains context across multiple messages.
    Note: user messages are NOT added to display_messages here because
    they are rendered directly in the chat at the point of submission.
    """
    st.session_state.messages.append({"role": "user", "content": prompt})
    
def add_claude_response(response: str):
    """
    Appends Claude's response to BOTH conversation histories:
    - messages: the full API history passed to Claude each turn
    - display_messages: the history rendered in the chat UI on each rerun
    """
    st.session_state.messages.append({"role": "assistant", "content": response})
    st.session_state.display_messages.append({"role": "assistant", "content": response})

def sql_to_english() -> str:
    """
    Sends the full conversation history to Claude and returns its response.
    Passing the entire history (not just the latest message) is what enables
    multi-turn conversation — Claude can see everything said so far.

    Returns
    -------
    str
        Claude's plain-English explanation of the SQL query.
    """
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=600,              
        system=SYSTEM_PROMPT,        
        messages=st.session_state.messages  
    )
    
    return message.content[0].text

# ── 6. SESSION STATE INITIALIZATION ──────────────────────────────────
# Streamlit reruns the entire script on every user interaction.
# session_state persists data across reruns, without it, all history
# would be wiped on every keypress or button click.

# messages: the full conversation history sent to the Claude API each turn.
# Includes both user and assistant turns to maintain multi-turn context.
if "messages" not in st.session_state:
    st.session_state.messages = []

# display_messages: a separate list used only for rendering the chat UI.
# Unlike `messages`, user messages are added here at render time (not via add_user_message),
# while assistant messages are added via add_claude_response.
# This separation exists because the API receives a structured prompt (the sqlglot breakdown)
# as the user message, but we want to show the raw SQL to the user in the chat — not the breakdown.
if "display_messages" not in st.session_state:
    st.session_state.display_messages = []

# pending_file_input: holds SQL content from an uploaded file between reruns.
# Set when a new file is detected, consumed (and cleared) when processed.
# This prevents the file from being re-submitted on every Streamlit rerun.
if "pending_file_input" not in st.session_state:
    st.session_state.pending_file_input = None

# last_uploaded_file: tracks the filename of the most recently uploaded file.
# Used to detect when a NEW file has been uploaded vs. the same file still being present.
if "last_uploaded_file" not in st.session_state:
    st.session_state.last_uploaded_file = None

# ── 7. SIDEBAR ────────────────────────────────────────────────────────
# The sidebar holds the dialect selector and file uploader.
# All content inside `with st.sidebar:` renders in the left panel.
with st.sidebar:
    st.markdown('<div class="sidebar-title">⬡ SQL Explainer</div>', unsafe_allow_html=True)
    st.markdown('<div class="app-subtitle">Plain English • Query Analysis</div>', unsafe_allow_html=True)
    st.markdown('<hr class="sidebar-divider">', unsafe_allow_html=True)
 
    # The chosen dialect is passed to sqlglot for accurate parsing
    # index=None means nothing is pre-selected, forcing the user to choose before submitting
    dialect = st.selectbox(
        "SQL Dialect",
        ("Snowflake", "Oracle", "PostgreSQL", "SQL Server"),
        index=None,
        placeholder="Select dialect...",
    )
 
    st.markdown('<hr class="sidebar-divider">', unsafe_allow_html=True)

    # File uploader that accepts .sql and .txt files only
    uploaded_file = st.file_uploader("Upload a .sql or .txt file (optional)", type=["sql", "txt"])
    sql_from_file = None

    if uploaded_file is not None:
        # Only process the file if it's a NEW upload (different filename from last time).
        # Without this check, Streamlit would re-trigger the file on every rerun
        # because the file widget persists in the sidebar across reruns.
        if st.session_state.last_uploaded_file != uploaded_file.name:
            st.session_state.last_uploaded_file = uploaded_file.name
            # Decode the binary file content to a UTF-8 string and store it
            # in pending_file_input to be picked up by the input processing block below
            st.session_state.pending_file_input = uploaded_file.getvalue().decode("utf-8")

        # Show a preview of the uploaded file content in the sidebar
        if st.session_state.pending_file_input:
            st.markdown('<hr class="sidebar-divider">', unsafe_allow_html=True)
            st.markdown('<p class="sidebar-hint">📄 File preview:</p>', unsafe_allow_html=True)
            st.code(st.session_state.pending_file_input, language="sql")
    else:
        # If file was removed from the uploader then reset both tracking variables
        # so a fresh upload of the same filename will be treated as new
        st.session_state.last_uploaded_file = None
        st.session_state.pending_file_input = None

    st.markdown('<hr class="sidebar-divider">', unsafe_allow_html=True)
    st.markdown('<p class="sidebar-hint">Paste SQL in the chat below, or upload a file above. Select your dialect before submitting.</p>', unsafe_allow_html=True)

# ── 8. MAIN AREA HEADER ───────────────────────────────────────────────
st.markdown('<div class="app-title">Plain English SQL Explainer</div>', unsafe_allow_html=True)
st.markdown('<div class="app-subtitle">Upload or paste your SQL — I\'ll break it down in simple English</div>', unsafe_allow_html=True)
st.markdown("---")

# ── 9. SQLGLOT PARSING FUNCTIONS ──────────────────────────────────────
# These functions use sqlglot to break the SQL into structured components
# before sending to Claude. This gives Claude a clean, clause-by-clause
# breakdown rather than raw SQL, resulting in more precise explanations.

def extract_select(select: exp.Select):
    """
    Extracts all meaningful clauses from a single SELECT statement node
    and returns them as a dictionary of clause name → SQL string.

    Parameters
    ----------
    select : exp.Select
        A sqlglot SELECT expression node from the parsed AST.

    Returns
    -------
    dict
        Keys are clause names (select, from, joins, where, etc.)
        Values are SQL strings, or None if the clause is absent.
    """
    return {
        "select": [e.sql() for e in select.expressions],   # Column list

        "from": select.args.get("from").sql()
        if select.args.get("from") else None,               # Source table(s)

        "joins": [
            j.sql() for j in select.args.get("joins", [])  # All JOIN clauses
        ],

        "where": select.args.get("where").sql()
        if select.args.get("where") else None,              # Filter condition

        "group_by": select.args.get("group").sql()
        if select.args.get("group") else None,              # Grouping columns

        "having": select.args.get("having").sql()
        if select.args.get("having") else None,             # Post-aggregation filter

        "order_by": select.args.get("order").sql()
        if select.args.get("order") else None,              # Sort order

        "limit": select.args.get("limit").sql()
        if select.args.get("limit") else None,              # Row limit
    }


def extract_ctes(expression):
    """
    Extracts all CTEs (Common Table Expressions) from a WITH clause.
    CTEs are named subqueries defined before the main SELECT — e.g.:
        WITH cte_name AS (SELECT ...)

    Parameters
    ----------
    expression : sqlglot expression
        The root of the parsed SQL AST.

    Returns
    -------
    list of dict
        Each dict has 'name' (the CTE alias) and 'query' (the CTE SQL body).
    """
    ctes = []
    with_clause = expression.args.get("with")

    if with_clause:
        for cte in with_clause.expressions:
            ctes.append({
                "name": cte.alias,          
                "query": cte.this.sql(),    
            })

    return ctes

def extract_all_queries(sql: str, dialect: str = None):
    """
    Parses the full SQL string using sqlglot and extracts all CTEs
    and SELECT blocks into a structured dictionary.

    Parameters
    ----------
    sql : str
        The raw SQL query string to parse.
    dialect : str, optional
        The SQL dialect (e.g. 'snowflake', 'oracle') for accurate parsing.

    Returns
    -------
    dict
        {
            "ctes": [...],      # List of CTE dicts from extract_ctes()
            "selects": [...]    # List of SELECT clause dicts from extract_select()
        }
    """
    # parse_one builds an AST (Abstract Syntax Tree) from the SQL string
    tree = sqlglot.parse_one(sql, dialect=dialect)
    
    result = {
        "ctes": extract_ctes(tree),
        "selects": []
    }
    
    # find_all traverses the entire AST and yields every SELECT node,
    # including nested subqueries and CTE bodies
    for select in tree.find_all(exp.Select):
        result["selects"].append(extract_select(select))
    
    return result

def build_breakdown_prompt(parsed: dict) -> str:
    """
    Converts the structured parsed SQL dictionary into a formatted text prompt
    that Claude can easily read and explain clause by clause.

    Parameters
    ----------
    parsed : dict
        The output of extract_all_queries() containing CTEs and SELECT blocks.

    Returns
    -------
    str
        A human-readable, line-by-line breakdown of the SQL structure,
        ready to be inserted into the Claude API messages payload.
    """
    lines = ["Break down this SQL query clause by clause:\n"]

    # List CTEs first — they're defined before the main query and provide context
    if parsed["ctes"]:
        lines.append("CTEs (WITH clauses):")
        for cte in parsed["ctes"]:
            lines.append(f"  - {cte['name']}: {cte['query']}")

    # Then list each SELECT block (there may be multiple for subqueries)
    for i, select in enumerate(parsed["selects"]):
        lines.append(f"\nSELECT block {i+1}:")
        if select["select"]:
            lines.append(f"  SELECT: {', '.join(select['select'])}")
        if select["from"]:
            lines.append(f"  FROM: {select['from']}")
        if select["joins"]:
            lines.append(f"  JOINs: {'; '.join(select['joins'])}")
        if select["where"]:
            lines.append(f"  WHERE: {select['where']}")
        if select["group_by"]:
            lines.append(f"  GROUP BY: {select['group_by']}")
        if select["having"]:
            lines.append(f"  HAVING: {select['having']}")
        if select["order_by"]:
            lines.append(f"  ORDER BY: {select['order_by']}")
        if select["limit"]:
            lines.append(f"  LIMIT: {select['limit']}")

    return "\n".join(lines)

# ── 10. DIALECT MAPPING ───────────────────────────────────────────────
# Maps the user-facing dropdown labels to sqlglot's internal dialect identifiers.
# sqlglot uses these lowercase strings to apply dialect-specific parsing rules.
DIALECT_MAP = {
    "Snowflake": "snowflake",
    "Oracle": "oracle",
    "PostgreSQL": "postgres",
    "SQL Server": "tsql"
}

# ── 11. DISPLAY CONVERSATION HISTORY ─────────────────────────────────
# Re-renders all past messages on every Streamlit rerun.
# Uses display_messages (not messages) so the user sees the raw SQL they typed,
# not the structured sqlglot breakdown that was actually sent to the API.
for msg in st.session_state.display_messages:
    if msg["role"] == "user":
        st.chat_message("user").write(msg["content"])
    else:
        st.chat_message("assistant").write(msg["content"])

# ── 12. INPUT RESOLUTION ──────────────────────────────────────────────
# Determines what the current user input is: from file upload or chat box.
# File upload takes priority: if a file was just uploaded (pending_file_input
# is set), use that and clear it so it doesn't re-trigger on the next rerun.
user_input = None

if st.session_state.pending_file_input:
    user_input = st.session_state.pending_file_input
    # Clear immediately so the same file content isn't submitted again on the next rerun
    st.session_state.pending_file_input = None

# Chat input always renders at the bottom and gives the user a text box
# for pasting SQL or asking follow-up questions after a file upload.
# The walrus operator (:=) assigns AND checks in one line
# only enters the if block if the user actually submitted something (not None/empty).
chat_input = st.chat_input("Paste your SQL code here...")
if chat_input and not user_input:
    # Only use chat input if no file input is already queued
    user_input = chat_input
 
# ── 13. INPUT PROCESSING + API CALL ──────────────────────────────────
if user_input:

    # Guard: require dialect selection before proceeding.
    # st.stop() halts the rest of the script for this rerun and nothing below executes.
    if not dialect:
        st.warning("Please select a SQL dialect in the sidebar before submitting.")
        st.stop()
 
    # Display the raw SQL in the chat immediately (before the API call)
    # and add it to display_messages so it persists on future reruns
    st.chat_message("user").write(user_input)
    st.session_state.display_messages.append({"role": "user", "content": user_input})
 
    try:
        # Attempt to parse the SQL with sqlglot and build a structured breakdown prompt.
        # This gives Claude a clean clause-by-clause view rather than raw SQL,
        # which produces more accurate and detailed explanations.
        parsed = extract_all_queries(user_input, dialect=DIALECT_MAP[dialect])
        breakdown_prompt = build_breakdown_prompt(parsed)
        # Add the structured breakdown (not raw SQL) to the API history
        add_user_message(f"[Dialect: {dialect}]\n\n{breakdown_prompt}")
    except Exception:
        # Fallback: if sqlglot can't parse the SQL (e.g. unsupported syntax),
        # send the raw SQL directly and Claude can still attempt an explanation
        add_user_message(f"[Dialect: {dialect}]\n\n{user_input}")
 
    # Call the Claude API and display the response
    with st.spinner("Analyzing your SQL..."):
        try:
            claude_response = sql_to_english()
            st.chat_message("assistant").write(claude_response)
            # Save to both histories so the response persists and Claude remembers it
            add_claude_response(claude_response)

        except anthropic.AuthenticationError:
            st.error("API key not found or invalid. Set ANTHROPIC_API_KEY in your environment.")

        except anthropic.RateLimitError:
            st.error("Rate limit hit. Please wait a moment and try again.")

        except Exception as e:
            st.error(f"Something went wrong: {e}")