import streamlit as st
import requests
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

# ── These two lines are the fix — hardcoded new URL as fallback ──
API_URL = os.getenv('API_URL', 'https://hwb6mfqk9e.execute-api.us-east-1.amazonaws.com/prod/agents/test-agent-1/execute')
API_KEY = os.getenv('API_KEY', 'DishaRihan22')

# ── Page config ──────────────────────────────────────────
st.set_page_config(
    page_title='AgentFlow',
    page_icon='🤖',
    layout='wide'
)

# ── Custom CSS ───────────────────────────────────────────
st.markdown('''
<style>
    .main { background-color: #fdf8f0; }
    .stTextInput input { background: #fdf8f0; color: #333333; border: 1px solid #2e75b6; }
    .stButton button { background: #2e75b6; color: white; border-radius: 8px; width: 100%; }
    .stButton button:hover { background: #1f4e79; }
    .chat-msg-user { background: #f5f0e8; color: #333333; padding: 10px 16px; border-radius: 12px; margin: 4px 0; border-left: 3px solid #c8b89a; }
    .chat-msg-ai { background: #fdf8f0; color: #333333; border-left: 3px solid #2e75b6; padding: 10px 16px; border-radius: 12px; margin: 4px 0; }
</style>
''', unsafe_allow_html=True)

# ── Session state ────────────────────────────────────────
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'history' not in st.session_state:
    st.session_state.history = []
if 'total_cost' not in st.session_state:
    st.session_state.total_cost = 0.0
if 'total_calls' not in st.session_state:
    st.session_state.total_calls = 0

# ── Header ───────────────────────────────────────────────
st.markdown('# 🤖 AgentFlow Dashboard')
st.markdown('*AI Agent Hosting Platform — Built by Rihan & Disha*')
st.divider()

# ── Layout ───────────────────────────────────────────────
col1, col2 = st.columns([2, 1])

with col1:
    st.markdown('### 💬 Chat with Agent')

    model = st.selectbox('Model', ['gpt-3.5-turbo', 'gpt-4o', 'gpt-4'], key='model')
    system_prompt = st.text_input('System Prompt', value='You are a helpful assistant.', key='sysprompt')
    st.divider()

    for msg in st.session_state.messages:
        if msg['role'] == 'user':
            st.markdown(f'<div class="chat-msg-user">👤 <b>You:</b> {msg["content"]}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="chat-msg-ai">🤖 <b>Agent:</b> {msg["content"]}</div>', unsafe_allow_html=True)

    st.divider()

    user_input = st.text_input('Your message:', placeholder='Type something...', key='user_input')
    send_btn = st.button('Send ➤', use_container_width=True)

    if send_btn and user_input.strip():
        with st.spinner('Agent is thinking...'):
            try:
                context = [
                    {'role': m['role'], 'content': m['content']}
                    for m in st.session_state.messages
                ]

                payload = {
                    'agent_type': 'langchain',
                    'agent_config': {
                        'model': model,
                        'system_prompt': system_prompt,
                    },
                    'user_input': user_input,
                    'context': context,
                    'api_key': API_KEY
                }

                response = requests.post(
                    API_URL,
                    json=payload,
                    headers={
                        'Content-Type': 'application/json',
                        'x-api-key': API_KEY
                    },
                    timeout=60
                )
                data = response.json()

                if data.get('status') == 'success':
                    output = data.get('output', '')
                    cost   = data.get('cost_usd', 0)
                    tokens = data.get('tokens', {})
                    ms     = data.get('execution_time_ms', 0)

                    st.session_state.messages.append({'role': 'user', 'content': user_input})
                    st.session_state.messages.append({'role': 'assistant', 'content': output})
                    st.session_state.total_cost  += cost
                    st.session_state.total_calls += 1
                    st.session_state.history.append({
                        'time':    datetime.now().strftime('%H:%M:%S'),
                        'input':   user_input[:40] + '...' if len(user_input) > 40 else user_input,
                        'output':  output[:60] + '...' if len(output) > 60 else output,
                        'model':   model,
                        'tokens':  tokens.get('prompt', 0) + tokens.get('completion', 0),
                        'cost':    f'${cost:.6f}',
                        'time_ms': f'{ms}ms'
                    })
                    st.rerun()
                else:
                    error = data.get('error', {})
                    if isinstance(error, dict):
                        st.error(f"Agent error: {error.get('message', 'Unknown error')}")
                    else:
                        st.error(f'Agent error: {error}')

            except requests.exceptions.Timeout:
                st.error('Request timed out — agent took too long to respond')
            except Exception as e:
                st.error(f'Error: {str(e)}')

    if st.button('🗑️ Clear Chat', use_container_width=True):
        st.session_state.messages = []
        st.rerun()

with col2:
    st.markdown('### 📊 Stats')
    st.metric('Total Calls', st.session_state.total_calls)
    st.metric('Total Cost', f'${st.session_state.total_cost:.6f}')
    st.metric('Messages', len(st.session_state.messages))
    st.divider()

    st.markdown('### ⚙️ Agent Info')
    st.markdown('**Endpoint:** `test-agent-1`')
    st.markdown('**Framework:** LangChain + OpenAI')
    st.markdown('**Memory:** Session-based')
    st.divider()

    st.markdown('### 🕒 Execution History')
    if st.session_state.history:
        for h in reversed(st.session_state.history[-5:]):
            with st.expander(f"{h['time']} — {h['input']}"):
                st.write(f"**Output:** {h['output']}")
                st.write(f"**Model:** {h['model']}")
                st.write(f"**Tokens:** {h['tokens']}")
                st.write(f"**Cost:** {h['cost']}")
                st.write(f"**Time:** {h['time_ms']}")
    else:
        st.info('No executions yet — send a message!')