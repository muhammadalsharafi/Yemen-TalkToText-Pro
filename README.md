# TalkToText Pro - AI Meeting Summarizer

This project, **TalkToText Pro**, is an AI-powered pipeline designed to process meeting recordings (audio or video), transcribe them, and generate a structured, actionable summary compliant with the SRS document.

---

## Core Features

- **End-to-End Automated Pipeline**
  Seamless workflow from media upload (file or URL) to a structured, final summary, managed via an intuitive web interface.

- **State-of-the-Art Accuracy & Speed**
  Optimal balance of performance by leveraging a multi-model AI stack, ensuring both world-class accuracy and efficient processing.

- **Intelligent Content Pre-Screening**
  Lightweight AI model (`gpt-5-nano`) analyzes metadata and audio snippets, automatically filtering irrelevant content before full processing.

- **Advanced Audio Engineering**
  Uses **FFmpeg** for robust audio processing, including format standardization, quality enhancement filters, and silence removal.

- **Precision Transcription**
  Employs OpenAI's **Whisper-1** model for highly accurate speech-to-text conversion across accents and domains.

- **Multi-Language Support**
  Detects the source language and translates to English using **gpt-5-mini** when needed.

- **SRS-Compliant Summarization**
  Uses **gpt-5** with a carefully engineered prompt to produce structured summaries:
  - Abstract
  - Key Points
  - Action Items
  - Decisions
  - Sentiment Analysis

- **Robust Backend Architecture**
  Built on **OOP principles** for modularity, scalability, and maintainability.

- **Persistent Job & User Management**
  Integrates with **MongoDB** for secure user and job tracking.

---

## Technical Architecture & Design

### OOP Structure
- **Encapsulation**: Each functionality is within its own class (`AudioProcessor`, `TextProcessor`, `AIServices`, `DatabaseManager`).
- **Orchestration**: `MainPipeline` manages interaction between components.
- **Custom Exceptions**: Dedicated exceptions (`FileSystemError`, `FFmpegError`, `ApiServiceError`) for precise error handling.

### Multi-Model AI Strategy
- `whisper-1`: For transcription
- `gpt-5-nano`: For pre-screening/classification
- `gpt-5-mini`: For translation
- `gpt-5`: For final structured summarization

---

## Prerequisites

### 1. Python
Install **Python 3.8+** from [python.org](https://www.python.org/downloads/). Check version:
```bash
python --version
```

### 2. FFmpeg

**System-Wide Installation**

- **Windows**: Download from [FFmpeg official](https://ffmpeg.org/download.html), extract, and add to PATH.
- **macOS**: `brew install ffmpeg`
- **Linux**: `sudo apt update && sudo apt install ffmpeg`

**Verify:**
```bash
ffmpeg -version
```

**Portable Installation (Bundled)**

Download from [gyan.dev](https://www.gyan.dev/ffmpeg/builds/). Extract and copy `ffmpeg.exe` and `ffprobe.exe` into `bin/` inside the project folder.

---

## Installation & Setup

### Step 1: Project Files
Place project files in a folder (e.g., `AI_Project`).

### Step 2: Virtual Environment
```bash
cd path/to/AI_Project
python -m venv venv
```

**Activate:**
- Windows: `venv\Scripts\activate`
- Linux/macOS: `source venv/bin/activate`

### Step 3: Install Dependencies
```bash
pip install -r "requirements.txt"
```

### Step 4: OpenAI API Key
In `.env` file:
```
OPENAI_API_KEY=sk-your-secret-key
```

### Step 5: MongoDB Connection
In `.env` file:
```
MONGO_CONNECTION_STRING="mongodb+srv://username:password@cluster.mongodb.net/mydatabase"
```

---

## How to Run

### Option 1: Web Application
```bash
python app.py
```
Open in browser: `http://127.0.0.1:5000`

### Option 2: Command-Line Script
Edit `main.py`:
```python
input_source = r"C:\path\to\your\meeting.mp4"
```

(Optional) edit `config.py`:
```python
SELECTED_AUDIO_QUALITY = "medium"
```

Run:
```bash
python "main.py"
```

Results are stored in MongoDB.

---

## Sources and References

### Command Engineering
- [Universal Command and Control Language Early System Engineering – RAND](https://www.rand.org/pubs/research_reports/RRA744-2.html)
- [Command and Control Systems Engineering: Integrating Rapid Prototyping and Cognitive Engineering – JHUAPL](https://secwww.jhuapl.edu/techdigest/content/techdigest/pdf/V31-N01/31-01-Cooley.pdf)
- [Engineering domains: executable commands as an example – ResearchGate](https://www.researchgate.net/publication/3756128_Engineering_domains_executable_commands_as_an_example)

### Context Engineering
- [A Survey of Context Engineering for Large Language Models – arXiv](https://arxiv.org/abs/2507.13334)
- [Context Engineering: Enhancing LLM Performance Through Comprehensive Contextual Management – ResearchGate](https://www.researchgate.net/publication/393511218_Context_Engineering_Enhancing_Large_Language_Model_Performance_Through_Comprehensive_Contextual_Management)
- [From Prompt Engineering to Context Engineering in Healthcare AI – SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=5365971)
- [Towards an Understanding of Context Utilization in Code Intelligence – arXiv](https://arxiv.org/abs/2504.08734)

### Python Language Courses
- [Google's Python Class](https://developers.google.com/edu/python)
- [Python Full Course 2024 (YouTube)](https://www.youtube.com/watch?v=ix9cRaBkVe0)
- [AI Python for Beginners – DeepLearning.AI](https://www.deeplearning.ai/short-courses/ai-python-for-beginners/)
- [Top Free Python Courses & Tutorials – Udemy](https://www.udemy.com/topic/python/free/)

### Advanced OOP in Python
- [Object-Oriented Programming in Python – RealPython](https://realpython.com/python3-object-oriented-programming/)
- [Object-Oriented Python: Inheritance and Encapsulation – Coursera](https://www.coursera.org/learn/object-oriented-python)
- [Advanced OOP Lesson – Imperial College London](https://python.pages.doc.ic.ac.uk/2021/lessons/oop)
- [Advanced Python OOP – LinkedIn Learning](https://www.linkedin.com/learning/advanced-python-object-oriented-programming)

### Flask Courses
- [Python Flask Tutorial – Full Course (YouTube)](https://www.youtube.com/watch?v=2YOBmELm_v0)
- [Full Flask Course For Python – From Basics To Deployment (YouTube)](https://www.youtube.com/watch?v=oQ5UfJqW5Jo)
- [Developing Web Applications with Python and Flask – TestDriven.io](https://testdriven.io/courses/learn-flask/)
- [Flask Tutorial – GeeksforGeeks](https://www.geeksforgeeks.org/python/flask-tutorial/)
- [Flask Courses – Coursera](https://www.coursera.org/courses?query=flask)

### OpenAI API with Python
- [Working with the OpenAI API – DataCamp](https://www.datacamp.com/courses/working-with-the-openai-api)
- [OpenAI API for Beginners: Create AI Assistants with ChatGPT – Coursera](https://www.coursera.org/projects/openai-api-for-beginners-create-ai-assistants-with-chatgpt)
- [OpenAI API Coding with Python – Codecademy](https://www.codecademy.com/learn/open-ai-api-coding-with-python)
- [OpenAI Quickstart Guide – Official Docs](https://platform.openai.com/docs/quickstart)
- [OpenAI Developer Full Course (YouTube)](https://www.youtube.com/watch?v=mnJJPltybBM)
