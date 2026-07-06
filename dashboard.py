import streamlit as st
import requests
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

BASE_URL   = os.getenv('BASE_URL',   'https://hwb6mfqk9e.execute-api.us-east-1.amazonaws.com/prod')
AUTH_URL   = os.getenv('AUTH_URL',   f'{BASE_URL}/auth')
UPLOAD_URL = os.getenv('UPLOAD_URL', f'{BASE_URL}/agents/upload')
AGENTS_URL = os.getenv('AGENTS_URL', f'{BASE_URL}/agents')
API_KEY    = os.getenv('API_KEY',    'DishaRihan22')

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
    .delete-btn button { background: #c0392b !important; }
</style>
''', unsafe_allow_html=True)

# ── Session state ────────────────────────────────────────
for key, val in {
    'logged_in': False, 'username': '', 'token': '',
    'messages': [], 'history': [], 'total_cost': 0.0,
    'total_calls': 0, 'calls_today': 0,
    'registered_agents': [],
    'active_agent_id': None,
    'active_agent_name': None,
    'agents_loaded': False,  # F26 — track if agents loaded from API
}.items():
    if key not in st.session_state:
        st.session_state[key] = val

# ── HELPER: Load agents from API (F26) ───────────────────
def load_agents_from_api(username):
    try:
        r = requests.get(f'{AGENTS_URL}?username={username}', timeout=10)
        if r.status_code == 200:
            agents = r.json().get('agents', [])
            st.session_state.registered_agents = [
                {
                    'agent_id':   a.get('agent_id', ''),
                    'name':       a.get('name', 'Unnamed Agent'),
                    'model':      a.get('model', 'gpt-3.5-turbo'),
                    'type':       a.get('agent_type', 'langchain'),
                }
                for a in agents
            ]
            st.session_state.agents_loaded = True
    except Exception as e:
        st.session_state.agents_loaded = True  # don't retry on error
        print(f'Failed to load agents: {e}')

# ── HELPER: Delete agent (F25) ───────────────────────────
def delete_agent(agent_id):
    try:
        r = requests.delete(f'{AGENTS_URL}/{agent_id}', timeout=10)
        if r.status_code == 200:
            st.session_state.registered_agents = [
                a for a in st.session_state.registered_agents
                if a['agent_id'] != agent_id
            ]
            if st.session_state.active_agent_id == agent_id:
                st.session_state.active_agent_id   = None
                st.session_state.active_agent_name = None
                st.session_state.messages = []
            return True
        return False
    except Exception:
        return False

# ── LOGIN PAGE ───────────────────────────────────────────
if not st.session_state.logged_in:
    st.markdown('# 🤖 AgentFlow')
    st.markdown('*AI Agent Hosting Platform — Built by Rihan & Disha*')
    st.divider()
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown('### 🔐 Login to AgentFlow')
        username = st.text_input('Username', placeholder='Enter username')
        password = st.text_input('Password', placeholder='Enter password', type='password')
        login_btn = st.button('Login ➤', use_container_width=True)
        st.info('Demo: username = rihan or disha  |  password = password123')
        if login_btn:
            if not username or not password:
                st.warning('Please enter both username and password')
            else:
                with st.spinner('Logging in...'):
                    try:
                        r = requests.post(AUTH_URL, json={
                            'action': 'login', 'username': username, 'password': password
                        }, timeout=10)
                        data = r.json()
                        if r.status_code == 200 and data.get('token'):
                            st.session_state.logged_in = True
                            st.session_state.username  = data.get('username', username)
                            st.session_state.token     = data.get('token', '')
                            st.rerun()
                        else:
                            st.error('❌ Invalid username or password')
                    except requests.exceptions.Timeout:
                        st.error('⏱️ Login timed out — please try again')
                    except Exception as e:
                        st.error(f'Login failed: {str(e)}')
    st.stop()

# ── F26: Load agents from API on first load after login ──
if not st.session_state.agents_loaded:
    with st.spinner('Loading your agents...'):
        load_agents_from_api(st.session_state.username)

# ── HEADER ───────────────────────────────────────────────
col_h1, col_h2 = st.columns([3, 1])
with col_h1:
    st.markdown('# 🤖 AgentFlow Dashboard')
    active_name = st.session_state.active_agent_name or 'No agent selected'
    st.markdown(f'*Logged in as **{st.session_state.username}** | Active: **{active_name}***')
with col_h2:
    if st.button('🚪 Logout', use_container_width=True):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
st.divider()

tab1, tab2, tab3 = st.tabs(['💬 Chat', '🚀 Register Agent', '📋 My Agents'])

# ══ TAB 1 — CHAT ════════════════════════════════════════
with tab1:
    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown('### 💬 Chat with Agent')
        if not st.session_state.active_agent_id:
            st.warning('⚠️ No agent selected. Go to **Register Agent** to create one, or **My Agents** to select an existing one.')
        else:
            st.success(f'Chatting with: **{st.session_state.active_agent_name}** ({st.session_state.active_agent_id[:8]}...)')
        model = st.selectbox('Model', ['gpt-3.5-turbo', 'gpt-4o', 'gpt-4'], key='model')
        st.divider()
        if st.session_state.messages:
            for msg in st.session_state.messages:
                if msg['role'] == 'user':
                    st.markdown(f'<div class="chat-msg-user">👤 <b>You:</b> {msg["content"]}</div>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<div class="chat-msg-ai">🤖 <b>Agent:</b> {msg["content"]}</div>', unsafe_allow_html=True)
        else:
            st.markdown('<p style="color:#999; text-align:center; margin:40px 0;">No messages yet — say something!</p>', unsafe_allow_html=True)
        st.divider()
        user_input = st.text_input('Your message:', placeholder='Type something...', key='user_input')
        send_btn = st.button('Send ➤', use_container_width=True, disabled=not st.session_state.active_agent_id)
        if send_btn and user_input.strip() and st.session_state.active_agent_id:
            with st.spinner('🤖 Agent is thinking...'):
                try:
                    agent_id    = st.session_state.active_agent_id
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
                        st.error('🚫 Rate limit reached! You have used all 100 calls for today. Try again tomorrow.')
                    elif response.status_code == 401:
                        st.error('🔐 Unauthorized — invalid API key')
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
                        msg = error.get('message', str(error)) if isinstance(error, dict) else str(data)
                        st.error(f'❌ Agent error: {msg}')
                except requests.exceptions.Timeout:
                    st.error('⏱️ Request timed out — agent took too long. Try a shorter message.')
                except requests.exceptions.ConnectionError:
                    st.error('🔌 Connection error — check your internet connection.')
                except Exception as e:
                    st.error(f'Unexpected error: {str(e)}')
        if st.session_state.messages:
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
        st.progress(min(calls_used / 100, 1.0))
        st.markdown(f'**{calls_used}/100** calls used today')
        st.markdown(f'**{calls_left}** calls remaining')
        if calls_left == 0:
            st.error('🚫 Rate limit reached!')
        elif calls_left < 20:
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

# ══ TAB 2 — REGISTER AGENT ══════════════════════════════
with tab2:
    st.markdown('### 🚀 Register a New Agent')
    st.markdown('Create your own AI agent with a custom name, model, and personality.')
    st.divider()
    col1, col2 = st.columns([2, 1])
    with col1:
        agent_name    = st.text_input('Agent Name *', placeholder='e.g. My Customer Support Bot', key='reg_name')
        agent_type    = st.selectbox('Framework', ['langchain', 'claude', 'streaming'], key='reg_type')
        agent_model   = st.selectbox('Model', ['gpt-3.5-turbo', 'gpt-4o', 'gpt-4'], key='reg_model')
        system_prompt = st.text_area('System Prompt', value='You are a helpful assistant.', height=120, key='reg_prompt',
                                     help='This defines your agent personality and behavior')
        register_btn  = st.button('🚀 Register Agent', use_container_width=True)
        if register_btn:
            if not agent_name.strip():
                st.warning('⚠️ Please enter an agent name')
            else:
                with st.spinner('Registering your agent...'):
                    try:
                        payload = {
                            'name':          agent_name,
                            'agent_type':    agent_type,
                            'model':         agent_model,
                            'system_prompt': system_prompt,
                            'username':      st.session_state.username
                        }
                        r = requests.post(UPLOAD_URL, json=payload, timeout=15)
                        data = r.json()
                        if r.status_code in [200, 201] and data.get('agent_id'):
                            agent_id = data['agent_id']
                            st.session_state.registered_agents.append({
                                'agent_id': agent_id, 'name': agent_name,
                                'model': agent_model, 'type': agent_type
                            })
                            st.session_state.active_agent_id   = agent_id
                            st.session_state.active_agent_name = agent_name
                            st.session_state.messages = []
                            st.success(f'✅ Agent registered successfully!')
                            st.code(f'Agent ID: {agent_id}')
                            st.info('Go to **Chat** tab to start chatting with your new agent!')
                            st.rerun()
                        else:
                            st.error(f'❌ Registration failed: {data.get("error", data)}')
                    except requests.exceptions.Timeout:
                        st.error('⏱️ Registration timed out — please try again')
                    except Exception as e:
                        st.error(f'❌ Error: {str(e)}')
    with col2:
        st.markdown('### ℹ️ How it works')
        st.markdown('1. Fill in the form')
        st.markdown('2. Click Register Agent')
        st.markdown('3. A real UUID is generated')
        st.markdown('4. Agent stored in DynamoDB')
        st.markdown('5. Chat switches to your agent')
        st.divider()
        st.markdown('**Model Guide:**')
        st.markdown('• **gpt-3.5-turbo** — Fast & cheap (~$0.000026/call)')
        st.markdown('• **gpt-4o** — Balanced & smart (~$0.0001/call)')
        st.markdown('• **gpt-4** — Most powerful (~$0.0003/call)')

# ══ TAB 3 — MY AGENTS ══════════════════════════════════
with tab3:
    col_title, col_refresh = st.columns([3, 1])
    with col_title:
        st.markdown('### 📋 My Registered Agents')
    with col_refresh:
        if st.button('🔄 Refresh', use_container_width=True):
            st.session_state.agents_loaded = False
            st.rerun()
    st.divider()
    if not st.session_state.registered_agents:
        st.info('📭 No agents found. Go to **Register Agent** tab to create your first agent!')
    else:
        st.markdown(f'**{len(st.session_state.registered_agents)}** agent(s) registered to **{st.session_state.username}**')
        st.divider()
        for agent in st.session_state.registered_agents:
            is_active = agent['agent_id'] == st.session_state.active_agent_id
            col1, col2, col3, col4 = st.columns([3, 2, 1, 1])
            with col1:
                prefix = '✅ ' if is_active else ''
                st.markdown(f'**{prefix}{agent["name"]}**')
                st.caption(f'ID: {agent["agent_id"]}')
            with col2:
                st.markdown(f'Model: `{agent["model"]}`')
                st.markdown(f'Type: `{agent["type"]}`')
            with col3:
                if not is_active:
                    if st.button('💬 Use', key=f'use_{agent["agent_id"]}'):
                        st.session_state.active_agent_id   = agent['agent_id']
                        st.session_state.active_agent_name = agent['name']
                        st.session_state.messages = []
                        st.rerun()
                else:
                    st.markdown('*Active*')
            with col4:
                # F25 — Delete button
                if st.button('🗑️', key=f'del_{agent["agent_id"]}', help=f'Delete {agent["name"]}'):
                    with st.spinner(f'Deleting {agent["name"]}...'):
                        success = delete_agent(agent['agent_id'])
                        if success:
                            st.success(f'✅ Agent deleted!')
                            st.rerun()
                        else:
                            st.error('❌ Delete failed — try again')
            st.divider()
