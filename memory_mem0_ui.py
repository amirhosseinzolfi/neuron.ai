"""Streamlit dashboard for browsing Mem0 memories and underlying Qdrant data.

Run with:  streamlit run memory_mem0_ui.py
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple
from urllib.parse import urlparse

import streamlit as st

try:
    from mem0 import Memory
except ImportError:  # pragma: no cover - optional dependency in some envs
    Memory = None

try:
    from langchain_ollama import OllamaEmbeddings
except ImportError:  # pragma: no cover - optional dependency in some envs
    OllamaEmbeddings = None

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult


class NullChatModel(BaseChatModel):
    """Minimal LangChain chat model that always returns an empty response."""

    @property
    def _llm_type(self) -> str:  # pragma: no cover - trivial
        return "null"

    def _generate(self, messages, stop=None, run_manager=None, **kwargs) -> ChatResult:
        generation = ChatGeneration(message=AIMessage(content=""))
        return ChatResult(generations=[generation])

    async def _agenerate(self, messages, stop=None, run_manager=None, **kwargs) -> ChatResult:  # pragma: no cover - unused
        return self._generate(messages, stop=stop, run_manager=run_manager, **kwargs)

try:
    from qdrant_client import QdrantClient
    from qdrant_client.http import models as qmodels
except ImportError:  # pragma: no cover - optional dependency in some envs
    QdrantClient = None
    qmodels = None

Mem0ClientType = Any
QdrantClientType = Any

DEFAULT_COLLECTION = os.getenv("MEM0_COLLECTION", "mem0_nomic_768")
DEFAULT_QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
DEFAULT_QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
DEFAULT_EMBED_MODEL = os.getenv("MEM0_EMBED_MODEL", "nomic-embed-text")
DEFAULT_LLM_MODEL = os.getenv("MEM0_LLM_MODEL")


@dataclass(frozen=True)
class ConnectionSettings:
    """Holds connection settings for Qdrant/Mem0."""

    qdrant_host: str
    qdrant_port: int
    qdrant_api_key: Optional[str]
    collection_name: str
    embed_model: str
    llm_model: Optional[str]
    enable_mem0: bool = True


def _mem0_available() -> bool:
    return Memory is not None and OllamaEmbeddings is not None


@st.cache_resource(show_spinner=False)
def get_qdrant_client(host: str, port: int, api_key: Optional[str]) -> Tuple[Optional[QdrantClientType], Optional[str]]:
    if QdrantClient is None:
        return None, "qdrant-client package not installed"

    normalized = host.strip()
    kwargs: Dict[str, Any] = {"api_key": api_key or None}

    if normalized.startswith(("http://", "https://")):
        parsed = urlparse(normalized)
        base_url = f"{parsed.scheme}://{parsed.netloc}"
        kwargs["url"] = base_url
        if parsed.path not in ("", "/"):
            kwargs["prefix"] = parsed.path
    else:
        kwargs["host"] = normalized
        kwargs["port"] = port

    try:
        client = QdrantClient(**kwargs)
        return client, None
    except Exception as exc:  # pragma: no cover - displayed in UI
        return None, str(exc)


@st.cache_resource(show_spinner=False)
def get_mem0_client(settings: ConnectionSettings) -> Tuple[Optional[Mem0ClientType], Optional[str]]:
    if not settings.enable_mem0:
        return None, "Mem0 client disabled in sidebar"

    if not _mem0_available():
        return None, "mem0ai or langchain-ollama not installed"

    embedder = OllamaEmbeddings(model=settings.embed_model)

    llm_obj: BaseChatModel = NullChatModel()
    if settings.llm_model:
        try:
            from langchain_openai import ChatOpenAI  # type: ignore

            llm_obj = ChatOpenAI(model=settings.llm_model, temperature=0)
        except Exception as exc:
            return None, f"Failed to initialize ChatOpenAI: {exc}"

    config: Dict[str, Any] = {
        "embedder": {
            "provider": "langchain",
            "config": {"model": embedder},
        },
        "vector_store": {
            "provider": "qdrant",
            "config": {
                "host": settings.qdrant_host,
                "port": settings.qdrant_port,
                "collection_name": settings.collection_name,
                "embedding_model_dims": 768,
            },
        },
        "llm": {
            "provider": "langchain",
            "config": {"model": llm_obj},
        },
    }

    try:
        client = Memory.from_config(config)
        return client, None
    except Exception as exc:  # pragma: no cover - surfaced in UI
        return None, str(exc)


def _normalize_mem0_items(results: Any) -> List[Dict[str, Any]]:
    if results is None:
        return []
    if isinstance(results, list):
        raw = results
    elif isinstance(results, dict):
        if "results" in results and isinstance(results["results"], list):
            raw = results["results"]
        elif "data" in results and isinstance(results["data"], list):
            raw = results["data"]
        else:
            raw = [results]
    else:
        raw = [results]

    formatted: List[Dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            formatted.append({"memory": str(item)})
            continue
        formatted.append(
            {
                "id": item.get("id") or item.get("_id"),
                "memory": item.get("memory")
                or item.get("text")
                or item.get("content"),
                "score": item.get("score") or item.get("similarity"),
                "user_id": item.get("user_id") or item.get("metadata", {}).get("user_id"),
                "metadata": item.get("metadata"),
                "created_at": item.get("created_at"),
                "updated_at": item.get("updated_at"),
            }
        )
    return formatted


def fetch_mem0_memories(client: Mem0ClientType, user_id: str) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    try:
        data = client.get_all(user_id=user_id)
        return _normalize_mem0_items(data), None
    except Exception as exc:  # pragma: no cover - streamlit displays the issue
        return [], str(exc)


def search_mem0(client: Mem0ClientType, user_id: str, query: str, limit: int) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    try:
        data = client.search(query=query, user_id=user_id, limit=limit)
        return _normalize_mem0_items(data), None
    except Exception as exc:  # pragma: no cover
        return [], str(exc)


def list_qdrant_collections(client: QdrantClientType) -> Sequence[str]:
    try:
        resp = client.get_collections()
        return [c.name for c in resp.collections]
    except Exception:
        return []


def sample_qdrant_points(
    client: QdrantClientType,
    collection: str,
    limit: int,
    user_filter: Optional[str],
) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    if client is None:
        return [], "Qdrant client is not available."

    if qmodels is None:
        return [], "qdrant-client models missing."

    scroll_filter = None
    if user_filter:
        scroll_filter = qmodels.Filter(must=[qmodels.FieldCondition(key="user_id", match=qmodels.MatchValue(value=user_filter))])

    try:
        points, _ = client.scroll(
            collection_name=collection,
            limit=limit,
            filter=scroll_filter,
            with_payload=True,
            with_vectors=False,
        )
    except Exception as exc:  # pragma: no cover
        return [], str(exc)

    rows: List[Dict[str, Any]] = []
    for point in points:
        rows.append(
            {
                "id": getattr(point, "id", None),
                "score": getattr(point, "score", None),
                "user_id": (point.payload or {}).get("user_id"),
                "metadata": (point.payload or {}).get("metadata"),
                "payload": point.payload,
            }
        )
    return rows, None


def gather_user_ids(client: QdrantClientType, collection: str, sample_size: int = 2048) -> List[str]:
    if client is None or qmodels is None:
        return []

    user_ids: List[str] = []
    seen = set()
    offset = None
    remaining = sample_size

    while remaining > 0:
        page_size = min(256, remaining)
        try:
            points, offset = client.scroll(
                collection_name=collection,
                limit=page_size,
                with_payload=True,
                with_vectors=False,
                offset=offset,
            )
        except Exception:
            break

        if not points:
            break

        for point in points:
            payload = point.payload or {}
            uid = payload.get("user_id") or payload.get("metadata", {}).get("user_id")
            if uid is None:
                continue
            uid_str = str(uid)
            if uid_str not in seen:
                seen.add(uid_str)
                user_ids.append(uid_str)

        remaining -= page_size
        if offset is None:
            break

    return sorted(user_ids)


def render_memories_tab(
    mem0_client: Optional[Mem0ClientType],
    qdrant_client: Optional[QdrantClientType],
    settings: ConnectionSettings,
    mem0_error: Optional[str] = None,
) -> None:
    st.subheader("Mem0 Memories")

    if mem0_client is None:
        warning = mem0_error or "Mem0 client is not available. Ensure mem0ai + langchain-ollama are installed, Ollama is running, and (optionally) supply an OpenAI-compatible model."
        st.warning(warning)
        return

    user_ids = gather_user_ids(qdrant_client, settings.collection_name) if qdrant_client else []

    col1, col2 = st.columns(2)
    with col1:
        selected_user = st.selectbox(
            "Select user",
            options=user_ids if user_ids else [""],
            format_func=lambda x: x or "Manual",
            help="User IDs are derived from Qdrant payloads."
        )
    with col2:
        manual_user = st.text_input("Manual user_id override", placeholder="Enter user/chat ID")

    user_id = manual_user.strip() or selected_user.strip()
    if not user_id:
        st.info("Provide a user_id to inspect memories.")
        return

    mems, err = fetch_mem0_memories(mem0_client, user_id)
    if err:
        st.error(f"Failed to load memories: {err}")
        return

    st.caption(f"Total memories retrieved: {len(mems)}")
    if mems:
        st.dataframe(mems, hide_index=True, width="stretch")
    else:
        st.info("No memories found for this user.")

    with st.expander("Search Mem0"):
        search_query = st.text_input("Search query", key="mem0_search_query")
        search_limit = st.slider("Max hits", min_value=1, max_value=20, value=5)
        if st.button("Run search", key="mem0_search_btn"):
            hits, search_err = search_mem0(mem0_client, user_id, search_query, search_limit)
            if search_err:
                st.error(f"Search failed: {search_err}")
            else:
                if hits:
                    st.success(f"{len(hits)} hits")
                    st.dataframe(hits, hide_index=True, width="stretch")
                else:
                    st.info("No hits for this query.")


def render_qdrant_tab(qdrant_client: Optional[QdrantClientType], collection_name: str, qdrant_error: Optional[str]) -> None:
    st.subheader("Qdrant Collections")

    if qdrant_client is None:
        st.warning(qdrant_error or "qdrant-client is not installed or Qdrant is unreachable.")
        return

    collections = list_qdrant_collections(qdrant_client)
    if not collections:
        st.info("No collections detected.")
        return

    selected_collection = st.selectbox("Collection", options=collections, index=collections.index(collection_name) if collection_name in collections else 0)

    try:
        details = qdrant_client.get_collection(selected_collection)
        st.json(details.model_dump())
    except Exception as exc:
        st.error(f"Failed to fetch collection info: {exc}")

    with st.expander("Sample points"):
        user_filter = st.text_input("Filter by user_id", key="qdrant_user_filter")
        limit = st.slider("Rows", min_value=10, max_value=200, value=50, step=10)
        if st.button("Load points", key="qdrant_sample_btn"):
            rows, err = sample_qdrant_points(qdrant_client, selected_collection, limit, user_filter.strip() or None)
            if err:
                st.error(err)
            elif rows:
                st.dataframe(rows, hide_index=True, width="stretch")
            else:
                st.info("No points matched the criteria.")


def main() -> None:
    st.set_page_config(page_title="Mem0 Memory Browser", page_icon="🧠", layout="wide")
    st.title("🧠 Mem0 Memory & Qdrant Explorer")
    st.caption("Inspect semantic memories stored via Mem0/qdrant.")

    with st.sidebar:
        st.header("Connections")
        qdrant_host = st.text_input("Qdrant host", value=DEFAULT_QDRANT_HOST)
        qdrant_port = st.number_input("Qdrant port", min_value=1, max_value=65535, value=DEFAULT_QDRANT_PORT)
        qdrant_api_key = st.text_input("Qdrant API key", type="password", help="Leave blank for local deployments")
        collection = st.text_input("Mem0 collection", value=DEFAULT_COLLECTION)
        embed_model = st.text_input("Ollama embedding model", value=DEFAULT_EMBED_MODEL)
        llm_model = st.text_input("Optional OpenAI model", value=DEFAULT_LLM_MODEL or "", help="Provide an OpenAI-compatible model name to run Mem0 extractors. Leave blank to use the built-in stub LLM.")
        enable_mem0 = st.checkbox("Enable Mem0 client", value=True, help="Disable to browse Qdrant without initializing Mem0.")
        if st.button("Reconnect clients"):
            st.cache_resource.clear()

    settings = ConnectionSettings(
        qdrant_host=qdrant_host.strip() or DEFAULT_QDRANT_HOST,
        qdrant_port=int(qdrant_port),
        qdrant_api_key=qdrant_api_key.strip() or None,
        collection_name=collection.strip() or DEFAULT_COLLECTION,
        embed_model=embed_model.strip() or DEFAULT_EMBED_MODEL,
        llm_model=llm_model.strip() or None,
        enable_mem0=enable_mem0,
    )

    qdrant_client, qdrant_error = get_qdrant_client(settings.qdrant_host, settings.qdrant_port, settings.qdrant_api_key)
    mem0_client, mem0_error = get_mem0_client(settings)

    if qdrant_error:
        st.error(f"Qdrant client error: {qdrant_error}")

    if mem0_error and settings.enable_mem0:
        st.warning(f"Mem0 initialization issue: {mem0_error}")

    tabs = st.tabs(["Memories", "Qdrant"])
    with tabs[0]:
        render_memories_tab(mem0_client, qdrant_client, settings, mem0_error if settings.enable_mem0 else "Mem0 disabled.")
    with tabs[1]:
        render_qdrant_tab(qdrant_client, settings.collection_name, qdrant_error)


if __name__ == "__main__":
    main()
