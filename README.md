# 🚀 Elite CV Builder | AI-Powered Resume Assistant

![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=Streamlit&logoColor=white)
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Groq](https://img.shields.io/badge/AI-Groq%20Llama%203-orange?style=for-the-badge)

**Elite CV Builder** is an intelligent, ATS-optimized resume generator powered by **Groq (Llama 3.3)**. It acts as a Senior HR Recruiter, helping users build world-class resumes from scratch or by upgrading their old ones.

Website Link : https://cv-creation-tool-n47uq2tqi3mpjvu6tfjgv5.streamlit.app/
---

## 🌟 Key Features

### 1. 🧠 Smart Resume Parser (New!)
* **Don't start from scratch:** Upload your old CV (PDF or Word), and the AI will extract your Name, Skills, and Experience automatically.
* **Time-Saver:** Pre-fills the form so you only need to review and tweak.

### 2. ✨ AI Content Suggestions
* **Writer's Block?** If you don't know how to describe your experience, just type your Job Title.
* **Instant Magic:** Click "Get Suggestions" to receive 5 metric-driven, strong bullet points tailored to your role.

### 3. 🎯 ATS Optimization
* Analyzes the **Job Description (JD)** you are applying for.
* Injects relevant **Keywords** to ensure your CV passes automated filtering systems.

### 4. ⚙️ Hybrid API System
* **Free Mode:** Uses a shared API key configured by the developer.
* **Pro Mode:** Users can enter their *own* Groq API Key in the sidebar for faster, private performance and to bypass rate limits.

### 5. 📂 Multi-Format Export
* **PDF:** Clean, professional design ready for application.
* **Word (DOCX):** Fully editable file for manual adjustments.

---

## 🛠️ Tech Stack

* **Frontend:** [Streamlit](https://streamlit.io/)
* **AI Engine:** [Groq API](https://groq.com/) (Llama-3.3-70b-versatile)
* **File Parsing:** `pypdf` (for PDF), `python-docx` (for Word)
* **File Generation:** `fpdf`, `python-docx`

---

## 🚀 Installation & Setup

To run this project locally:

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/YourUsername/Elite-CV-Builder.git](https://github.com/YourUsername/Elite-CV-Builder.git)
    cd Elite-CV-Builder
    ```

2.  **Install requirements:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Configure API Key (Secrets):**
    * Create a folder named `.streamlit` in the root directory.
    * Inside it, create a file named `secrets.toml`.
    * Add your Groq API Key (this will be the "Shared Key"):
    ```toml
    GROQ_API_KEY = "gsk_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
    ```

4.  **Run the App:**
    ```bash
    streamlit run app.py
    ```

---

## 📖 How to Use

1.  **Step 1 (Personal Info):** Fill in your details manually **OR** upload an old CV to auto-fill the data.
2.  **Step 2 (Skills):** List your technical and soft skills.
3.  **Step 3 (Experience):** * Type your experience.
    * Use the **"Get Suggestions"** button to let AI write professional bullet points for you.
4.  **Step 4 (Projects):** Add extra details like certifications or volunteering.
5.  **Step 5 (Target Job):** Paste the Job Description for ATS tailoring.
6.  **Step 6 (Download):** Preview your CV, generate a Cover Letter, check your ATS Score, and Download!

---

## 🤝 Contributing

Contributions are welcome!
1.  Fork the Project
2.  Create your Feature Branch (`git checkout -b feature/NewFeature`)
3.  Commit your Changes (`git commit -m 'Add NewFeature'`)
4.  Push to the Branch (`git push origin feature/NewFeature`)
5.  Open a Pull Request

---

## 📞 Contact

**Islam Nasser**

* [LinkedIn](https://www.linkedin.com/in/islam-nasser1/)
* [GitHub](https://github.com/Islamnasser932)

---
*If you find this tool useful, please give it a ⭐ on GitHub!*
