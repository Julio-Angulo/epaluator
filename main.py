import boto3
import streamlit as st
import hmac


def check_password():
    """Returns `True` if the user had a correct password."""

    def login_form():
        """Form with widgets to collect user information"""
        with st.form("Credentials"):
            st.text_input("Username", key="username")
            st.text_input("Password", type="password", key="password")
            st.form_submit_button("Log in", on_click=password_entered)

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if st.session_state["username"] in st.secrets[
            "passwords"
        ] and hmac.compare_digest(
            st.session_state["password"],
            st.secrets.passwords[st.session_state["username"]],
        ):
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Don't store the username or password.
            del st.session_state["username"]
        else:
            st.session_state["password_correct"] = False

    # Return True if the username + password is validated.
    if st.session_state.get("password_correct", False):
        return True

    # Show inputs for username + password.
    login_form()
    if "password_correct" in st.session_state:
        st.error("😕 User not known or password incorrect")
    return False


if not check_password():
    st.stop()


st.title(":star-struck: GenAI EPAluator")  # title

# try out KB using RetrieveAndGenerate API
bedrock_agent_runtime_client = boto3.client(
    "bedrock-agent-runtime", region_name="us-west-2"
)
model_id = "anthropic.claude-v2"  # try with both claude instant as well as claude-v2. for claude v2 - "anthropic.claude-v2"
model_arn = f"arn:aws:bedrock:us-west-2::foundation-model/{model_id}"

if "bedrock_model" not in st.session_state:
    st.session_state["bedrock_model"] = model_arn

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("What is up?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        query = prompt

        response_from_bedrock = bedrock_agent_runtime_client.retrieve_and_generate(
            input={"text": query},
            retrieveAndGenerateConfiguration={
                "type": "KNOWLEDGE_BASE",
                "knowledgeBaseConfiguration": {
                    "knowledgeBaseId": st.secrets["knowledge_Base_Id"],
                    "modelArn": st.session_state["bedrock_model"],
                },
            },
        )

        st.markdown(response_from_bedrock["output"]["text"])

        citations = response_from_bedrock["citations"]
        contexts = []
        for citation in citations:
            retrievedReferences = citation["retrievedReferences"]
            for reference in retrievedReferences:
                contexts.append(reference["content"]["text"])

        with st.expander("Sources:"):
            tab1, tab2, tab3 = st.tabs(["Source 1", "Source 2", "Source 3"])
            number_sources = len(contexts)

            if number_sources >= 1:
                with tab1:
                    if contexts[0] != None:
                        st.markdown(contexts[0])
                if number_sources >= 2:
                    with tab2:
                        if contexts[1] != None:
                            st.markdown(contexts[1])
                    if number_sources >= 3:
                        with tab3:
                            if contexts[2] != None:
                                st.markdown(contexts[2])

    st.session_state.messages.append(
        {"role": "assistant", "content": response_from_bedrock["output"]["text"]}
    )
