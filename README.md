# 🚀 Elite CV Builder | AI-Powered Resume Assistant

![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=Streamlit&logoColor=white)
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Groq](https://img.shields.io/badge/AI-Groq%20Llama%203-orange?style=for-the-badge)

**Elite CV Builder** is an intelligent, ATS-optimized resume generator powered by **Groq (Llama 3.3)**. It acts as a Senior HR Recruiter, transforming raw experience into a high-impact, quantifiable, and perfectly formatted CV (PDF & Word), tailored specifically to pass Applicant Tracking Systems.

---

## 🌟 Key Features

This is not just a resume writer; it is a full career optimization suite:

* **🧠 Smart AI Logic:** Leverages **Llama 3.3** to analyze experience and rewrite it using the **Google XYZ Formula** (Accomplished [X] as measured by [Y], by doing [Z]) for maximum impact.
* **🎯 ATS Optimization:** Analyzes the target **Job Description (JD)** and intelligently injects relevant keywords to ensure high ranking in ATS filters.
* **🎨 Professional Formatting:**
    * **Clean Layout:** No complex tables or graphics that confuse ATS parsers.
    * **Smart Alignment:** Professional left/center alignment logic.
    * **Consistency:** Automatically standardizes date formats (e.g., "May 2023 - Present").
* **📂 Multi-Format Export:** Generates both **PDF** (ready to submit) and **Word/DOCX** (fully editable) files with perfect formatting.
* **💡 Intelligent Inferences:** If project details are missing, the AI infers the likely tech stack and impact based on the project title.
* **🔒 Secure & Scalable:** Supports custom user API keys via the sidebar for scalability, with a fallback to the app's default key.

---

## 🛠️ Tech Stack

* **Frontend:** [Streamlit](https://streamlit.io/) (Interactive Web UI).
* **AI Engine:** [Groq API](https://groq.com/) (Llama-3.3-70b-versatile for ultra-fast inference).
* **PDF Generation:** `fpdf2` (Programmatic PDF creation).
* **Word Generation:** `python-docx` (Editable document generation).

---

## 🚀 Installation & Setup

To run this project locally on your machine:

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/YourUsername/Elite-CV-Builder.git](https://github.com/YourUsername/Elite-CV-Builder.git)
    cd Elite-CV-Builder
    ```

2.  **Install requirements:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Setup API Keys:**
    * Create a folder named `.streamlit` in the root directory.
    * Inside it, create a file named `secrets.toml`.
    * Add your Groq API Key:
    ```toml
    GROQ_API_KEY = "gsk_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
    ```

4.  **Run the App:**
    ```bash
    streamlit run app.py
    ```

---

## 📖 How to Use

1.  **Personal Info:** Enter your contact details, LinkedIn, GitHub, and target job title.
2.  **Skills:** List your hard skills (the AI will categorize them logically).
3.  **Experience:** Paste your raw experience bullets. The AI will rewrite them into metric-driven achievements.
4.  **Projects:** Add your key projects. The AI will generate technical descriptions and tech stacks.
5.  **Target Job (Crucial):** Paste the Job Description you are applying for. The AI will tailor your CV to match it.
6.  **Generate:** Click the button to generate your CV and download it as PDF or Word.

---

## 🤝 Contributing

Contributions are welcome! If you have ideas for improvements:
1.  Fork the Project.
2.  Create your Feature Branch (`git checkout -b feature/AmazingFeature`).
3.  Commit your Changes (`git commit -m 'Add some AmazingFeature'`).
4.  Push to the Branch (`git push origin feature/AmazingFeature`).
5.  Open a Pull Request.

---

## 📞 Contact

Developed by **Islam Nasser**

* [LinkedIn](https://www.linkedin.com/in/islam-nasser1/)
* [GitHub](https://github.com/Islamnasser932)
* [Portfolio](https://islamnasser.vercel.app/)

---
*If you find this tool useful, please give it a ⭐ on GitHub!*
