import streamlit as st
import requests
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

BASE_URL = os.getenv('BASE_URL', 'https://hwb6mfqk9e.execute-api.us-east-1.amazonaws.com/prod')
AUTH_URL = os.getenv('AUTH_URL', f'{BASE_URL}/auth')
UPLOAD_URL = os.getenv('UPLOAD_URL', f'{BASE_URL}/agents/upload')
API_KEY  = os.getenv('API_KEY', 'DishaRihan22')

st.set_page_config(page_title='AgentFlow', page_icon='🤖', layout='wide')

st.markdown('''
<style>
    .stTextInput input { background: #fdf8f0; color: #333333; border: 1px solid #2e75b6; }
    .stTextArea textarea { background: #fdf8f0; color: #333333; border: 1px solid #2e75b6; }
    .stButton button { background: #2e75b6; color: white; border-radius: 8px; width: 100%; }
    .stButton button:hover { background: #1f4e79; }
    .chat-msg-user { background: #f5f0e8; color: #333333; padding: 10px 16px; border-radius: 12px; margin: 4px 0; border-left: 3px solid #c8b89a; }
    .chat-msg-ai { background: #fdf8f0; color: #333333; border-left: 3px solid #2e75b6; padding: 10px 16px; border-radius: 12px; margin: 4px 0; }
    .agent-card { background: #f0f4ff; padding: 12px; border-radius: 10px; border-left: 4px solid #2e75b6; margin: 6px 0; }
</style>
''', unsafe_allow_html=True)

# ── Session state ────────────────────────────────────────
for key, val in {
    'logged_in': False, 'username': '', 'token': '',
    'messages': [], 'history': [], 'total_cost': 0.0,
    'total_calls': 0, 'calls_today': 0,
    'registered_agents': [],  # list of registered agents this session
    'active_agent_id': None,  # currently selected agent_id
    'active_agent_name': None,
}.items():
    if key not in st.session_state:
        st.session_state[key] = val

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
        st.info('Demo credentials: username = rihan or disha / password = password123')
        if login_btn and username and password:
            with st.spinner('Logging in...'):
                try:
                    r = requests.post(AUTH_URL, json={'action': 'login', 'username': username, 'password': password}, timeout=10)
                    data = r.json()
                    if r.status_code == 200 and data.get('token'):
                        st.session_state.logged_in = True
                        st.session_state.username  = data.get('username', username)
                        st.session_state.token     = data.get('token', '')
                        st.rerun()
                    else:
                        st.error('Invalid username or password')
                except Exception as e:
                    st.error(f'Login failed: {str(e)}')
    st.stop()

# ── HEADER ───────────────────────────────────────────────
col_h1, col_h2 = st.columns([3, 1])
with col_h1:
    st.markdown('# 🤖 AgentFlow Dashboard')
    active_name = st.session_state.active_agent_name or 'No agent selected'
    st.markdown(f'*Logged in as **{st.session_state.username}** | Active agent: **{active_name}***')
with col_h2:
    if st.button('🚪 Logout', use_container_width=True):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
st.divider()

# ── TABS: Chat | Register Agent | My Agents ─────────────
tab1, tab2, tab3 = st.tabs(['💬 Chat', '🚀 Register Agent', '📋 My Agents'])

# ══════════════════════════════════════════════════════
# TAB 1 — CHAT
# ══════════════════════════════════════════════════════
with tab1:
    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown('### 💬 Chat with Agent')
        if not st.session_state.active_agent_id:
            st.warning('⚠️ No agent selected. Go to **Register Agent** tab to create one first.')
        else:
            st.success(f'Chatting with: **{st.session_state.active_agent_name}** ({st.session_state.active_agent_id[:8]}...)')
        model = st.selectbox('Model', ['gpt-3.5-turbo', 'gpt-4o', 'gpt-4'], key='model')
        st.divider()
        for msg in st.session_state.messages:
            if msg['role'] == 'user':
                st.markdown(f'<div class="chat-msg-user">👤 <b>You:</b> {msg["content"]}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="chat-msg-ai">🤖 <b>Agent:</b> {msg["content"]}</div>', unsafe_allow_html=True)
        st.divider()
        user_input = st.text_input('Your message:', placeholder='Type something...', key='user_input')
        send_btn = st.button('Send ➤', use_container_width=True, disabled=not st.session_state.active_agent_id)
        if send_btn and user_input.strip() and st.session_state.active_agent_id:
            with st.spinner('Agent is thinking...'):
                try:
                    agent_id = st.session_state.active_agent_id
                    execute_url = f'{BASE_URL}/agents/{agent_id}/execute'
                    context = [{'role': m['role'], 'content': m['content']} for m in st.session_state.messages]
                    payload = {
                        'agent_type': 'langchain',
                        'agent_config': {'model': model},
                        'user_input': user_input,
                        'context': context,
                        'api_key': API_KEY
                    }
                    response = requests.post(execute_url, json=payload, timeout=60)
                    data = response.json()
                    if response.status_code == 429:
                        st.error('Rate limit exceeded! 100 calls/day limit reached.')
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
                            'time': datetime.now().strftime('%H:%M:%S'),
                            'input': user_input[:40] + '...' if len(user_input) > 40 else user_input,
                            'output': output[:60] + '...' if len(output) > 60 else output,
                            'model': model, 'tokens': tokens.get('prompt', 0) + tokens.get('completion', 0),
                            'cost': f'${cost:.6f}', 'time_ms': f'{ms}ms'
                        })
                        st.rerun()
                    else:
                        error = data.get('error', {})
                        st.error(f"Agent error: {error.get('message', str(error))}" if isinstance(error, dict) else f'Error: {data}')
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
        st.markdown('### 🔢 Rate Limit')
        calls_used = st.session_state.calls_today
        calls_left = max(0, 100 - calls_used)
        st.progress(calls_used / 100)
        st.markdown(f'**{calls_used}/100** calls used today')
        st.markdown(f'**{calls_left}** calls remaining')
        if calls_left < 20:
            st.warning('⚠️ Running low on calls!')
        st.divider()
        st.markdown('### 🕒 Execution History')
        if st.session_state.history:
            for h in reversed(st.session_state.history[-5:]):
                with st.expander(f"{h['time']} — {h['input']}"):
                    st.write(f"**Output:** {h['output']}")
                    st.write(f"**Tokens:** {h['tokens']} | **Cost:** {h['cost']} | **Time:** {h['time_ms']}")
        else:
            st.info('No executions yet — send a message!')

# ══════════════════════════════════════════════════════
# TAB 2 — REGISTER AGENT  (F21)
# ══════════════════════════════════════════════════════
with tab2:
    st.markdown('### 🚀 Register a New Agent')
    st.markdown('Fill in the details below to create your own AI agent.')
    st.divider()
    col1, col2 = st.columns([2, 1])
    with col1:
        agent_name    = st.text_input('Agent Name', placeholder='e.g. My Customer Support Bot', key='reg_name')
        agent_type    = st.selectbox('Framework', ['langchain', 'claude', 'streaming'], key='reg_type')
        agent_model   = st.selectbox('Model', ['gpt-3.5-turbo', 'gpt-4o', 'gpt-4'], key='reg_model')
        system_prompt = st.text_area('System Prompt', value='You are a helpful assistant.', height=120, key='reg_prompt')
        register_btn  = st.button('🚀 Register Agent', use_container_width=True)
        if register_btn and agent_name.strip():
            with st.spinner('Registering your agent...'):
                try:
                    payload = {
                        'name': agent_name,
                        'agent_type': agent_type,
                        'model': agent_model,
                        'system_prompt': system_prompt,
                        'username': st.session_state.username
                    }
                    r = requests.post(UPLOAD_URL, json=payload, timeout=15)
                    data = r.json()
                    if r.status_code in [200, 201] and data.get('agent_id'):
                        agent_id = data['agent_id']
                        st.session_state.registered_agents.append({
                            'agent_id': agent_id,
                            'name': agent_name,
                            'model': agent_model,
                            'type': agent_type
                        })
                        st.session_state.active_agent_id   = agent_id
                        st.session_state.active_agent_name = agent_name
                        st.session_state.messages = []  # clear chat for new agent
                        st.success(f'✅ Agent registered! ID: {agent_id}')
                        st.info(f'Agent is now active — go to Chat tab to start chatting!')
                        st.rerun()
                    else:
                        st.error(f'Registration failed: {data}')
                except Exception as e:
                    st.error(f'Error: {str(e)}')
        elif register_btn:
            st.warning('Please enter an agent name')
    with col2:
        st.markdown('### ℹ️ How it works')
        st.markdown('1. Fill in the form')
        st.markdown('2. Click Register Agent')
        st.markdown('3. A real UUID is generated')
        st.markdown('4. Agent is stored in DynamoDB')
        st.markdown('5. Chat tab switches to your new agent')
        st.divider()
        st.markdown('**Model Guide:**')
        st.markdown('• gpt-3.5-turbo — Fast, cheap')
        st.markdown('• gpt-4o — Balanced, smart')
        st.markdown('• gpt-4 — Most powerful')

# ══════════════════════════════════════════════════════
# TAB 3 — MY AGENTS  (F23)
# ══════════════════════════════════════════════════════
with tab3:
    st.markdown('### 📋 My Registered Agents')
    st.markdown('Agents you registered in this session:')
    st.divider()
    if not st.session_state.registered_agents:
        st.info('No agents registered yet — go to Register Agent tab to create one!')
    else:
        for agent in st.session_state.registered_agents:
            col1, col2, col3 = st.columns([3, 2, 1])
            with col1:
                st.markdown(f'**{agent["name"]}**')
                st.caption(f'ID: {agent["agent_id"]}')
            with col2:
                st.markdown(f'Model: `{agent["model"]}`')
                st.markdown(f'Type: `{agent["type"]}`')
            with col3:
                if st.button('💬 Use', key=f'use_{agent["agent_id"]}'):
                    st.session_state.active_agent_id   = agent['agent_id']
                    st.session_state.active_agent_name = agent['name']
                    st.session_state.messages = []
                    st.rerun()
            st.divider()
