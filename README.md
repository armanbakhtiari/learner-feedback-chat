# AI-Powered Learner Feedback Chat System

An interactive chatbot that provides personalized, constructive feedback on "Learning by Concordance" medical training assessments. Built with LangGraph and Claude Sonnet 4.5.

## 🚀 Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Create .env file with your API keys
ANTHROPIC_API_KEY=your_key_here
LANGCHAIN_API_KEY=your_key_here
TAVILY_API_KEY=your_key_here  # Optional: for web search

# 3. Start the application
python3 run.py
```

The application will automatically:
- Start the backend server on http://localhost:8000
- Start the frontend server on http://localhost:3000
- Open your browser to the application

## 🏗️ Architecture

### Supervisor-Based Agent System

The chat agent uses a **Supervisor Agent** that intelligently routes user queries:

```
User Query → Supervisor (analyzes & decides) → Tools (if needed) → Chat Agent (responds) → User
```

**Supervisor Decision Logic:**
- Conservative approach: Only calls tools when explicitly needed
- Can invoke multiple tools in one turn
- Passes tool results to chat agent for final response

**Available Tools:**
1. `generate_visualization` - Creates charts/tables using matplotlib
2. `search_web` - Tavily web search for current medical information
3. `get_training_content` - Retrieves detailed training module content

### LangGraph Flow

```
START
  ↓
supervisor (decide which tools to call)
  ↓
generate_response (generate French response using tool results)
  ↓
END
```

## 📁 Project Structure

```
Implementation/
├── backend/
│   ├── app.py                    # FastAPI server & endpoints
│   ├── chat_agent.py             # LangGraph chat agent
│   ├── supervisor_agent.py       # Supervisor with tool binding
│   ├── supervisor_tools.py       # Tool definitions (@tool decorated)
│   ├── code_tool.py              # Visualization code generator
│   ├── web_search_tool.py        # Tavily search integration
│   └── evaluator.py              # Training evaluation logic
├── frontend/
│   ├── index.html                # Landing page
│   ├── chat.html                 # Chat interface
│   ├── styles.css                # Styling
│   └── app.js                    # Shared utilities
├── trainings_2_experts.py        # Training modules & expert data
├── requirements.txt              # Python dependencies
├── run.py                        # Application launcher
└── .env                          # API keys (not in repo)
```

## 💡 Features

### ✅ Implemented
- **Intelligent Routing**: Supervisor decides when to call visualization, web search, or retrieve training content
- **Interactive Feedback**: Chat in French about training performance
- **Data Visualization**: Automatic chart/table generation with matplotlib
- **Web Search**: Optional toggle for current medical guidelines/research
- **LangSmith Tracing**: Full observability of agent decisions and tool calls
- **Non-judgmental Tone**: Constructive, supportive feedback
- **Bilingual Support**: Understands English queries, responds in French

### 🎯 Use Cases
- "Create a table showing my performance overview"
- "In which scenarios did I struggle?"
- "What are the latest migraine treatment guidelines?" (with web search enabled)
- "Show me expert responses for scenario 2 in module 1"

## 🔧 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Health check |
| GET | `/trainings` | List training modules |
| POST | `/evaluate` | Run evaluation (creates session) |
| POST | `/chat` | Chat with agent |
| POST | `/chat/reset/{session_id}` | Reset conversation |

## 📊 LangSmith Tracing

View complete traces at https://smith.langchain.com/

**What you'll see:**
- Supervisor reasoning and tool selection
- Tool invocation inputs/outputs
- Chat agent response generation
- Token usage and latency
- Full conversation context

**Project name:** `Feedback_Chat_Agent`

## 🛠️ Technology Stack

| Component | Technology |
|-----------|------------|
| Backend Framework | FastAPI |
| Agent Framework | LangGraph + LangChain |
| LLM | Claude Sonnet 4.5 (Anthropic) |
| Visualization | Matplotlib + Pandas |
| Web Search | Tavily API |
| Observability | LangSmith |
| Frontend | Vanilla HTML/CSS/JS |

## 📝 Configuration

### Environment Variables (.env)

```bash
# Required
ANTHROPIC_API_KEY=sk-ant-...

# Optional but recommended
LANGCHAIN_API_KEY=lsv2_pt_...  # For LangSmith tracing
TAVILY_API_KEY=tvly-...        # For web search feature
```

### Creating a .env file

```bash
# Copy the template
cat > .env << EOF
ANTHROPIC_API_KEY=your_anthropic_key_here
LANGCHAIN_API_KEY=your_langchain_key_here
TAVILY_API_KEY=your_tavily_key_here
EOF
```

## 🐛 Troubleshooting

**Port already in use:**
```bash
# Kill existing processes
lsof -ti:8000 | xargs kill -9  # Backend
lsof -ti:3000 | xargs kill -9  # Frontend
```

**Missing dependencies:**
```bash
pip install -r requirements.txt
```

**Backend not starting:**
- Check that .env file exists with ANTHROPIC_API_KEY
- Verify Python 3.8+ is installed

**Visualizations showing code instead of images:**
- Already fixed! If you see this, restart the server
- Make sure matplotlib is installed: `pip install matplotlib`

**No LangSmith traces:**
- Add LANGCHAIN_API_KEY to .env
- Get key from https://smith.langchain.com/ → Settings → API Keys

## 🚦 Development

### Running Tests
```bash
# Test backend API
curl http://localhost:8000/

# Test frontend
open http://localhost:3000/test.html
```

### Debugging
- Backend logs appear in the terminal running `run.py`
- Frontend logs in browser console (F12)
- Full traces in LangSmith dashboard

## 📄 License

[Your License Here]

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📧 Contact

[Your Contact Information]

---


