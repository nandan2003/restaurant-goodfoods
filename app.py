import streamlit as st
from agent import MCP_Controller # Import the new Controller

# --- Page Configuration ---
st.set_page_config(page_title="GoodFoods Reservations", layout="wide")
st.title("🤖 GoodFoods AI Reservation Assistant")

# --- Agent and History Initialization ---

def initialize_agent():
    """Initializes the agent and chat history in session state."""
    
    if "agent" not in st.session_state:
        st.session_state.agent = MCP_Controller() # Use the new Controller
        
    if "messages" not in st.session_state:
        
        new_greeting = (
            "Welcome to GoodFoods! 🍽️ I can help you find a table at any of our locations, "
            "give recommendations, or manage an existing booking.\n\n"
            "To get started, what would you like to do? And please let me know the **date** you're planning for."
        )
        
        st.session_state.messages = [
            {"role": "assistant", "content": new_greeting}
        ]

initialize_agent()

# --- Chat History Display ---

def display_chat_history():
    """Displays the chat history, skipping system/tool messages."""
    for message in st.session_state.messages:
        if message["role"] == "system" or message["role"] == "tool":
            continue
        
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

display_chat_history()

# --- User Input Handling ---

if prompt := st.chat_input("What would you like to do?"):
    
    # Add user message to state
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Rerun the display to show the user's message immediately
    st.rerun()

# --- MODIFIED: Agent Run Logic ---
# This logic is now outside the `if prompt` block
# to allow it to run *after* the st.rerun
if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            
            # Call the agent with the full conversational history
            new_messages = st.session_state.agent.run(st.session_state.messages)
            
            # Add all new messages to the state
            st.session_state.messages.extend(new_messages)
            
            # Rerun the app to display the new messages
            st.rerun()