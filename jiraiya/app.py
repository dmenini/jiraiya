import json
import logging
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path

import streamlit as st
import yaml  # type: ignore[import-untyped]
from pydantic_ai import Agent

from jiraiya.agent.components import create_agent
from jiraiya.agent.tools import ToolContext
from jiraiya.domain.config import Config
from jiraiya.io.jira_ticket_manager import JiraIssueManager
from jiraiya.settings import Settings
from jiraiya.store.code_store import CodeVectorStore

logger = logging.getLogger()
logging.basicConfig(level=logging.INFO)

settings = Settings()


class ChatApp:
    def __init__(self, agent: Agent, context: ToolContext) -> None:
        self.agent = agent
        self.initialize_session_state()
        self.context = context

    def initialize_session_state(self) -> None:
        """Initialize Streamlit session state variables."""
        if "messages" not in st.session_state:
            st.session_state.messages = []
            st.session_state.raw_history = []
            st.session_state.usage = None
        if "agent_initialized" not in st.session_state:
            st.session_state.agent_initialized = True
        if "last_user_prompt" not in st.session_state:
            st.session_state.last_user_prompt = None

    def display_chat_history(self) -> None:
        """Display the chat history in the Streamlit interface."""
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

    def _run_agent(self, prompt: str) -> str:
        """Runs the agent, updates state and displays assistant message."""
        st.session_state.last_user_prompt = prompt

        response = self.agent.run_sync(
            user_prompt=prompt,
            deps=self.context,
            message_history=st.session_state.raw_history,
        )
        message = response.output
        st.session_state.raw_history = response.all_messages()
        st.session_state.usage = response.usage().__dict__

        return message

    def handle_user_input(self) -> None:
        if prompt := st.chat_input("Type your message here..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    message = self._run_agent(prompt)
                    st.markdown(message)

                st.session_state.messages.append({"role": "assistant", "content": message})

    def retry_last_message(self) -> None:
        if not st.session_state.last_user_prompt:
            st.warning("No previous message to retry.")
            return

        if st.session_state.messages and st.session_state.messages[-1]["role"] == "assistant":
            st.session_state.messages.pop()
            st.session_state.raw_history.pop()

        self._run_agent(st.session_state.last_user_prompt)

    def display_sidebar(self) -> None:
        with st.sidebar:
            st.title("🤖 Chat Settings")
            st.write(f"**LLM:** {self.agent.model.model_name}")
            st.write(f"**Documents:** {self.context.vectorstore.count()}")
            st.write("**Repos:**")
            for repo in self.context.vectorstore.get_all_repos():
                st.write(f"* {repo}")

            st.divider()

            st.subheader("📊 Chat Stats")
            user_messages = len([m for m in st.session_state.messages if m["role"] == "user"])
            assistant_messages = len([m for m in st.session_state.messages if m["role"] == "assistant"])
            st.write(f"User messages: {user_messages}")
            st.write(f"Assistant messages: {assistant_messages}")
            st.write(f"Usage: {st.session_state.usage}")

            st.divider()

            st.subheader("🛠️ Controls")
            if st.button("Clear Chat History", type="secondary"):
                st.session_state.messages = []
                st.session_state.raw_history = []
                st.session_state.last_user_prompt = None
                st.rerun()

            if st.button("Retry Last Message", type="primary"):
                self.retry_last_message()

            if st.button("Export Chat", type="secondary"):
                chat_data = {
                    "chat_history": st.session_state.messages,
                    "timestamp": datetime.now(tz=UTC).isoformat(),
                    "llm": self.agent.model.model_name,
                }
                st.download_button(
                    label="Download Chat JSON",
                    data=json.dumps(chat_data, indent=2),
                    file_name=f"chat_export_{datetime.now(tz=UTC).strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json",
                )

    def run(self) -> None:
        """Main method to run the Streamlit app."""
        st.title("🤖 Code Assistant")
        st.markdown("---")

        self.display_sidebar()
        self.display_chat_history()
        self.handle_user_input()


def main() -> None:
    st.set_page_config(page_title="Code QA", page_icon="🤖", layout="wide")

    config_path = Path(__file__).parent / "config.yaml"
    with config_path.open() as fp:
        config = yaml.safe_load(fp)
        config = Config.model_validate(config)

    vectorstore = CodeVectorStore(
        tenant=config.data.tenant,
        code_encoder=config.data.code_encoder,
        text_encoder=config.data.dense_encoder,
        host=settings.qdrant_host,
        port=settings.qdrant_port,
        cache_dir=config.data.cache_dir,
    )

    jira = JiraIssueManager(server=settings.jira_server, token=str(settings.jira_token))

    agent = create_agent(config=config.agent)

    logger.info("total documents %d", vectorstore.count())

    @lru_cache
    @agent.system_prompt()
    def add_repos() -> str:
        repos = vectorstore.get_all_repos()
        logger.info(repos)

        return f"The repositories you have access to are: {', '.join(repos)}.\n"

    tool_config = config.agent.tools.search.model_dump() | config.agent.tools.jira.model_dump()
    tool_context = ToolContext(
        vectorstore=vectorstore,
        jira_client=jira,
        **tool_config,
    )

    chat_app = ChatApp(agent, tool_context)
    chat_app.run()


if __name__ == "__main__":
    main()
