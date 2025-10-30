import streamlit as st
from agent import ReservationAgent
# We no longer need get_system_prompt in this file

# --- Page Configuration ---
st.set_page_config(page_title="GoodFoods Reservations", layout="wide")
st.title("🤖 GoodFoods AI Reservation Assistant")

# --- Agent and History Initialization ---

def initialize_agent():
    """Initializes the agent and chat history in session state."""
    
    if "agent" not in st.session_state:
        st.session_state.agent = ReservationAgent()
        
    if "messages" not in st.session_state:
        # --- MODIFIED ---
        # We NO LONGER add the system prompt to the session state.
        # The agent will add a fresh one every time.
        
        new_greeting = (
            "Welcome to GoodFoods! 🍽️ I can help you find a table at any of our locations, "
            "give recommendations, or manage an existing booking.\n\n"
            "To get started, what would you like to do? And please let me know the **date, time, preferred time and favourite cuisines!😋**"
        )
        
        st.session_state.messages = [
            # The system prompt is removed from here
            {"role": "assistant", "content": new_greeting}
        ]

initialize_agent()

# --- Chat History Display ---

def display_chat_history():
    """Displays the chat history, skipping system messages."""
    for message in st.session_state.messages:
        # This logic is now simpler, as system messages are never in the state
        if message["role"] == "system":
            continue
        if message["role"] == "tool":
            continue
        if "tool_calls" in message:
            continue
            
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

display_chat_history()

# --- User Input Handling ---

if prompt := st.chat_input("What would you like to do?"):
    
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
        
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            
            # The agent's run method will now handle adding the fresh system prompt
            new_messages = st.session_state.agent.run(st.session_state.messages)
            
            st.session_state.messages.extend(new_messages)
            
            final_response = new_messages[-1]
            if final_response.get("content"):
                st.markdown(final_response["content"])
            else:
                st.markdown("Sorry, I had trouble processing that.")