import streamlit as st
from google import genai
from datetime import date, datetime
import json
import os
if "pwa_loaded" not in st.session_state:
    st.session_state.pwa_loaded = True

    st.markdown("""
    <script>
    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.register('/static/sw.js');
    }
    </script>
    """, unsafe_allow_html=True)
st.title("AI Study Planner with Exam Prediction - Agentic Edition")
st.caption("Tutor Agent | Memory Agent | Evaluator Agent | Adaptive Engine")

# ================= Page Config =================
st.set_page_config(page_title="AI Study Planner - Agentic Edition", page_icon="", layout="wide")
st.title("AI Study Planner with Exam Prediction - Agentic Edition")
st.caption("Tutor Agent | Memory Agent | Evaluator Agent | Adaptive Engine - Powered by Google Gemini")

MEMORY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "memory.json")

DEFAULT_MEMORY = {
    "profile": {},
    "evaluations": [],
    "weak_topics": [],
    "plans_generated": 0,
}

# ================= Helpers =================
def load_env_key():
    try:
        return st.secrets.get("GEMINI_API_KEY", "")
    except Exception:
        return ""

def clean_key(raw):
    return raw.strip().strip('"').strip("'").strip()

def friendly_error(e):
    msg = str(e)
    if "401" in msg or "UNAUTHENTICATED" in msg or "API_KEY_INVALID" in msg or "API key not valid" in msg:
        return ("Your API key was rejected. Create a fresh key at "
                "https://aistudio.google.com/apikey and paste it in the sidebar.")
    if "429" in msg or "quota" in msg.lower() or "RESOURCE_EXHAUSTED" in msg:
        return "Free quota exceeded. Wait a minute and try again."
    if "404" in msg or "NOT_FOUND" in msg:
        return "Model unavailable. Pick a different model in the sidebar."
    if "Deadline" in msg or "timeout" in msg.lower():
        return "Network timeout. Check your internet."
    return f"Unexpected error: {e}"

@st.cache_data(ttl=300)
def fetch_available_models(api_key):
    try:
        c = genai.Client(api_key=api_key)
        ids = [m.name.replace("models/", "") for m in c.models.list()]
        models = sorted([m for m in ids if "gemini" in m.lower()])
        return models if models else ["gemini-3.1-pro-preview"]
    except Exception:
        return ["gemini-3.1-pro-preview"]

# ================= Memory Agent =================
def load_memory():
    """Memory Agent: reads the student's long-term memory from disk."""
    try:
        with open(MEMORY_FILE) as f:
            return json.load(f)
    except Exception:
        return json.loads(json.dumps(DEFAULT_MEMORY))

def save_memory(mem):
    """Memory Agent: writes updated memory back to disk."""
    with open(MEMORY_FILE, "w") as f:
        json.dump(mem, f, indent=2)

def remember_evaluation(mem, subject, topic, score_pct, weak):
    """Memory Agent: stores an evaluation result and updates global weak topics."""
    mem["evaluations"].append({
        "date": str(date.today()),
        "subject": subject,
        "topic": topic,
        "score_pct": score_pct,
        "weak_topics": weak,
    })
    for w in weak:
        if w not in mem["weak_topics"]:
            mem["weak_topics"].append(w)
    save_memory(mem)

def avg_score(mem):
    evs = mem.get("evaluations", [])
    return round(sum(e["score_pct"] for e in evs) / len(evs)) if evs else None

# ================= Tutor Agent =================
def tutor_reply(client, model, subject, topic, messages):
    history = "\n".join([f"{m['role']}: {m['content']}" for m in messages])
    prompt = f"""You are TutorAgent, a patient, friendly and expert AI tutor.
Subject: {subject}
Topic the student is learning: {topic}

Conversation so far:
{history}

Rules:
1. Explain concepts simply, step by step, with real-world examples.
2. Keep answers focused and under 250 words.
3. End every reply with one short check-in question to test understanding.
Now respond as TutorAgent."""
    return client.models.generate_content(model=model, contents=prompt).text

# ================= Evaluator Agent =================
def generate_quiz(client, model, subject, topic, n):
    prompt = f"""You are the Evaluator Agent. Create {n} multiple-choice questions on the topic "{topic}" (subject: {subject}).
Respond with ONLY a raw JSON array (no markdown fences, no explanation):
[{{"question": "question text", "options": ["A", "B", "C", "D"], "correct": 0, "tag": "subtopic"}}]
Rules: "correct" is the index (0-3) of the correct option. "tag" is the specific subtopic tested."""
    text = client.models.generate_content(model=model, contents=prompt).text.strip()
    text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    return json.loads(text)

def evaluate_quiz(client, model, subject, topic, quiz, answers):
    """Hybrid evaluation: deterministic scoring + AI feedback and weak-area detection."""
    score = sum(1 for i, q in enumerate(quiz) if answers[i] == q["correct"])
    pct = round(100 * score / len(quiz))
    lines = []
    for i, q in enumerate(quiz):
        ok = answers[i] == q["correct"]
        mark = "Correct" if ok else "Wrong (correct answer: " + q["options"][q["correct"]] + ")"
        lines.append(f"Q{i+1} [{q.get('tag', 'general')}]: student picked {q['options'][answers[i]]} -> {mark}")
    review = "\n".join(lines)
    prompt = f"""You are the Evaluator Agent. A student scored {pct}% on "{topic}" ({subject}).
Per-question review:
{review}

Respond in EXACTLY this format:
FEEDBACK: 2-3 sentences of constructive feedback.
WEAK: a JSON array of the subtopics the student should revise, e.g. ["Pointers", "Recursion"] (empty array if none)."""
    text = client.models.generate_content(model=model, contents=prompt).text.strip()
    feedback, weak = "Good effort!", []
    for line in text.splitlines():
        if line.startswith("FEEDBACK:"):
            feedback = line.replace("FEEDBACK:", "").strip()
        if line.startswith("WEAK:"):
            raw = line.replace("WEAK:", "").strip()
            try:
                weak = json.loads(raw)
            except Exception:
                weak = []
    return pct, feedback, weak

# ================= Adaptive Engine =================
def adapt_plan(client, model, mem, subject, topics, exam_date, hours, level, days_left):
    """Adaptive Engine: rewrites the plan giving extra weight to weak areas from memory."""
    weak = ", ".join(mem.get("weak_topics", [])) or "no weak areas recorded yet"
    evs = mem.get("evaluations", [])
    history_lines = "\n".join(
        f"- {e['date']} | {e['topic']} | score {e['score_pct']}% | weak: {', '.join(e['weak_topics']) or 'none'}"
        for e in evs[-10:]
    ) or "- no evaluations yet"
    prompt = f"""You are the Adaptive Engine of an AI study planner.
Student profile:
- Subject: {subject}
- Full syllabus: {topics}
- Exam date: {exam_date} ({days_left} days left)
- Study hours per day: {hours}
- Preparation level: {level}

Memory Agent data:
- Known weak areas: {weak}
- Evaluation history:
{history_lines}

Task: create a REVISED day-by-day study plan that ADAPTS to the student's measured performance:
1. Give weak areas from memory significantly more time and repetition.
2. Reduce time on topics the student already scores well in.
3. Keep the same daily format:
### Day N - <theme>
- Study: <topics>
- Practice: <tasks>
- Self-test: <questions/task>
- Time split: Xh study / Yh practice
4. Start with a short "Why this plan changed" summary (2-3 lines).
5. End with one motivational tip.
Be specific and practical."""
    return client.models.generate_content(model=model, contents=prompt).text

# ================= Sidebar =================
st.sidebar.header("Settings")
env_key = clean_key(load_env_key())
default_val = "" if env_key in ("", "PASTE_YOUR_API_KEY_HERE") else env_key
raw_key = st.sidebar.text_input("Gemini API Key", value=default_val, type="password",
                                help="Get a free key at https://aistudio.google.com/apikey")
api_key = clean_key(raw_key)

mem = load_memory()

if api_key:
    st.sidebar.caption(f"Loaded key: {api_key[:4]}...{api_key[-4:]} ({len(api_key)} chars)")
    if st.sidebar.button("Test API Key", use_container_width=True):
        with st.sidebar.spinner("Testing..."):
            try:
                t = genai.Client(api_key=api_key)
                st.sidebar.success(f"Key works! {len(list(t.models.list()))} models available.")
            except Exception as e:
                st.sidebar.error(friendly_error(e))
    available = fetch_available_models(api_key)
    default_idx = next((i for i, m in enumerate(available) if "flash" in m), 0)
    model_name = st.sidebar.selectbox("Model", available, index=default_idx)
else:
    model_name = None

st.sidebar.markdown("---")
st.sidebar.subheader("Memory Agent")
st.sidebar.caption(f"Quizzes taken: {len(mem['evaluations'])}")
a = avg_score(mem)
st.sidebar.caption(f"Average score: {a if a is not None else 'N/A'}%")
st.sidebar.caption("Weak areas: " + (", ".join(mem["weak_topics"]) if mem["weak_topics"] else "none yet"))
if st.sidebar.button("Clear Memory", use_container_width=True):
    if os.path.exists(MEMORY_FILE):
        os.remove(MEMORY_FILE)
    st.session_state.clear()
    st.sidebar.success("Memory cleared.")
    st.rerun()

if not api_key:
    st.warning("Please enter your Gemini API key in the sidebar to continue.")
    st.stop()

client = genai.Client(api_key=api_key)

# ================= Main Input Form =================
with st.form("study_form"):
    col1, col2 = st.columns(2)
    with col1:
        subject = st.text_input("Subject", placeholder="e.g. Data Structures")
        exam_date = st.date_input("Exam Date", value=date.today())
        hours_per_day = st.slider("Study hours available per day", 1, 12, 3)
    with col2:
        level = st.selectbox("Current preparation level",
                             ["Just started", "Halfway done", "Almost done", "Only revision left"])
        style = st.selectbox("Learning style",
                             ["Balanced (mix of everything)", "Theory first", "Practice problems", "Visual / diagrams"])
        difficulty = st.selectbox("Exam difficulty", ["Easy", "Moderate", "Hard", "Very Hard"])
    topics = st.text_area("Syllabus / Topics",
                          placeholder="e.g. Arrays, Linked Lists, Trees, Graphs...",
                          height=100)
    submitted = st.form_submit_button("Save Profile", use_container_width=True)

if subject and topics:
    mem["profile"] = {"subject": subject, "topics": topics, "exam_date": str(exam_date),
                      "hours": hours_per_day, "level": level}
    save_memory(mem)

days_left = (exam_date - date.today()).days

tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["Study Plan", "Exam Prediction", "Tutor Agent", "Quiz + Evaluator", "Adaptive Engine"])

# ================= Tab 1: Study Plan =================
with tab1:
    if st.button("Generate My Study Plan", use_container_width=True, key="plan_btn"):
        if days_left < 1:
            st.error("Exam date must be in the future!")
        elif not (subject and topics):
            st.error("Fill in Subject and Syllabus above and click Save Profile first.")
        else:
            prompt = f"""You are an expert academic study planner.
Create a detailed DAY-BY-DAY study plan:
- Subject: {subject}
- Syllabus/Topics: {topics}
- Exam date: {exam_date} ({days_left} days left)
- Daily hours: {hours_per_day}
- Level: {level} | Style: {style} | Difficulty: {difficulty}
Format each day as:
### Day N - <theme>
- Study: <topics>
- Practice: <tasks>
- Self-test: <questions/task>
- Time split: Xh study / Yh practice
End with a 2-3 day revision + mock test block and one motivational tip."""
            with st.spinner("Building your plan..."):
                try:
                    plan = client.models.generate_content(model=model_name, contents=prompt).text
                    mem["plans_generated"] += 1
                    save_memory(mem)
                    st.success("Your study plan is ready!")
                    st.markdown(plan)
                    st.download_button("Download Plan", plan,
                                       file_name=f"study_plan_{subject.replace(' ', '_')}.md",
                                       mime="text/markdown")
                except Exception as e:
                    st.error(friendly_error(e))

# ================= Tab 2: Exam Prediction =================
with tab2:
    if not (subject and topics):
        st.info("Fill in Subject and Syllabus above and click Save Profile first.")
    else:
        past_papers = st.text_area("Optional: paste past paper questions",
                                   placeholder="Paste previous year questions here...", height=80)
        if st.button("Predict My Exam", use_container_width=True, key="pred_btn"):
            prompt = f"""You are an exam prediction expert.
Subject: {subject} | Syllabus: {topics} | Level: {level} | Difficulty: {difficulty} | Days left: {days_left}
{f"Past papers: {past_papers}" if past_papers.strip() else ""}
Known weak areas from memory: {', '.join(mem['weak_topics']) or 'none'}
Respond in EXACTLY this format:
## Most Likely Exam Topics
Table: | Rank | Topic | Probability (%) | Why likely |
## 5 Predicted Questions
## Predicted Score Range
- If preparation continues: X-Y%
- If weak areas are fixed: A-B%
## Weak-Area Alert
## Question Pattern Guess"""
            with st.spinner("Predicting your exam..."):
                try:
                    prediction = client.models.generate_content(model=model_name, contents=prompt).text
                    st.success("Prediction complete!")
                    st.markdown(prediction)
                    st.download_button("Download Prediction", prediction,
                                       file_name=f"prediction_{subject.replace(' ', '_')}.md",
                                       mime="text/markdown")
                except Exception as e:
                    st.error(friendly_error(e))

# ================= Tab 3: Tutor Agent =================
with tab3:
    subj_t = subject or mem["profile"].get("subject", "")
    topic_t = st.text_input("Topic you want to learn", placeholder="e.g. Recursion in Trees",
                            key="tutor_topic")
    if "tutor_msgs" not in st.session_state:
        st.session_state.tutor_msgs = []
    for m in st.session_state.tutor_msgs:
        with st.chat_message(m["role"]):
            st.write(m["content"])
    user_q = st.chat_input("Ask your tutor anything about this topic...")
    if user_q:
        if not topic_t:
            st.warning("Please type the topic first.")
        else:
            st.session_state.tutor_msgs.append({"role": "user", "content": user_q})
            with st.spinner("Tutor Agent is thinking..."):
                try:
                    reply = tutor_reply(client, model_name, subj_t, topic_t, st.session_state.tutor_msgs)
                    st.session_state.tutor_msgs.append({"role": "assistant", "content": reply})
                except Exception as e:
                    st.error(friendly_error(e))
            st.rerun()
    if st.button("Reset Tutor Chat"):
        st.session_state.tutor_msgs = []
        st.rerun()

# ================= Tab 4: Quiz + Evaluator Agent =================
with tab4:
    subj_q = subject or mem["profile"].get("subject", "")
    topic_q = st.text_input("Topic for quiz", placeholder="e.g. Arrays", key="quiz_topic")
    n_q = st.slider("Number of questions", 3, 10, 5)
    if st.button("Generate Quiz"):
        if not topic_q:
            st.warning("Enter a topic first.")
        else:
            with st.spinner("Evaluator Agent is creating questions..."):
                try:
                    st.session_state.quiz = generate_quiz(client, model_name, subj_q, topic_q, n_q)
                    st.session_state.pop("quiz_result", None)
                except Exception as e:
                    st.error(friendly_error(e))
    if "quiz" in st.session_state:
        quiz = st.session_state.quiz
        st.markdown(f"**Quiz on: {topic_q}**")
        answers = []
        for i, q in enumerate(quiz):
            st.write(f"**Q{i+1}.** {q['question']}")
            answers.append(st.radio("Choose an answer:", q["options"], key=f"quiz_q{i}", index=None))
        if st.button("Submit Answers", key="submit_quiz"):
            if any(a is None for a in answers):
                st.warning("Answer all questions before submitting.")
            else:
                with st.spinner("Evaluator Agent is grading..."):
                    try:
                        pct, feedback, weak = evaluate_quiz(client, model_name, subj_q, topic_q, quiz, answers)
                        remember_evaluation(mem, subj_q, topic_q, pct, weak)
                        st.session_state.quiz_result = {"pct": pct, "feedback": feedback, "weak": weak}
                    except Exception as e:
                        st.error(friendly_error(e))
    if "quiz_result" in st.session_state:
        r = st.session_state.quiz_result
        st.success(f"Score: {r['pct']}%")
        st.write("**Feedback:** " + r["feedback"])
        st.write("**Weak areas detected:** " + (", ".join(r["weak"]) if r["weak"] else "none, great job!"))
        st.info("The Adaptive Engine can now use this result to fix your plan. Check the last tab.")
        if st.button("Take New Quiz"):
            st.session_state.pop("quiz", None)
            st.session_state.pop("quiz_result", None)
            st.rerun()

# ================= Tab 5: Adaptive Engine =================
with tab5:
    st.subheader("Adaptive Engine - Plan That Reacts to Your Performance")
    prof = mem["profile"]
    use_saved = st.checkbox("Use saved profile", value=bool(prof))
    a_subj = subject or prof.get("subject", "")
    a_topics = topics or prof.get("topics", "")
    a_date = exam_date or datetime.strptime(prof.get("exam_date", str(date.today())), "%Y-%m-%d").date()
    a_hours = hours_per_day or prof.get("hours", 3)
    a_level = level or prof.get("level", "Just started")
    a_days = (a_date - date.today()).days
    st.caption(f"Days left: {a_days} | Weak areas in memory: "
               + (", ".join(mem["weak_topics"]) if mem["weak_topics"] else "none yet"))
    if st.button("Adapt My Study Plan", use_container_width=True):
        if not (a_subj and a_topics):
            st.error("Fill in Subject and Syllabus first (or save a profile).")
        elif a_days < 1:
            st.error("Exam date must be in the future!")
        else:
            with st.spinner("Adaptive Engine is rewriting your plan..."):
                try:
                    new_plan = adapt_plan(client, model_name, mem, a_subj, a_topics,
                                          a_date, a_hours, a_level, a_days)
                    st.success("Adaptive plan generated! Weak areas now get priority.")
                    st.markdown(new_plan)
                    st.download_button("Download Adaptive Plan", new_plan,
                                       file_name=f"adaptive_plan_{a_subj.replace(' ', '_')}.md",
                                       mime="text/markdown")
                except Exception as e:
                    st.error(friendly_error(e))

st.markdown("---")
st.caption("Agentic AI Study Planner | Tutor + Memory + Evaluator + Adaptive Engine | Streamlit + Gemini")
