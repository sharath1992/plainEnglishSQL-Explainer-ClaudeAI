# ⬡ Plain English SQL Explainer

An AI-powered conversational SQL analysis tool built with Python, Streamlit, and the Claude API.
Paste or upload a SQL query and the app will explain what it does, reviews its efficiency, and suggests improvements.

## 📸 Screenshot

<img width="2161" height="1261" alt="image" src="https://github.com/user-attachments/assets/73a44647-bba4-423d-9c6c-fc205f999665" />

## 💡 What It Does

- User pastes a SQL query or uploads a `.sql` / `.txt` file
- The query is parsed clause-by-clause using **sqlglot** before being sent to Claude
- Claude explains what the query does in plain English, broken down by each SQL block
- Claude also reviews query efficiency and suggests performance improvements
- Supports multi-turn conversation: ask follow-up questions about the query
- Supports 4 SQL dialects: **Snowflake, Oracle, PostgreSQL, SQL Server**

## 🧠 Key Concepts Practiced

- Combining a third-party parsing library (sqlglot) with an LLM for richer, more accurate responses
- Designing a two-layer messaging system: structured API messages vs. user-facing display messages
- Managing file uploads in Streamlit with session state to prevent re-triggering on reruns
- Multi-turn conversation history for follow-up question support
- Dialect-aware SQL parsing across four major SQL engines
