import boto3
import streamlit as st
import hmac

BUCKET_NAME = "epaluator-bucket-for-bedrock"
s3_location = []

st.set_page_config(layout="wide")

st.markdown(
    """
    <style>
    [data-testid="stChatMessageContent"] p{
        font-size: 1.5rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <style>
        [data-testid=stImage]{
            text-align: center;
            display: block;
            margin-left: auto;
            margin-right: auto;
            width: 100%;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <style>
        [data-testid=stForm]{
            text-align: center;
            display: block;
            margin-left: auto;
            margin-right: auto;
            width: 40%;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


def create_presigned_url(bucket_name, object_name, expiration=3600):
    """Generate a presigned URL to share an S3 object

    :param bucket_name: string
    :param object_name: string
    :param expiration: Time in seconds for the presigned URL to remain valid
    :return: Presigned URL as string. If error, returns None.
    """

    # Generate a presigned URL for the S3 object
    s3_client = boto3.client("s3")

    response = s3_client.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket_name, "Key": object_name},
        ExpiresIn=expiration,
    )

    # The response contains the presigned URL
    return response


def check_password():
    """Returns `True` if the user had a correct password."""

    def login_form():
        """Form with widgets to collect user information"""
        st.image("./images/epa_banner.png", use_column_width="always")
        st.image("./images/epa_xplorer.png")

        with st.form("Credentials"):
            st.text_input("Username", key="username")
            st.text_input("Password", type="password", key="password")
            st.form_submit_button("Log in", on_click=password_entered)

        message = f"<h5 style='text-align: center; color: #4e95d9;'>I AM YOUR GUIDE TO ALL GHG EMISSIONS IN EPA AND OGMP!</h5>"
        st.markdown(
            message,
            unsafe_allow_html=True,
        )

        st.write("#")
        st.write("#")
        st.image("./images/methane_iq.png")

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

st.image("./images/epa_banner.png", use_column_width="always")

col1, col2, col3 = st.columns([0.2, 0.6, 0.2])

with col1:
    st.subheader(
        ":blue[MY KNOWLEDGE BASE INCLUDES THE FOLLOWING DOCUMENTS FROM EPA & OGMP. I UPDATE MY INFORMATION REGULARLY:]",
        divider="gray",
    )
    container = st.container(border=True, height=800)

    with container:
        s3 = boto3.resource("s3")
        myBucket = s3.Bucket(BUCKET_NAME)

        cont = 0
        for object_summary in myBucket.objects.all():
            cont = cont + 1

        text_total = (
            f"<h5 style='text-align: left; color: black;'>{cont} Documents:</h5>"
        )
        st.markdown(
            text_total,
            unsafe_allow_html=True,
        )

        for object_summary in myBucket.objects.all():
            url = create_presigned_url(BUCKET_NAME, object_summary.key)
            element = f"- [{object_summary.key}]"
            st.write(element + "(%s)" % url)

with col2:
    st.image("./images/epa_xplorer.png")

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

    # Required in case you want to display all comment history
    # for message in st.session_state.messages:
    #     with st.chat_message(message["role"]):
    #         st.markdown(message["content"])

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
                    if not reference["location"]["s3Location"]["uri"] in s3_location:
                        s3_location.append(reference["location"]["s3Location"]["uri"])

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

with col3:

    st.subheader(
        ":blue[BASED ON YOUR QUESTION, YOU MAY WANT TO LOOK AT THESE REFERENCES:]",
        divider="gray",
    )
    container = st.container(border=True)

    with container:

        for path in s3_location:
            path_split = path.split("/")
            document_name = path_split[-1]
            url = create_presigned_url(BUCKET_NAME, document_name)
            element = f"- [{document_name}]"
            st.write(element + "(%s)" % url)
