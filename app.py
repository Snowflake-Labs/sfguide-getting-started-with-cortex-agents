import streamlit as st
import json
import requests
import sseclient
import os
from dotenv import load_dotenv
import generate_jwt
import logging
import pandas as pd
import snowflake.connector

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('app.log')
    ]
)
logger = logging.getLogger(__name__)

# Constants
# ACCOUNT = "CORTEXSEARCHSUMMITDEMO"
# USER = "JCHAEARLEY"
# RSA_PRIVATE_KEY_PATH = "rsa_key.p8"
SNOWFLAKE_ACCOUNT = os.getenv("SNOWFLAKE_ACCOUNT")
SNOWFLAKE_ACCOUNT_URL = os.getenv("SNOWFLAKE_ACCOUNT_URL")
SNOWFLAKE_USER = os.getenv("SNOWFLAKE_USER")
SNOWFLAKE_PASSWORD = os.getenv("SNOWFLAKE_PASSWORD")
SNOWFLAKE_ROLE = os.getenv("SNOWFLAKE_ROLE")
SNOWFLAKE_WAREHOUSE = os.getenv("SNOWFLAKE_WAREHOUSE")
SNOWFLAKE_DATABASE = os.getenv("SNOWFLAKE_DATABASE")
SNOWFLAKE_SCHEMA = os.getenv("SNOWFLAKE_SCHEMA")
RSA_PRIVATE_KEY_PATH = os.getenv("RSA_PRIVATE_KEY_PATH")
CORTEX_SEARCH_SERVICES = "sales_intelligence.data.sales_conversation_search"
SEMANTIC_MODELS = "@sales_intelligence.data.models/sales_metrics_model.yaml"


# Custom CSS styling
st.markdown("""
<style>
/* Unified Color Palette */
:root {
    --background-color: #FFFFFF;
    --text-color: #222222;
    --title-color: #1A1A1A;
    --button-color: #1a56db;
    --button-text: #FFFFFF;
    --border-color: #CBD5E0;
    --accent-color: #2C5282;
}

/* General App Styling */
.stApp {
    background-color: var(--background-color);
    color: var(--text-color);
}

/* Title Styling */
h1, .stTitle {
    color: var(--title-color) !important;
    font-size: 36px !important;
    font-weight: 600 !important;
    padding: 1.5rem 0;
}

/* Input Fields */
textarea {
    background-color: white !important;
    border: 1px solid var(--border-color) !important;
    border-radius: 4px !important;
    padding: 16px !important;
    font-size: 16px !important;
    color: var(--text-color) !important;
}

textarea:focus {
    border-color: var(--accent-color) !important;
    box-shadow: 0 0 0 1px var(--accent-color) !important;
}

textarea::placeholder {
    color: #666666 !important;
}

/* Success & Error Messages */
.stException {
    background-color: #FEE2E2 !important;
    border: 1px solid #EF4444 !important;
    padding: 16px !important;
    border-radius: 4px !important;
    margin: 16px 0 !important;
    color: #991B1B !important;
}

div[data-testid="stAlert"], div[data-testid="stException"] {
    background-color: #f8d7da !important;
    color: #721c24 !important;
    border: 1px solid #f5c6cb !important;
    padding: 12px !important;
    border-radius: 6px !important;
    font-weight: bold !important;
}

div[data-testid="stAlertContentError"] {
    color: #721c24 !important;
}

.stFormSubmitButton {
    background-color: white !important;
    padding: 10px;
    border-radius: 8px;
}

button[data-testid="stBaseButton-secondaryFormSubmit"] {
    background-color: #007bff !important;
    color: white !important;
    font-weight: bold !important;
    border-radius: 5px !important;
    padding: 8px 16px !important;
    border: none !important;
}

/* Sidebar Buttons */
.stSidebar button {
    background-color: #1a56db !important;
    color: white !important;
    font-weight: 600 !important;
    border: none !important;
}

/* Tooltips */
.tooltip {
    visibility: hidden;
    opacity: 0;
    background-color: white;
    color: var(--text-color);
    padding: 10px;
    border-radius: 10px;
    font-size: 14px;
    line-height: 1.5;
    width: max-content;
    max-width: 300px;
    position: absolute;
    z-index: 1000;
    bottom: calc(100% + 5px);
    left: 50%;
    transform: translateX(-50%);
    transition: opacity 0.3s ease, transform 0.3s ease;
}

.citation:hover + .tooltip {
    visibility: visible;
    opacity: 1;
    transform: translateX(-50%) translateY(0);
}

/* Hide Streamlit Branding */
#MainMenu, header, footer {
    visibility: hidden;
}

[data-testid="stDownloadButton"] button {
    background-color: #2196F3 !important;
    color: #FFFFFF !important;
    font-weight: 600 !important;
    border: none !important;
    padding: 0.5rem 1rem !important;
    border-radius: 0.375rem !important;
    box-shadow: none !important;
}
</style>
""", unsafe_allow_html=True)

def run_snowflake_query(query):
    try:
        conn = snowflake.connector.connect(
            account=SNOWFLAKE_ACCOUNT,
            host=SNOWFLAKE_ACCOUNT_URL,
            user=SNOWFLAKE_USER,
            password=SNOWFLAKE_PASSWORD,
            role=SNOWFLAKE_ROLE,
            warehouse=SNOWFLAKE_WAREHOUSE,
            database=SNOWFLAKE_DATABASE,
            schema=SNOWFLAKE_SCHEMA
        )
        
        cursor = conn.cursor()
        cursor.execute(query)
        columns = [col[0] for col in cursor.description]
        results = cursor.fetchall()

        cursor.close()
        conn.close()
        return results, columns

    except Exception as e:
        print(f"Error executing SQL: {str(e)}")

def snowflake_api_call(query: str, jwt_token:str, limit: int = 10):
    """Make API call with JWT token"""
    logger.info(f"Making API call with query: {query}")

    # API endpoint
    url = "cortexsearchsummitdemo.preprod8.us-west-2.aws.snowflakecomputing.com/api/v2/cortex/agent:run"
    
    # Headers
    headers = {
        'X-Snowflake-Authorization-Token-Type': 'KEYPAIR_JWT',
        'Content-Type': 'application/json',
        'Accept': 'text/event-stream',
        'Authorization': f'Bearer {jwt_token}'
    }
    
    # Request payload
    payload = {
        "model": "claude-3-5-sonnet",
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": query
                    }
                ]
            }
        ],
        "tools": [
            {
                "tool_spec": {
                    "type": "cortex_analyst_text_to_sql",
                    "name": "analyst1"
                }
            },
            {
                "tool_spec": {
                    "type": "cortex_search",
                    "name": "search1"
                }
            }
        ],
        "tool_resources": {
            "analyst1": {"semantic_model_file": SEMANTIC_MODELS},
            "search1": {
                "name": CORTEX_SEARCH_SERVICES,
                "max_results": limit
            }
        }
    }
    
    try:
        logger.info("Sending API request")
        response = requests.post(
            url=f"https://{url}",
            headers=headers,
            json=payload,
            stream=True
        )
        
        if response.status_code != 200:
            logger.error(f"Error response: {response.status_code} - {response.text}")
            st.error(f"Error: {response.status_code} - {response.text}")
            return None
            
        logger.info("Successfully created SSE client")
        return sseclient.SSEClient(response)
            
    except Exception as e:
        logger.error(f"Error making request: {str(e)}", exc_info=True)
        st.error(f"Error making request: {str(e)}")
        return None

def process_sse_response(sse_client):
    """Process SSE response"""
    logger.info("Processing SSE response")
    text = ""
    citations = []
    debug_info = ""
    sql = ""
    other_info = ""
    
    if not sse_client:
        return text, citations, debug_info, sql, other_info
        
    try:
        for event in sse_client.events():
            logger.debug(f"Received SSE event: {event.data}")
            if event.data == "[DONE]":
                break
                
            try:
                data = json.loads(event.data)
                
                if 'delta' in data and 'content' in data['delta']:
                    for content_item in data['delta']['content']:
                        content_type = content_item.get('type')
                        
                        if content_type == "tool_use":
                            tool_use = content_item.get('tool_use', {})
                            
                        elif content_type == "tool_results":
                            tool_results = content_item.get('tool_results', {})
                            if 'content' in tool_results:
                                for result in tool_results['content']:
                                    if result.get('type') == 'json':
                                        logger.debug(f"JSON result: {result}")
                                        text += result.get('json', {}).get('text', '')
                                        search_results = result.get('json', {}).get('searchResults', [])
                                        for search_result in search_results:
                                            text += f"\n• {search_result.get('text', '')}"
                                        sql = result.get('json', {}).get('sql', '')
                            
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse event data: {str(e)}")
                continue
                
    except Exception as e:
        logger.error(f"Error processing events: {str(e)}", exc_info=True)
        st.error(f"Error processing events: {str(e)}")
        
    return text, citations, debug_info, sql, other_info

def main():
    st.title("Sales Intelligence Platform")

    # Initialize JWT Generator
    jwt_token = generate_jwt.JWTGenerator(SNOWFLAKE_ACCOUNT,SNOWFLAKE_USER,RSA_PRIVATE_KEY_PATH).get_token()

    # Sidebar for new chat
    with st.sidebar:
        if st.button("New Conversation", key="new_chat"):
            st.session_state.messages = []
            st.rerun()

    # Initialize session state
    if 'messages' not in st.session_state:
        st.session_state.messages = []

    # Chat input form
    with st.form(key="query_form"):
        query = st.text_area(
            "",
            placeholder="Ask about sales conversations or sales data...",
            key="query_input",
            height=100
        )
        submit = st.form_submit_button("Submit")

    if submit and query:
        # Add user message to chat
        st.session_state.messages.append({"role": "user", "content": query})
        
        # Get response from API
        with st.spinner("Processing your request..."):
            sse_client = snowflake_api_call(query, jwt_token)
            text, citations, debug_info, sql, other_info = process_sse_response(sse_client)
            
            # Add assistant response to chat
            if text:
                st.session_state.messages.append({"role": "assistant", "content": text})

            # Display chat history
            for message in st.session_state.messages:
                logger.info(f"Message: {message}")
                with st.container():
                    if message["role"] == "user":
                        st.markdown("**You:**")
                    else:
                        st.markdown("**Assistant:**")
                    st.markdown(message["content"].replace("•", "\n\n-"))
                    st.markdown("---")
            
            # Display SQL if present
            if sql:
                st.markdown("### Generated SQL")
                st.code(sql, language="sql")
                sales_results, column_names = run_snowflake_query(sql)
                if sales_results:
                    df = pd.DataFrame(sales_results, columns=column_names)
                    st.write("### Sales Metrics Report")
                    st.dataframe(df)

            
            # Display citations if present
            if citations:
                st.markdown("### Citations")
                for i, citation in enumerate(citations, 1):
                    st.markdown(f"{i}. {citation.get('chunk', '')}")


if __name__ == "__main__":
    main()