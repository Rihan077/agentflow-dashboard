import streamlit as st
import requests
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

API_URL  = os.getenv('API_URL', 'https://hwb6mfqk9e.execute-api.us-east-1.amazonaws.com/prod/agents/test-agent-1/execute')
AUTH_URL = os.getenv('AUTH_URL', 'https://hwb6mfqk9e.execute-api.us-east-1.amazonaws.com/prod/auth')
API_KEY  = os.getenv('API_KEY', 'DishaRihan22')

st.set_page_config(page_title='AgentFlow', page_icon='🤖', layout='wide')

st.markdown('''
<style>
    .stTextInput input { background: #fdf8f0; color: #333333; border: 1px solid #2e75b6; }
    .stButton button { background: #2e75b6; color: white; border-radius: 8px; width: 100%; }
    .stButton button:hover { background: #1f4e79; }
    .chat-msg-user { background: #f5f0e8; color: #333333; padding: 10px 16px; border-radius: 12px; margin: 4px 0; border-left: 3px solid #c8b89a; }
    .chat-msg-ai { background: #fdf8f0; color: #333333; border-left: 3px solid #2e75b6; padding: 10px 16px; border-radius: 12px; margin: 4px 0; }
    .login-box { max-width: 400px; margin: 100px auto; padding: 40px; background: #fdf8f0; border-radius: 16px; border: 1px solid #2e75b6; }
</style>
''', unsafe_allow_html=True)

# ── Session state ────────────────────────────────────────
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'username' not in st.session_state:
    st.session_state.username = ''
if 'token' not in st.session_state:
    st.session_state.token = ''
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'history' not in st.session_state:
    st.session_state.history = []
if 'total_cost' not in st.session_state:
    st.session_state.total_cost = 0.0
if 'total_calls' not in st.session_state:
    st.session_state.total_calls = 0
if 'calls_today' not in st.session_state:
    st.session_state.calls_today = 0

# ── LOGIN PAGE ───────────────────────────────────────────
if not st.session_state.logged_in:
    st.markdown('# 🤖 AgentFlow')
    st.markdown('*AI Agent Hosting Platform*')
    st.divider()
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown('### 🔐 Login to AgentFlow')
        username = st.text_input('Username', placeholder='Enter username')
        password = st.text_input('Password', placeholder='Enter password', type='password')
        login_btn = st.button('Login ➤', use_container_width=True)
        st.markdown('')
        st.info('Demo credentials: username = rihan or disha / password = password123')

        if login_btn and username and password:
            with st.spinner('Logging in...'):
                try:
                    response = requests.post(AUTH_URL, json={
                        'action': 'login',
                        'username': username,
                        'password': password
                    }, timeout=10)
                    data = response.json()
                    if response.status_code == 200 and data.get('token'):
                        st.session_state.logged_in = True
                        st.session_state.username  = data.get('username', username)
                        st.session_state.token     = data.get('token', '')
                        st.success(f'Welcome, {st.session_state.username}!')
                        st.rerun()
                    else:
                        st.error('Invalid username or password')
                except Exception as e:
                    st.error(f'Login failed: {str(e)}')
    st.stop()

# ── MAIN DASHBOARD (only shown when logged in) ───────────
col_header1, col_header2 = st.columns([3, 1])
with col_header1:
    st.markdown(f'# 🤖 AgentFlow Dashboard')
    st.markdown(f'*Logged in as **{st.session_state.username}** | AI Agent Hosting Platform — Built by Rihan & Disha*')
with col_header2:
    if st.button('🚪 Logout', use_container_width=True):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
st.divider()

col1, col2 = st.columns([2, 1])

with col1:
    st.markdown('### 💬 Chat with Agent')
    model = st.selectbox('Model', ['gpt-3.5-turbo', 'gpt-4o', 'gpt-4'], key='model')
    system_prompt = st.text_input('System Prompt', value='You are a helpful assistant.', key='sysprompt')
    st.divider()

    chat_container = st.container()
    with chat_container:
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
                context = [{'role': m['role'], 'content': m['content']} for m in st.session_state.messages]
                payload = {
                    'agent_type': 'langchain',
                    'agent_config': {'model': model, 'system_prompt': system_prompt},
                    'user_input': user_input,
                    'context': context,
                    'api_key': API_KEY
                }
                response = requests.post(API_URL, json=payload, timeout=60)
                data = response.json()

                if response.status_code == 429:
                    st.error(f'Rate limit exceeded! You have used all 100 calls for today.')
                elif data.get('status') == 'success':
                    output = data.get('output', '')
                    cost   = data.get('cost_usd', 0)
                    tokens = data.get('tokens', {})
                    ms     = data.get('execution_time_ms', 0)
                    st.session_state.messages.append({'role': 'user', 'content': user_input})
                    st.session_state.messages.append({'role': 'assistant', 'content': output})
                    st.session_state.total_cost  += cost
                    st.session_state.total_calls += 1
                    st.session_state.calls_today += 1
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
                        st.error(f'Error: {data}')
            except requests.exceptions.Timeout:
                st.error('Request timed out')
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

    # F19 — Rate limit display
    st.markdown('### 🔢 Rate Limit')
    calls_used = st.session_state.calls_today
    calls_left = max(0, 100 - calls_used)
    st.progress(calls_used / 100)
    st.markdown(f'**{calls_used}/100** calls used today')
    st.markdown(f'**{calls_left}** calls remaining')
    if calls_left < 20:
        st.warning('⚠️ Running low on calls!')
    st.divider()

    st.markdown('### ⚙️ Agent Info')
    st.markdown(f'**User:** `{st.session_state.username}`')
    st.markdown(f'**Endpoint:** `test-agent-1`')
    st.markdown(f'**Framework:** LangChain + OpenAI')
    st.markdown(f'**Memory:** Session-based')
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
