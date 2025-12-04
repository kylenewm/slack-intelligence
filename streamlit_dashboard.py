#!/usr/bin/env python3
"""
Streamlit Dashboard for Slack Intelligence
Visual interface for viewing and managing prioritized messages.
Features: Smart Inbox, Jira Integration, Context Engine Debugger
"""

import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Page config (must be first)
st.set_page_config(
    page_title="Traverse.ai Dashboard",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Force Sidebar Open on Load (via Session State hack if needed, but config usually enough)
if "sidebar_state" not in st.session_state:
    st.session_state.sidebar_state = "expanded"

# Environment Selection
if 'env_mode' not in st.session_state:
    st.session_state.env_mode = "Local"

# Configuration
LOCAL_PORT = int(os.getenv("API_PORT", "8000"))
LOCAL_API = f"http://localhost:{LOCAL_PORT}"
PROD_API = "https://slack-automation-production.up.railway.app"

# Dynamic API Base - use .get() to avoid errors during import
API_BASE = PROD_API if st.session_state.get('env_mode', 'Local') == "Production" else LOCAL_API

# Custom CSS - FIXED VERSION
st.markdown("""
<style>
    /* SIDEBAR TOGGLE - ALWAYS VISIBLE */
    button[kind="header"] {
        display: block !important;
        visibility: visible !important;
        opacity: 1 !important;
    }
    
    [data-testid="collapsedControl"] {
        display: flex !important;
        visibility: visible !important;
        position: fixed !important;
        top: 0.5rem !important;
        left: 0.5rem !important;
        z-index: 999999 !important;
        background: #667eea !important;
        border-radius: 8px !important;
        padding: 8px !important;
        color: white !important;
    }
    
    [data-testid="collapsedControl"] svg {
        stroke: white !important;
    }
    
    /* Basic Layout */
    .block-container {
        padding-top: 4rem !important;
        max-width: 95% !important;
    }
    
    .stApp {
        background-color: #f8f9fa;
    }
    
    /* ============ MAIN CONTENT - DARK TEXT ============ */
    .main h1, .main h2, .main h3, .main h4, .main h5, .main h6 {
        color: #0f172a !important;
    }
    
    .main p, .main span, .main div, .main li, .main label {
        color: #1e293b !important;
    }
    
    /* Force dark text in stMarkdown within main */
    .main .stMarkdown, .main .stMarkdown p, .main .stMarkdown span, .main .stMarkdown h3 {
        color: #1e293b !important;
    }
    
    /* Metric text specifically */
    [data-testid="stMetricLabel"] {
        color: #64748b !important;
    }
    [data-testid="stMetricValue"] {
        color: #0f172a !important;
    }

    /* Metrics Styling */
    [data-testid="stMetric"] {
        background-color: white;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 1px 3px 0 rgb(0 0 0 / 0.1);
        border: 1px solid #e2e8f0;
    }

    /* Priority Badges */
    .priority-critical { background-color: #fee2e2; color: #991b1b !important; padding: 4px 10px; border-radius: 12px; font-weight: 700; font-size: 0.7rem; text-transform: uppercase; }
    .priority-high { background-color: #ffedd5; color: #9a3412 !important; padding: 4px 10px; border-radius: 12px; font-weight: 700; font-size: 0.7rem; text-transform: uppercase; }
    .priority-medium { background-color: #dbeafe; color: #1e40af !important; padding: 4px 10px; border-radius: 12px; font-weight: 700; font-size: 0.7rem; text-transform: uppercase; }
    .priority-low { background-color: #f1f5f9; color: #475569 !important; padding: 4px 10px; border-radius: 12px; font-weight: 700; font-size: 0.7rem; text-transform: uppercase; }
    
    /* Buttons */
    .stButton button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
    }
    
    /* Main content dropdown/slider labels */
    .main .stSelectbox label, .main .stSlider label {
        color: #1e293b !important;
    }
    
    /* Form selectbox (Type dropdown) - white text on dark background */
    .main .stSelectbox div[data-baseweb="select"] * {
        color: white !important;
    }
    .main .stSelectbox div[data-baseweb="select"] svg {
        fill: white !important;
    }
    
    /* ============ SIDEBAR - WHITE TEXT ============ */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%);
    }
    
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] span,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] .stMarkdown {
        color: #f8fafc !important;
    }
    
    /* Sidebar radio button labels */
    [data-testid="stSidebar"] .stRadio label span {
        color: #f8fafc !important;
    }
    
    /* Sidebar slider labels */
    [data-testid="stSidebar"] .stSlider label {
        color: #f8fafc !important;
    }
    
    /* Sidebar selectbox label */
    [data-testid="stSidebar"] .stSelectbox label {
        color: #f8fafc !important;
    }
</style>
""", unsafe_allow_html=True)

def check_server():
    """Check if API server is running"""
    try:
        response = requests.get(f"{API_BASE}/health", timeout=2)
        return response.status_code == 200
    except:
        return False

@st.cache_data(ttl=30)
def get_inbox(view="all", hours_ago=24, limit=50, api_base=None):
    """Fetch messages from API - cached for 30 seconds"""
    # Use passed api_base or fall back to global (but passed one ensures cache invalidation)
    base = api_base or API_BASE
    try:
        response = requests.get(
            f"{base}/api/slack/inbox",
            params={"view": view, "hours_ago": hours_ago, "limit": limit},
            timeout=10
        )
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return None

def get_stats():
    """Fetch system stats"""
    try:
        response = requests.get(f"{API_BASE}/api/slack/stats", timeout=5)
        if response.status_code == 200:
            return response.json()
        return None
    except:
        return None

def format_time_ago(timestamp_str):
    """Format timestamp as relative time"""
    try:
        if isinstance(timestamp_str, str):
            timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        else:
            timestamp = timestamp_str
        
        # Timestamps in DB are UTC naive. Convert to local for display.
        # Add UTC timezone, then convert to local
        from datetime import timezone
        if timestamp.tzinfo is None:
            # Assume UTC, make aware
            timestamp_utc = timestamp.replace(tzinfo=timezone.utc)
        else:
            timestamp_utc = timestamp
        
        # Convert to local time for display comparison
        timestamp_local = timestamp_utc.astimezone()  # Converts to system local time
        now_local = datetime.now().astimezone()
        
        delta = now_local - timestamp_local
        total_seconds = delta.total_seconds()
        
        if total_seconds < 0:
            return "just now"
        
        hours = int(total_seconds // 3600)
        minutes = int((total_seconds % 3600) // 60)
        
        if hours >= 24:
            return f"{hours // 24}d ago"
        elif hours >= 1:
            return f"{hours}h ago"
        elif minutes >= 1:
            return f"{minutes}m ago"
        else:
            return "just now"
    except:
        return "unknown"

# --- Main App ---
def main():
    # Professional Sidebar
    with st.sidebar:
        # Logo & Brand
        st.markdown("""
        <div style="text-align: center; padding: 20px 0;">
            <div style="font-size: 2.5rem; margin-bottom: 8px;">🧠</div>
            <div style="font-size: 1.5rem; font-weight: 700; color: white; letter-spacing: -0.5px;">Traverse.ai</div>
            <div style="font-size: 0.75rem; color: #94a3b8; text-transform: uppercase; letter-spacing: 1px; margin-top: 4px;">Intelligence Dashboard</div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Environment Switcher - Modern Toggle Style
        st.markdown("""
        <div style="margin: 20px 0;">
            <div style="color: #cbd5e1; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px;">Environment</div>
        </div>
        """, unsafe_allow_html=True)
        
        env = st.radio(
            "env_label",
            ["Local", "Production"],
            index=0 if st.session_state.env_mode == "Local" else 1,
            label_visibility="collapsed"
        )
        st.session_state.env_mode = env
        
        # Status Indicator
        server_online = check_server()
        status_color = "#10b981" if server_online else "#ef4444"
        status_text = "Online" if server_online else "Offline"
        
        st.markdown(f"""
        <div style="
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 8px;
            padding: 12px;
            margin: 16px 0;
        ">
            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 6px;">
                <div style="width: 8px; height: 8px; background: {status_color}; border-radius: 50%; box-shadow: 0 0 8px {status_color};"></div>
                <span style="color: #e2e8f0; font-weight: 600; font-size: 0.9rem;">{status_text}</span>
            </div>
            <div style="color: #94a3b8; font-size: 0.75rem; font-family: monospace;">{API_BASE}</div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Navigation
        st.markdown("""
        <div style="color: #cbd5e1; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 1px; margin: 20px 0 12px 0;">Navigation</div>
        """, unsafe_allow_html=True)
        
        page = st.radio(
            "nav_label",
            ["📥 Smart Inbox", "🧠 Context Engine", "📊 Analytics", "⚙️ Settings"],
            label_visibility="collapsed"
        )
        
        st.markdown("---")

    # Route to correct page
    if "Context Engine" in page:
        render_debugger()
    elif "Analytics" in page:
        render_analytics()
    elif "Settings" in page:
        render_settings()
    else:
        # INBOX FILTERS (Moved to Sidebar for Stability)
        with st.sidebar:
            st.markdown("""
            <div style="color: #cbd5e1; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 1px; margin: 0 0 12px 0;">Inbox Controls</div>
            """, unsafe_allow_html=True)
            
            view_filter = st.selectbox(
                "Filter View",
                options=["all", "needs_response", "high_priority", "fyi", "low_priority"],
                format_func=lambda x: x.replace("_", " ").title(),
                key="inbox_view_filter"
            )
            
            # Channel filter - uses channels from session state (populated after fetch)
            available_channels = st.session_state.get('available_channels', ["All Channels"])
            channel_filter = st.selectbox(
                "Filter by Channel",
                options=available_channels,
                key="inbox_channel_filter",
                help="Group messages by channel to see conversations together"
            )
            
            min_score = st.slider("Min Priority Score", 0, 100, 0, key="inbox_min_score")
            limit_filter = st.slider("Message Limit", 10, 100, 50, key="inbox_limit")
            hours_ago = st.slider("Time Window (hours)", 1, 168, 72, key="inbox_hours_ago", 
                                 help="Show messages from last N hours (168 = 7 days)")
            
        render_inbox(view_filter, limit_filter, min_score, channel_filter, hours_ago)

    # Footer (Fixed at bottom)
    with st.sidebar:
        st.markdown("""
        <div style="margin-top: 40px; border-top: 1px solid rgba(255, 255, 255, 0.1); padding-top: 16px; text-align: center;">
            <div style="color: #64748b; font-size: 0.7rem;">Powered by GPT-4o & Exa AI</div>
        </div>
        """, unsafe_allow_html=True)

def render_debugger():
    # Header in purple gradient (matching Smart Inbox)
    st.markdown("""
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 20px 24px; border-radius: 12px; margin-bottom: 24px;">
        <h2 style="color: white !important; margin: 0;">🧠 Context Engine</h2>
        <p style="color: rgba(255,255,255,0.8) !important; margin: 8px 0 0 0;">Visualize the AI's internal knowledge: Identity, Memory, and Self-Awareness.</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Custom styled tab headers
    st.markdown("""
    <style>
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
        }
        .stTabs [data-baseweb="tab"] {
            background: white !important;
            border: 1px solid #e2e8f0 !important;
            border-radius: 8px !important;
            padding: 12px 20px !important;
            color: #334155 !important;
            font-weight: 600 !important;
        }
        .stTabs [data-baseweb="tab"]:hover {
            background: #f8fafc !important;
            border-color: #8b5cf6 !important;
        }
        .stTabs [aria-selected="true"] {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
            color: white !important;
            border-color: #8b5cf6 !important;
        }
        .stTabs [data-baseweb="tab-highlight"] {
            display: none !important;
        }
        .stTabs [data-baseweb="tab-border"] {
            display: none !important;
        }
    </style>
    """, unsafe_allow_html=True)
    
    tab1, tab2, tab3, tab4 = st.tabs(["🏢 Identity & Values", "🧠 Institutional Memory", "👁️ Self-Awareness", "📋 PRDs/Plans"])
    
    with tab1:
        try:
            with open("backend/context/identity.md", "r") as f:
                identity_content = f.read()
            
            # Parse and display as styled cards (similar to Memory)
            st.markdown("""
            <div style="background: white; border-left: 4px solid #667eea; border-radius: 8px; padding: 20px; margin-bottom: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
                <div style="color: #667eea; font-weight: 700; font-size: 1.1rem; margin-bottom: 12px;">🏢 Company Identity</div>
                <div style="color: #64748b; margin-bottom: 8px;"><strong style="color: #334155;">Company:</strong> Traverse.ai</div>
                <div style="color: #64748b; margin-bottom: 8px;"><strong style="color: #334155;">Product:</strong> Traverse Core (Enterprise Slack Middleware)</div>
                <div style="background: #f8fafc; padding: 12px; border-radius: 6px; color: #334155;">
                    <strong>Mission:</strong> "Traversing the noise to find signal in your enterprise communications."
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("""
            <div style="background: white; border-left: 4px solid #8b5cf6; border-radius: 8px; padding: 20px; margin-bottom: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
                <div style="color: #8b5cf6; font-weight: 700; font-size: 1.1rem; margin-bottom: 12px;">💎 Core Value Proposition</div>
                <div style="color: #334155; line-height: 1.6;">
                    We build the ultimate "Slack OS" layer. We don't just dump notifications; we intelligently route, prioritize, and enrich messages so engineering teams can focus on deep work.
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("""
            <div style="background: white; border-left: 4px solid #10b981; border-radius: 8px; padding: 20px; margin-bottom: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
                <div style="color: #10b981; font-weight: 700; font-size: 1.1rem; margin-bottom: 12px;">🚀 Key Features</div>
                <ul style="color: #334155; line-height: 1.8; margin: 0; padding-left: 20px;">
                    <li><strong>Intelligent Ingestion:</strong> Capture every message, thread, and reaction in real-time</li>
                    <li><strong>Context-Aware Prioritization:</strong> AI understands "urgent" vs "noise" based on your tech stack</li>
                    <li><strong>Automated Action:</strong> Turn conversations into Jira tickets and Notion docs</li>
                    <li><strong>Research Assistant:</strong> Research solutions using the open web before the engineer sees the bug</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("""
            <div style="background: white; border-left: 4px solid #f59e0b; border-radius: 8px; padding: 20px; margin-bottom: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
                <div style="color: #f59e0b; font-weight: 700; font-size: 1.1rem; margin-bottom: 12px;">⭐ Core Values</div>
                <div style="color: #334155; line-height: 1.8;">
                    <div style="margin-bottom: 8px;">• <strong>Developer Experience First:</strong> If it adds friction, it's a bug</div>
                    <div style="margin-bottom: 8px;">• <strong>Context is King:</strong> A message without context is noise</div>
                    <div>• <strong>Automation over Administration:</strong> Engineers should write code, not Jira tickets</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
        except:
            st.warning("Identity file not found locally.")

    with tab2:
        try:
            with open("backend/context/institutional_memory.json", "r") as f:
                import json
                memory = json.load(f)
            
            for item in memory:
                # Custom styled cards instead of expanders
                st.markdown(f"""
                <div style="background: white; border-left: 4px solid #8b5cf6; border-radius: 8px; padding: 20px; margin-bottom: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
                    <div style="color: #8b5cf6; font-weight: 700; font-size: 1.1rem; margin-bottom: 12px;">🔧 {item.get('issue')}</div>
                    <div style="color: #64748b; margin-bottom: 12px;"><strong style="color: #334155;">Context:</strong> {item.get('context')}</div>
                    <div style="background: #f8fafc; padding: 12px; border-radius: 6px; color: #334155;">
                        <strong>Solution:</strong> {item.get('solution')}
                    </div>
                </div>
                """, unsafe_allow_html=True)
        except Exception as e:
            st.warning(f"Memory file not found: {e}")
            
    with tab3:
        st.markdown("""
        <div style="background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 8px; padding: 16px; color: #1e40af; margin-bottom: 16px;">
            ℹ️ The AI scans the codebase structure dynamically to understand the API surface.
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("🔍 Run Live Codebase Scan", use_container_width=True):
            with st.spinner("Scanning backend..."):
                try:
                    from backend.services.context_service import ContextService
                    ctx = ContextService()
                    codebase_map = ctx._scan_codebase()
                    st.code(codebase_map, language="text")
                except Exception as e:
                    st.error(f"Scan failed: {e}")
    
    with tab4:
        st.markdown("""
        <div style="background: #fef3c7; border: 1px solid #fcd34d; border-radius: 8px; padding: 16px; color: #92400e; margin-bottom: 16px;">
            📋 Product plans and PRDs are injected into AI prompts for context-aware prioritization.
        </div>
        """, unsafe_allow_html=True)
        
        try:
            from backend.services.context_service import ContextService
            ctx = ContextService()
            plans = ctx.get_plans_list()
            
            if not plans:
                st.info("No PRDs found in backend/context/plans/")
            else:
                for plan in plans:
                    # Card for each plan
                    st.markdown(f"""
                    <div style="background: white; border-left: 4px solid #f59e0b; border-radius: 8px; padding: 20px; margin-bottom: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
                        <div style="color: #f59e0b; font-weight: 700; font-size: 1.1rem; margin-bottom: 8px;">📋 {plan['title']}</div>
                        <div style="color: #64748b; font-size: 0.85rem; margin-bottom: 12px;">📄 {plan['filename']}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Expandable content
                    with st.expander(f"View full content: {plan['title']}", expanded=False):
                        st.markdown(plan['content'])
                        
        except Exception as e:
            st.error(f"Error loading plans: {e}")

def render_analytics():
    # Header in dark container
    st.markdown("""
    <div style="background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); padding: 20px 24px; border-radius: 12px; margin-bottom: 24px;">
        <h2 style="color: white !important; margin: 0;">📊 Analytics</h2>
    </div>
    """, unsafe_allow_html=True)
    st.info("Analytics dashboard coming soon...")

def render_settings():
    # Inject CSS specifically for Settings page to force light theme on inputs
    st.markdown("""
    <style>
    /* Force light backgrounds on text areas in settings */
    .stTextArea textarea {
        background-color: #f8fafc !important;
        color: #1e293b !important;
        border: 1px solid #e2e8f0 !important;
    }
    .stTextArea textarea::placeholder {
        color: #94a3b8 !important;
    }
    /* Settings page specific - force ALL text dark - NUCLEAR OPTION */
    .settings-card, .settings-card * {
        color: #0f172a !important;
    }
    .settings-card h3 {
        color: #0f172a !important;
        margin: 0 0 4px 0 !important;
        font-size: 1.1rem !important;
    }
    .settings-card p {
        color: #475569 !important;
        font-size: 0.85rem !important;
        margin: 0 !important;
    }
    /* Override any conflicting rules */
    div[style*="border-left: 4px"] h3,
    div[style*="border-left: 4px"] p {
        color: #0f172a !important;
    }
    div[style*="border-left: 4px"] p {
        color: #475569 !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Header with inline styling (same pattern as other pages)
    st.markdown("""
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 20px 24px; border-radius: 12px; margin-bottom: 24px;">
        <h2 style="color: white !important; margin: 0;">⚙️ Priority Settings</h2>
        <p style="color: rgba(255,255,255,0.8) !important; margin: 8px 0 0 0;">Configure how messages are scored and prioritized.</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Load current preferences
    try:
        response = requests.get(f"{API_BASE}/api/slack/preferences", params={"user_id": "default"}, timeout=5)
        if response.status_code == 200:
            prefs = response.json()
        else:
            prefs = {"key_people": [], "key_channels": [], "key_keywords": [], "mute_channels": []}
    except:
        prefs = {"key_people": [], "key_channels": [], "key_keywords": [], "mute_channels": []}
    
    # VIP People Section
    st.markdown("""
    <div class="settings-card" style="background: white; border-left: 4px solid #667eea; border-radius: 8px; padding: 16px; margin-bottom: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
        <h3 style="color: #0f172a !important;">👑 VIP People</h3>
        <p style="color: #475569 !important;">Messages from these people will be scored higher. Enter Slack user IDs or names, comma-separated.</p>
    </div>
    """, unsafe_allow_html=True)
    key_people = st.text_area(
        "VIP People",
        value=", ".join(prefs.get("key_people", [])),
        key="settings_key_people",
        label_visibility="collapsed",
        height=80,
        placeholder="e.g., Jordan CTO, Sarah PM, U12345678"
    )
    
    # Priority Channels Section
    st.markdown("""
    <div class="settings-card" style="background: white; border-left: 4px solid #10b981; border-radius: 8px; padding: 16px; margin-bottom: 8px; margin-top: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
        <h3 style="color: #0f172a !important;">📢 Priority Channels</h3>
        <p style="color: #475569 !important;">Messages in these channels will be scored higher. Enter channel IDs or names, comma-separated.</p>
    </div>
    """, unsafe_allow_html=True)
    key_channels = st.text_area(
        "Priority Channels",
        value=", ".join(prefs.get("key_channels", [])),
        key="settings_key_channels",
        label_visibility="collapsed",
        height=80,
        placeholder="e.g., engineering-alerts, incidents, C12345678"
    )
    
    # Priority Keywords Section
    st.markdown("""
    <div class="settings-card" style="background: white; border-left: 4px solid #f59e0b; border-radius: 8px; padding: 16px; margin-bottom: 8px; margin-top: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
        <h3 style="color: #0f172a !important;">🔑 Priority Keywords</h3>
        <p style="color: #475569 !important;">Messages containing these keywords will be scored higher. Comma-separated.</p>
    </div>
    """, unsafe_allow_html=True)
    key_keywords = st.text_area(
        "Priority Keywords",
        value=", ".join(prefs.get("key_keywords", [])),
        key="settings_key_keywords",
        label_visibility="collapsed",
        height=80,
        placeholder="e.g., urgent, production, deployment, outage"
    )
    
    # Muted Channels Section
    st.markdown("""
    <div class="settings-card" style="background: white; border-left: 4px solid #ef4444; border-radius: 8px; padding: 16px; margin-bottom: 8px; margin-top: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
        <h3 style="color: #0f172a !important;">🔇 Muted Channels</h3>
        <p style="color: #475569 !important;">Messages in these channels will be scored lower. Comma-separated.</p>
    </div>
    """, unsafe_allow_html=True)
    mute_channels = st.text_area(
        "Muted Channels",
        value=", ".join(prefs.get("mute_channels", [])),
        key="settings_mute_channels",
        label_visibility="collapsed",
        height=80,
        placeholder="e.g., random, watercooler, social"
    )
    
    st.markdown("---")
    
    if st.button("💾 Save Preferences", key="save_prefs_btn", use_container_width=True):
        try:
            response = requests.post(
                f"{API_BASE}/api/slack/preferences",
                params={
                    "user_id": "default",
                    "key_people": key_people,
                    "key_channels": key_channels,
                    "key_keywords": key_keywords,
                    "mute_channels": mute_channels
                },
                timeout=10
            )
            if response.status_code == 200:
                st.success("✅ Preferences saved! New messages will use these weights.")
            else:
                st.error(f"Failed to save: {response.text}")
        except Exception as e:
            st.error(f"Connection failed: {e}")

def render_inbox(view="all", limit=50, min_score=0, channel_filter="All Channels", hours_ago=72):
    # Page Header in lighter container
    col_title, col_refresh = st.columns([4, 1])
    with col_title:
        st.markdown("""
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 16px 24px; border-radius: 12px; display: inline-block; margin-top: 1rem;">
            <h2 style="color: white !important; margin: 0;">📥 Smart Inbox</h2>
        </div>
        """, unsafe_allow_html=True)
    with col_refresh:
        st.markdown("<div style='margin-top: 1rem;'></div>", unsafe_allow_html=True)
        if st.button("🔄 Refresh", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
    
    st.markdown("<br>", unsafe_allow_html=True)

    # Fetch Data
    with st.spinner(f"Fetching from {st.session_state.env_mode}..."):
        data = get_inbox(view, hours_ago=hours_ago, limit=limit, api_base=API_BASE)
    
    if not data or not data.get('messages'):
        st.info("📭 Inbox is empty.")
        return

    # Metrics
    stats = data.get('messages', [])
    
    # Extract unique channels and update the sidebar filter
    unique_channels = sorted(set(m.get('channel_name', 'unknown') for m in stats))
    if unique_channels:
        # Store channels in session state for the sidebar to use
        st.session_state['available_channels'] = ["All Channels"] + unique_channels
    
    # Filter by channel
    if channel_filter and channel_filter != "All Channels":
        stats = [m for m in stats if m.get('channel_name') == channel_filter]
    
    # Filter by min_score
    if min_score > 0:
        stats = [m for m in stats if m.get('priority_score', 0) >= min_score]
    avg = sum(m['priority_score'] for m in stats) / len(stats) if stats else 0
    critical_count = sum(1 for m in stats if m.get('priority_score', 0) >= 90)
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("📬 Total", len(stats))
    m2.metric("⚡ Avg Priority", f"{avg:.1f}")
    m3.metric("🔴 Critical", critical_count)
    m4.metric("🌐 Source", st.session_state.env_mode)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Filter out locally archived messages
    if 'archived_messages' not in st.session_state:
        st.session_state.archived_messages = set()
        
    filtered_stats = [m for m in stats if m['id'] not in st.session_state.archived_messages]
    
    for msg in filtered_stats:
        score = msg.get('priority_score', 0)
        
        # Determine styling based on score
        if score >= 90:
            priority_label = "CRITICAL"
            badge_class = "priority-critical"
            border_color = "#dc2626"
        elif score >= 70:
            priority_label = "HIGH"
            badge_class = "priority-high"
            border_color = "#ea580c"
        elif score >= 50:
            priority_label = "MEDIUM"
            badge_class = "priority-medium"
            border_color = "#2563eb"
        else:
            priority_label = "LOW"
            badge_class = "priority-low"
            border_color = "#64748b"
            
        # Modern Card Layout
        st.markdown(f"""
        <div style="
            background: white;
            border-left: 4px solid {border_color};
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 16px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        ">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                <div style="display: flex; gap: 12px; align-items: center;">
                    <span class='{badge_class}'>{priority_label}</span>
                    <span style="color: #64748b; font-size: 0.9rem;">#{msg.get('channel_name')}</span>
                </div>
                <div style="display: flex; gap: 16px; align-items: center;">
                    <span style="background: #f1f5f9; padding: 4px 12px; border-radius: 6px; font-weight: 600; color: #334155;">Score: {score}</span>
                    <span style="color: #94a3b8; font-size: 0.85rem;">{format_time_ago(msg.get('timestamp'))}</span>
                </div>
            </div>
            <div style="color: #1e293b; line-height: 1.6; margin-top: 12px;">
                <strong>{msg.get('user_name')}:</strong> {msg.get('text')}
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # AI Analysis Section
        st.markdown(f"""
        <div style="
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            padding: 16px;
            margin-bottom: 16px;
        ">
            <div style="color: #475569; font-weight: 600; margin-bottom: 8px;">💡 AI Analysis</div>
            <div style="color: #334155; line-height: 1.6;">{msg.get('priority_reason')}</div>
        </div>
        """, unsafe_allow_html=True)
        
        # Bug Analysis Button
        if st.button("🔍 Analyze Bug", key=f"analyze_{msg['id']}", use_container_width=False):
            st.session_state[f"show_bug_analysis_{msg['id']}"] = True
        
        # Bug Analysis Display
        if st.session_state.get(f"show_bug_analysis_{msg['id']}", False):
            st.markdown("---")
            with st.spinner("Running bug analysis..."):
                try:
                    response = requests.get(
                        f"{API_BASE}/api/slack/integrations/bug-analysis/{msg['id']}",
                        timeout=30
                    )
                    if response.status_code == 200:
                        analysis = response.json()
                        
                        if analysis.get('is_bug'):
                            st.markdown("### 🐛 Bug Analysis Pipeline")
                            
                            # Detection
                            detection = analysis.get('detection', {})
                            st.markdown("#### 1️⃣ Ticket Type Detection")
                            col1, col2 = st.columns(2)
                            col1.metric("Type", detection.get('ticket_type', 'unknown'))
                            col2.metric("Needs Research", "No" if not detection.get('needs_research') else "Yes")
                            st.info(f"**Reason:** {detection.get('reason', 'N/A')}")
                            
                            # Code Analysis
                            code_analysis = analysis.get('code_analysis', {})
                            patterns = code_analysis.get('patterns', {})
                            
                            st.markdown("#### 2️⃣ Extracted Patterns")
                            pattern_cols = st.columns(4)
                            if patterns.get('exception_types'):
                                pattern_cols[0].metric("Exceptions", len(patterns['exception_types']))
                                st.code(", ".join(patterns['exception_types']))
                            if patterns.get('status_codes'):
                                pattern_cols[1].metric("Status Codes", len(patterns['status_codes']))
                                st.code(", ".join(patterns['status_codes']))
                            if patterns.get('file_mentions'):
                                pattern_cols[2].metric("Files", len(patterns['file_mentions']))
                                st.code(", ".join(patterns['file_mentions']))
                            
                            if patterns.get('error_description'):
                                st.info(f"**Error:** {patterns['error_description']}")
                            if patterns.get('likely_cause'):
                                st.warning(f"**Likely Cause:** {patterns['likely_cause']}")
                            
                            # Codebase Matches
                            codebase_matches = code_analysis.get('codebase_matches', [])
                            st.markdown("#### 3️⃣ Codebase Matches")
                            if codebase_matches:
                                st.success(f"Found {len(codebase_matches)} relevant file(s)")
                                for match in codebase_matches[:3]:
                                    with st.expander(f"📄 {match.get('file', 'unknown')}"):
                                        if match.get('line'):
                                            st.text(f"Line {match['line']}")
                                        if match.get('snippet'):
                                            st.code(match['snippet'], language='python')
                            else:
                                st.info("No codebase matches found")
                            
                            # Memory Matches
                            memory_matches = code_analysis.get('memory_matches', [])
                            st.markdown("#### 4️⃣ Institutional Memory Matches")
                            if memory_matches:
                                st.success(f"Found {len(memory_matches)} past solution(s)")
                                for match in memory_matches:
                                    with st.expander(f"🧠 {match.get('issue', 'Unknown Issue')} (Relevance: {match.get('relevance', 0):.0%})"):
                                        st.text(f"**Context:** {match.get('context', 'N/A')}")
                                        st.text(f"**Solution:** {match.get('solution', 'N/A')}")
                            else:
                                st.info("No institutional memory matches found")
                            
                            # Debugging Steps
                            debugging_steps = code_analysis.get('debugging_steps', [])
                            st.markdown("#### 5️⃣ Recommended Debugging Steps")
                            if debugging_steps:
                                for i, step in enumerate(debugging_steps, 1):
                                    st.markdown(f"{i}. {step}")
                            else:
                                st.info("No debugging steps generated")
                            
                            # Summary
                            summary = code_analysis.get('summary', '')
                            if summary:
                                st.markdown("#### 📊 Summary")
                                st.info(summary)
                            
                            # Jira Preview
                            jira_preview = analysis.get('jira_preview', {})
                            if jira_preview:
                                st.markdown("#### 🎫 Jira Ticket Preview")
                                with st.expander("View formatted Jira description (ADF format)"):
                                    st.json(jira_preview)
                            
                            if st.button("Close Analysis", key=f"close_analysis_bug_{msg['id']}"):
                                st.session_state[f"show_bug_analysis_{msg['id']}"] = False
                                st.rerun()
                        else:
                            st.info("This message is not classified as a bug. Use Exa research for other types.")
                            if st.button("Close", key=f"close_analysis_notbug_{msg['id']}"):
                                st.session_state[f"show_bug_analysis_{msg['id']}"] = False
                                st.rerun()
                    else:
                        st.error(f"Error: {response.text}")
                except Exception as e:
                    st.error(f"Failed to analyze: {e}")
            st.markdown("---")
        
        # Action Buttons (outside bug analysis block)
        act1, act2, act3 = st.columns(3)
        
        if act1.button("🎫 Create Jira Ticket", key=f"jira_{msg['id']}", use_container_width=True):
            st.session_state[f"show_jira_form_{msg['id']}"] = True
            
        if act2.button("📝 Create Notion Task", key=f"notion_{msg['id']}", use_container_width=True):
            with st.spinner("Creating Notion task..."):
                try:
                    response = requests.post(
                        f"{API_BASE}/api/slack/integrations/notion/create",
                        params={"message_id": msg['id']},
                        timeout=15
                    )
                    if response.status_code == 200:
                        result = response.json()
                        st.success(f"✅ Notion task created!")
                        if result.get('notion_url'):
                            st.markdown(f"[Open in Notion]({result['notion_url']})")
                    elif response.status_code == 400:
                        st.warning("Notion not configured. Set NOTION_API_KEY in .env")
                    else:
                        st.error(f"Failed: {response.text}")
                except Exception as e:
                    st.error(f"Connection failed: {e}")
            
        if act3.button("✅ Mark as Done", key=f"done_{msg['id']}", use_container_width=True):
            try:
                response = requests.post(
                    f"{API_BASE}/api/slack/messages/{msg['id']}/archive",
                    timeout=5
                )
                if response.status_code == 200:
                    st.toast("✅ Archived!")
                    if 'archived_messages' not in st.session_state:
                        st.session_state.archived_messages = set()
                    st.session_state.archived_messages.add(msg['id'])
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error(f"Failed to archive: {response.text}")
            except Exception as e:
                st.error(f"Failed to archive: {e}")
        
        # If Jira form was requested
        if st.session_state.get(f"show_jira_form_{msg['id']}", False):
            st.markdown("---")
            
            st.markdown("""
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 12px 16px; border-radius: 8px; margin-bottom: 16px;">
                <span style="color: white; font-weight: 700; font-size: 1.1rem;">🎫 Create Jira Ticket</span>
            </div>
            """, unsafe_allow_html=True)
            
            with st.form(key=f"jira_form_{msg['id']}"):
                summary = st.text_input("Summary", value=f"Slack: {msg.get('text')[:80]}...")
                issue_type = st.selectbox("Type", ["Task", "Story", "Bug", "Improvement"])
                st.info("💡 Exa research runs for comparisons, architecture decisions & best practices questions")
                submitted = st.form_submit_button("🚀 Create Ticket", use_container_width=True)
            
            if submitted:
                spinner_msg = "Creating ticket..." if issue_type == "Bug" else "Researching & creating ticket (~15-20s)..."
                with st.spinner(spinner_msg):
                    try:
                        response = requests.post(
                            f"{API_BASE}/api/slack/integrations/jira/create",
                            params={
                                "message_id": msg['id'],
                                "summary": summary,
                                "issue_type": issue_type
                            },
                            timeout=60
                        )
                        if response.status_code == 200:
                            result = response.json()
                            ticket_key = result.get('jira_key', 'Created')
                            st.success(f"✅ Ticket created! Key: {ticket_key}")
                            st.session_state[f"show_jira_form_{msg['id']}"] = False
                            import time
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error(f"Jira Error: {response.text}")
                    except Exception as e:
                        st.error(f"Connection failed: {e}")
            
            if st.button("Cancel", key=f"close_{msg['id']}"):
                st.session_state[f"show_jira_form_{msg['id']}"] = False
                st.rerun()

if __name__ == "__main__":
    main()
