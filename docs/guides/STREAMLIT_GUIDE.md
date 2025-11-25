# Streamlit Dashboard Guide

Visual dashboard for Slack Intelligence - see your prioritized messages in a beautiful web interface.

## Quick Start

### 1. Start the API Server
```bash
cd backend
python main.py
```

Server should be running on `http://localhost:8000`

### 2. Start the Dashboard
In a new terminal:
```bash
streamlit run streamlit_dashboard.py
```

Dashboard opens at `http://localhost:8501`

---

## Features

### 📊 Overview Metrics
- **Total Messages** - Messages in current view
- **🔴 Needs Response** - Critical messages (score ≥90)
- **🟡 High Priority** - Important messages (score 70-89)
- **Average Score** - Mean priority across all messages

### 📈 Priority Distribution Chart
Bar chart showing message breakdown by priority level:
- 🔴 Critical (90-100)
- 🟡 High (70-89)
- 🟢 Medium (50-69)
- ⚪ Low (0-49)

### 📬 Message List
Each message shows:
- Priority score with emoji indicator
- Sender name
- Channel name
- Timestamp (relative time)
- Full message text
- AI reasoning for prioritization
- Quick action buttons

### 🔍 Search
Real-time search across:
- Message text
- Sender names
- Channel names

### ⚙️ Filters (Sidebar)

**View:**
- 📬 All Messages
- 🔴 Needs Response (score ≥90)
- 🟡 High Priority (score 70-89)
- 🟢 FYI (score 50-69)
- ⚪ Low Priority (score <50)

**Time Window:**
- Slider from 1 to 168 hours
- Default: 24 hours

**Max Messages:**
- Limit results (10-100)
- Default: 50

**Auto-refresh:**
- Checkbox to enable
- Refreshes every 30 seconds

### Quick Actions

**Per Message:**
- ✅ **Mark Read** - Mark message as read
- ⏰ **Snooze** - Snooze for 1 hour
- 📝 **Create Task** - Create Notion task

*(Note: Action buttons currently show UI feedback. Backend integration coming soon.)*

---

## Usage Examples

### Morning Inbox Review
```bash
# Start with needs_response view
# Review critical messages first
# Use search to find specific topics
# Mark as read when done
```

**Workflow:**
1. Select "🔴 Needs Response" view
2. Time window: 24 hours
3. Review top 3 expanded messages
4. Take action on critical items
5. Mark as read

### Weekly Catch-up
```bash
# View all messages from past week
# Filter by high priority
# Search for specific projects
```

**Settings:**
- View: "🟡 High Priority"
- Time window: 168 hours (7 days)
- Limit: 100
- Search: "project name"

### Monitor Specific Channel
```bash
# Search for channel name
# See all messages in that channel
# Track priority trends
```

**Steps:**
1. View: "📬 All Messages"
2. Search: "channel-name"
3. Review distribution chart
4. Check average score

---

## Keyboard Shortcuts

- `Ctrl+R` - Refresh page
- `Ctrl+F` - Focus search box
- `Esc` - Close expanded message

---

## Troubleshooting

### "API Server not running"
**Solution:**
```bash
cd backend
python main.py
```

Verify server at: `http://localhost:8000/health`

### Dashboard won't start
**Solution:**
```bash
# Install streamlit
pip install streamlit

# Check installation
streamlit --version

# Run dashboard
streamlit run streamlit_dashboard.py
```

### Port already in use
**Solution:**
```bash
# Use different port
streamlit run streamlit_dashboard.py --server.port 8502
```

### No messages showing
**Possible causes:**
1. No messages in database - Run demo first
2. Time window too narrow - Increase hours
3. Filters too restrictive - Try "All Messages"

**Solution:**
```bash
# Run demo to populate data
python scripts/demo.py --channel C123ABC

# Refresh dashboard
```

---

## Configuration

### Change API Port
If your API runs on a different port:

1. Update `.env`:
```bash
API_PORT=8080
```

2. Restart dashboard

### Custom Styling
Edit CSS in `streamlit_dashboard.py` around line 25:
```python
st.markdown("""
<style>
    .priority-critical { 
        background-color: #your-color;
    }
</style>
""", unsafe_allow_html=True)
```

### Auto-refresh Interval
Change refresh rate (default 30s):

Line 260:
```python
time.sleep(30)  # Change to your desired seconds
```

---

## Advanced Features

### Running in Production

**Option 1: Local Network Access**
```bash
streamlit run streamlit_dashboard.py --server.address 0.0.0.0
```

Access from other devices: `http://your-ip:8501`

**Option 2: Cloud Deployment**
Deploy to Streamlit Cloud:
1. Push code to GitHub
2. Go to streamlit.io/cloud
3. Connect repository
4. Deploy

**Option 3: Docker**
```dockerfile
FROM python:3.9
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["streamlit", "run", "streamlit_dashboard.py"]
```

### Add Custom Widgets

Example - Add date picker:
```python
from datetime import date

st.sidebar.date_input(
    "Date range",
    value=(date.today() - timedelta(days=7), date.today())
)
```

### Export Data

Add export button:
```python
if st.button("📥 Export CSV"):
    df = pd.DataFrame(messages)
    csv = df.to_csv(index=False)
    st.download_button(
        "Download CSV",
        csv,
        "messages.csv",
        "text/csv"
    )
```

---

## Performance Tips

1. **Limit message count** - Use 50 or fewer for best performance
2. **Narrow time window** - Shorter ranges load faster
3. **Use specific views** - Filter to reduce data
4. **Disable auto-refresh** - Manual refresh for large datasets

---

## Screenshots

### Main Dashboard
- Overview metrics at top
- Priority distribution chart
- Expandable message list
- Search and filters

### Message Detail
- Full message text
- AI reasoning
- Action buttons
- Metadata (time, channel, sender)

### Sidebar
- View selector
- Time window slider
- Max messages slider
- Auto-refresh toggle
- Quick stats

---

## Integration with Existing Tools

### With Notion
- "Create Task" button syncs to Notion
- Uses existing Notion integration
- Respects NOTION_MIN_PRIORITY_SCORE

### With Demo
```bash
# Run demo to generate test data
python scripts/demo.py --channel C123ABC

# View in dashboard
streamlit run streamlit_dashboard.py
```

### With Production Monitor
Run both simultaneously:
```bash
# Terminal 1: API Server
cd backend && python main.py

# Terminal 2: Dashboard
streamlit run streamlit_dashboard.py

# Terminal 3: Monitor
python scripts/production_monitor.py
```

---

## Future Enhancements

Planned features:
- [ ] Mark as read (persist to database)
- [ ] Snooze functionality
- [ ] Direct Notion task creation from dashboard
- [ ] Message threading view
- [ ] User preferences editor
- [ ] Priority threshold configuration
- [ ] Dark mode toggle
- [ ] Export to CSV/JSON
- [ ] Message tagging
- [ ] Advanced filtering (regex, multiple channels)

---

## Getting Help

**Issues:**
- API not responding → Check `backend/main.py` is running
- No messages → Run `python scripts/demo.py --channel C123ABC`
- Port conflict → Use `--server.port 8502`

**Documentation:**
- Streamlit docs: https://docs.streamlit.io
- API endpoints: `http://localhost:8000/docs`
- Project README: `README.md`

---

## Quick Reference

| Command | Purpose |
|---------|---------|
| `streamlit run streamlit_dashboard.py` | Start dashboard |
| `streamlit run ... --server.port 8502` | Use different port |
| `streamlit run ... --server.address 0.0.0.0` | Allow network access |
| `Ctrl+C` | Stop dashboard |
| `Ctrl+R` | Refresh page |

**Default URLs:**
- Dashboard: `http://localhost:8501`
- API: `http://localhost:8000`
- API Docs: `http://localhost:8000/docs`

