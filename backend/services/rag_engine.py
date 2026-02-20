"""
RAG Engine – LangChain + ChromaDB pipeline for RBI policy retrieval.
Indexes local policy text files at startup and retrieves relevant clauses
per agent utterance during compliance analysis.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document


CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")
EMBED_MODEL = "models/gemini-embedding-001"
COLLECTION_RBI = "rbi_policies"
COLLECTION_CLIENT = "client_rules"


# ---------------------------------------------------------------------------
# Global retriever (initialized once at startup)
# ---------------------------------------------------------------------------

_rbi_vectorstore: Optional[Chroma] = None


def get_embeddings(api_key: str) -> GoogleGenerativeAIEmbeddings:
    return GoogleGenerativeAIEmbeddings(
        model=EMBED_MODEL,
        google_api_key=api_key,
    )


def initialize_policy_store(policies_dir: str, api_key: str) -> Chroma:
    """
    Load all .txt policy files, chunk them, embed with Google embeddings,
    and persist to ChromaDB. Returns the Chroma vectorstore.
    Called ONCE at FastAPI startup.
    """
    global _rbi_vectorstore

    embeddings = get_embeddings(api_key)
    persist_path = str(Path(CHROMA_PERSIST_DIR) / COLLECTION_RBI)

    # If persisted store already exists, reload it
    if Path(persist_path).exists():
        print(f"[RAG] Loading existing ChromaDB from {persist_path}")
        _rbi_vectorstore = Chroma(
            collection_name=COLLECTION_RBI,
            embedding_function=embeddings,
            persist_directory=persist_path,
        )
        count = _rbi_vectorstore._collection.count()
        print(f"[RAG] Loaded {count} policy chunks from cache.")
        return _rbi_vectorstore

    # Build fresh store from policy .txt files
    print(f"[RAG] Building policy vector store from: {policies_dir}")
    policy_path = Path(policies_dir)
    documents: list[Document] = []

    for txt_file in sorted(policy_path.glob("*.txt")):
        loader = TextLoader(str(txt_file), encoding="utf-8")
        docs = loader.load()
        for doc in docs:
            doc.metadata["source"] = txt_file.name
        documents.extend(docs)
        print(f"[RAG]   Loaded: {txt_file.name} ({len(docs)} docs)")

    if not documents:
        raise RuntimeError(f"No .txt policy files found in {policies_dir}")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=60,
        separators=["\n\n", "\n", ". ", " "],
    )
    chunks = splitter.split_documents(documents)
    print(f"[RAG] Split into {len(chunks)} chunks. Embedding now...")

    _rbi_vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        collection_name=COLLECTION_RBI,
        persist_directory=persist_path,
    )
    print(f"[RAG] Policy store built and persisted to {persist_path}")
    return _rbi_vectorstore


def load_client_rules(client_config: dict, api_key: str) -> Optional[Chroma]:
    """
    Convert client config rules to LangChain Documents and store in ChromaDB.
    Returns a Chroma retriever or None if no custom rules exist.
    """
    custom_rules = client_config.get("custom_rules", [])
    risk_triggers = client_config.get("risk_triggers", [])

    if not custom_rules and not risk_triggers:
        return None

    embeddings = get_embeddings(api_key)
    documents: list[Document] = []

    # Add custom rules as documents
    for rule in custom_rules:
        content = (
            f"CLAUSE {rule.get('rule_id', 'CUSTOM-XX')}: {rule.get('rule_name', '')}\n"
            f"{rule.get('description', '')}"
        )
        documents.append(
            Document(
                page_content=content,
                metadata={
                    "clause_id": rule.get("rule_id", "CUSTOM-XX"),
                    "rule_name": rule.get("rule_name", ""),
                    "source": "client_config",
                },
            )
        )

    # Add risk triggers as documents
    for trigger in risk_triggers:
        content = f"RISK TRIGGER: {trigger} — Any agent behaviour constituting '{trigger}' is a policy violation."
        documents.append(
            Document(
                page_content=content,
                metadata={
                    "clause_id": "CLIENT-TRIGGER",
                    "rule_name": trigger,
                    "source": "client_config",
                },
            )
        )

    if not documents:
        return None

    client_store = Chroma.from_documents(
        documents=documents,
        embedding=embeddings,
        collection_name=COLLECTION_CLIENT,
        # Use in-memory (no persist) – ephemeral per request
    )
    print(f"[RAG] Client rules vectorstore built with {len(documents)} entries.")
    return client_store


def retrieve_relevant_clauses(
    transcript_threads: list[dict],
    api_key: str,
    client_config: Optional[dict] = None,
) -> list[dict]:
    """
    For each AGENT utterance, retrieve matching policy clauses from RBI store
    and optionally the client rule store.

    Returns a deduplicated list of:
    [
        {
            "clause_id": ...,
            "rule_name": ...,
            "description": ...,
            "source": ...
        }
    ]
    """
    global _rbi_vectorstore

    if _rbi_vectorstore is None:
        print("[RAG] WARNING: Policy store not initialized. Returning empty clauses.")
        return []

    rbi_retriever = _rbi_vectorstore.as_retriever(search_kwargs={"k": 3})

    client_store = None
    if client_config:
        client_store = load_client_rules(client_config, api_key)
    client_retriever = client_store.as_retriever(search_kwargs={"k": 2}) if client_store else None

    agent_messages = [
        t["message"]
        for t in transcript_threads
        if t.get("speaker", "").lower() == "agent" and t.get("message")
    ]

    seen_clauses: set[str] = set()
    clauses: list[dict] = []

    for message in agent_messages:
        # Query RBI store
        try:
            rbi_docs = rbi_retriever.invoke(message)
            for doc in rbi_docs:
                meta = doc.metadata
                clause_id = meta.get("clause_id", _extract_clause_id(doc.page_content))
                if clause_id not in seen_clauses:
                    seen_clauses.add(clause_id)
                    clauses.append(
                        {
                            "clause_id": clause_id,
                            "rule_name": meta.get("rule_name", _extract_rule_name(doc.page_content)),
                            "description": doc.page_content[:300],
                            "source": meta.get("source", "rbi_policies"),
                        }
                    )
        except Exception as exc:
            print(f"[RAG] RBI retrieval error: {exc}")

        # Query client store
        if client_retriever:
            try:
                client_docs = client_retriever.invoke(message)
                for doc in client_docs:
                    meta = doc.metadata
                    clause_id = meta.get("clause_id", "CLIENT-XX")
                    key = f"CLIENT-{meta.get('rule_name', clause_id)}"
                    if key not in seen_clauses:
                        seen_clauses.add(key)
                        clauses.append(
                            {
                                "clause_id": clause_id,
                                "rule_name": meta.get("rule_name", "Client Rule"),
                                "description": doc.page_content[:300],
                                "source": "client_config",
                            }
                        )
            except Exception as exc:
                print(f"[RAG] Client retrieval error: {exc}")

    print(f"[RAG] Retrieved {len(clauses)} unique relevant clauses.")
    return clauses


def _extract_clause_id(text: str) -> str:
    """Extract CLAUSE ID from raw policy text chunk."""
    import re
    match = re.search(r"CLAUSE\s+([\w-]+):", text)
    return match.group(1) if match else "UNKNOWN"


def _extract_rule_name(text: str) -> str:
    """Extract rule name after CLAUSE ID."""
    import re
    match = re.search(r"CLAUSE\s+[\w-]+:\s*(.+)", text)
    if match:
        return match.group(1).strip()[:80]
    return "Policy Clause"
