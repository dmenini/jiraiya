import json
import logging
from datetime import datetime, UTC
from functools import lru_cache
from pathlib import Path

import streamlit as st
import yaml  # type: ignore[import-untyped]
from pydantic_ai import Agent

from doc_scribe.agent.components import create_agent
from doc_scribe.agent.tools import ToolContext
from doc_scribe.domain.config import Config
from doc_scribe.settings import Settings
from doc_scribe.store.code_store import CodeVectorStore

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

    def display_chat_history(self) -> None:
        """Display the chat history in the Streamlit interface."""
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

    def handle_user_input(self) -> None:
        """Handle user input and generate agent response."""
        if prompt := st.chat_input("Type your message here..."):
            # Add user message to session state
            st.session_state.messages.append({"role": "user", "content": prompt})

            # Display user message
            with st.chat_message("user"):
                st.markdown(prompt)

            # Generate and display assistant response
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    response = self.agent.run_sync(
                        user_prompt=prompt,
                        deps=self.context,
                        message_history=st.session_state.raw_history,
                    )
                    message = response.output
                    st.session_state.raw_history = response.all_messages()
                    st.session_state.usage = response.usage().__dict__
                st.markdown(message)

            # Add assistant response to session state
            st.session_state.messages.append({"role": "assistant", "content": message})

    def display_sidebar(self) -> None:
        """Display sidebar with app information and controls."""
        with st.sidebar:
            st.title("🤖 Chat Settings")
            st.write(f"**LLM:** {self.agent.model.model_name}")
            st.write(f"**Documents:** {self.context.vectorstore.count()}")
            st.write(f"**Repos:**")
            for repo in self.context.vectorstore.get_all_repos():
                st.write(f"{repo}")

            st.divider()

            # Chat statistics
            st.subheader("📊 Chat Stats")
            user_messages = len([msg for msg in st.session_state.messages if msg["role"] == "user"])
            assistant_messages = len([msg for msg in st.session_state.messages if msg["role"] == "assistant"])
            st.write(f"User messages: {user_messages}")
            st.write(f"Assistant messages: {assistant_messages}")
            st.write(f"Usage: {st.session_state.usage}")

            st.divider()

            # Controls
            st.subheader("🛠️ Controls")
            if st.button("Clear Chat History", type="secondary"):
                st.session_state.messages = []
                st.session_state.raw_history = []
                st.rerun()

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
    # Initialize the Pydantic agent
    st.set_page_config(page_title="Code QA", page_icon="🤖", layout="wide")

    config_path = Path(__file__).parent / "agent_config.yaml"
    with config_path.open() as fp:
        config = yaml.safe_load(fp)
        config = Config.model_validate(config)

    vectorstore = CodeVectorStore(
        tenant=config.data.tenant,
        code_encoder=config.data.code_encoder,
        text_encoder=config.data.dense_encoder,
        host=settings.qdrant_host,
        port=settings.qdrant_port,
    )

    agent = create_agent(config=config.agent)

    logger.info("total documents %d", vectorstore.count())

    @lru_cache
    @agent.system_prompt()
    def add_repos() -> str:
        repos = vectorstore.get_all_repos()
        logger.info(repos)

        return f"The repositories you have access to are: {', '.join(repos)}.\n"

    tool_context = ToolContext(vectorstore=vectorstore, **config.agent.tools.search.model_dump())

    chat_app = ChatApp(agent, tool_context)
    chat_app.run()


if __name__ == "__main__":
    main()
