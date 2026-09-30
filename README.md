# 🤖 AI Study Planner with Exam Prediction (Agentic AI)

An intelligent AI-powered study planner that creates personalized day-by-day study plans and predicts the most likely exam questions using **Google Gemini AI** and an **Agent-based architecture**.

---

## 🚀 Features

- 📅 **Smart Study Plan Generator**
  - Generates a structured day-wise study plan based on:
    - Exam date
    - Study hours
    - Preparation level
    - Learning style

- 🔮 **Exam Prediction Engine**
  - Predicts:
    - Most probable topics
    - 5 expected exam questions
    - Probability scores
    - Expected marks range
    - Weak-area alerts

- 📊 **Past Paper Analysis**
  - Improves prediction accuracy using previous year questions

- 🧠 **Agent-Based Intelligence**
  - Uses multiple AI agents for smarter decision-making

- 🔑 **API Key Tester**
  - Validate Gemini API key before usage

- 📥 **Download Results**
  - Export study plans and predictions as markdown files

---

## 🧠 Agent Architecture

This project uses an **Agentic AI system** with multiple intelligent modules:

### 👨‍🏫 Tutor Agent
- Explains topics in a simple way
- Breaks down complex syllabus into easy concepts
- Suggests study techniques and examples

### 🧠 Memory Agent
- Stores user preferences and past study behavior
- Remembers weak and strong topics
- Helps personalize future plans

### 🧪 Evaluator Agent
- Analyzes user progress and performance
- Identifies weak areas
- Suggests improvements and revision strategies

### ⚙️ Adaptive Engine
- Dynamically updates study plans based on:
  - User progress
  - Performance feedback
  - Time constraints
- Makes the system **self-improving**

---

## 🛠️ Tech Stack

- **Language:** Python  
- **Framework:** Streamlit  
- **AI API:** Google Gemini (google-genai SDK)  

---

## ⚙️ How It Works

1. User enters:
   - Subject, syllabus, exam date
   - Study hours, preparation level, learning style

2. System processes input using:
   - Tutor Agent (guidance)
   - Memory Agent (history)
   - Evaluator Agent (analysis)

3. Adaptive Engine refines the plan

4. Gemini AI generates:
   - Study plan / Exam predictions

5. Results displayed + downloadable

---

## 📁 Project Structure
ai-study-planner/
│
├── app.py # Main Streamlit application
├── requirements.txt # Dependencies
├── README.md # Documentation
│
├── agents/ # AI Agents
│ ├── tutor_agent.py # Teaching & explanation logic
│ ├── memory_agent.py # User memory & tracking
│ ├── evaluator_agent.py # Performance evaluation
│
├── engine/
│ ├── adaptive_engine.py # Dynamic plan adjustment
│
├── utils/
│ ├── prompt_builder.py # Gemini prompt creation
│ ├── api_handler.py # API communication
│
└── .streamlit/
└── secrets.toml # API Key storage

---


---

## 🚀 Quick Start

### 1️⃣ Get Gemini API Key  
👉 https://aistudio.google.com/apikey  

### 2️⃣ Add API Key  
Paste in `.streamlit/secrets.toml` or inside the app UI

### 3️⃣ Install Dependencies
```bash
pip install -r requirements.txt

---
streamlit run app.py

---

Open browser → http://localhost:8501
Enter API Key
Fill study details
Click:
Generate Study Plan
Predict Exam Questions
Download results
---

Author

Kenny (Kenith Paul Ganaraj)

Game Developer | Python Programmer | AI Enthusiast

GitHub: https://github.com/kenny-oops

---


---

🔥 This version is **perfect for your final-year MCA project + GitHub + placements**.

If you want next step, I can:
- :contentReference[oaicite:0]{index=0}  
- OR :contentReference[oaicite:1]{index=1}  
- OR :contentReference[oaicite:2]{index=2}
