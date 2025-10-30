import streamlit as st
from agent import ReservationAgent
from system_prompt import get_system_prompt

# --- Page Configuration ---
st.set_page_config(page_title="GoodFoods Reservations", layout="wide")
st.title("🤖 GoodFoods AI Reservation Assistant")

# --- Agent and History Initialization ---

def initialize_agent():
    """Initializes the agent and chat history in session state."""
    
    if "agent" not in st.session_state:
        st.session_state.agent = ReservationAgent()
        
    if "messages" not in st.session_state:
        # Start with the system prompt (not displayed) 
        # and a hardcoded greeting (displayed).
                new_greeting = (
            "Welcome to GoodFoods! 🍽️ I can help you find a table at any of our locations, "
            "give recommendations, or manage an existing booking.\n\n"
            "To get started, what would you like to do? And please let me know the **date** you're planning for."
        )
        system_prompt = get_system_prompt()
        st.session_state.messages = [
            {"role": "system", "content": system_prompt},
            {"role": "assistant", "content": new_greeting}
        ]

initialize_agent()

# --- Chat History Display ---

def display_chat_history():
    """Displays the chat history, skipping system messages."""
    for message in st.session_state.messages:
        if message["role"] == "system":
            continue
        if message["role"] == "tool":
            # Optional: Show tool calls for debugging
            # with st.expander(f"Tool Call: `{message['tool_call_id']}`"):
            #     st.json(message['content'])
            continue
        if "tool_calls" in message:
            # Optional: Show that the agent is thinking
            # st.log("Agent is using tools...")
            continue
            
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

display_chat_history()

# --- User Input Handling ---

if prompt := st.chat_input("What would you like to do?"):
    
    # 1. Add user message to history and display it
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
        
    # 2. Call the agent to get a response
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            
            # The agent's `run` method takes the *entire* history
            # and returns *all* new messages (tool calls, tool results, final answer)
            new_messages = st.session_state.agent.run(st.session_state.messages)
            
            # 3. Add new messages to history
            st.session_state.messages.extend(new_messages)
            
            # 4. Display the *last* message (the final text response)
            # The display_chat_history() function will handle the rest on rerun,
            # but we display the last one immediately.
            final_response = new_messages[-1]
            if final_response.get("content"):
                st.markdown(final_response["content"])
            else:
                st.markdown("Sorry, I had trouble processing that.")
