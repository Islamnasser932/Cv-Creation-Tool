import streamlit as st
import os
from groq import Groq
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
from fpdf import FPDF
import io
import re

# 1. Page Config & Layout
st.set_page_config(
    page_title="Elite CV Builder",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. Sidebar & Hybrid API Logic ---
# تعريف متغيرات الاتصال
api_key = None
using_shared_key = False

with st.sidebar:
    st.title("⚙️ Configuration")
    st.info("💡 **Tip:** This tool uses Groq's Llama 3.3 AI.")
    
    # --- Hybrid Logic Start ---
    # خيار للمستخدم: يستخدم السيرفر المجاني ولا مفتاحه الخاص
    use_own_key = st.checkbox("Use my own API Key (More Stability)", value=False)
    
    if use_own_key:
        user_input_key = st.text_input("🔑 Enter Groq API Key", type="password", help="Get it for free from console.groq.com")
        if user_input_key:
            api_key = user_input_key
            using_shared_key = False
    else:
        # محاولة استخدام مفتاح السيرفر (مفتاحك أنت)
        if "GROQ_API_KEY" in st.secrets:
            api_key = st.secrets["GROQ_API_KEY"]
            using_shared_key = True
            st.success("✅ Connected via Shared Server")
        else:
            st.warning("⚠️ No Shared Key found in Secrets.")
    # --- Hybrid Logic End ---

    st.markdown("---")
    st.markdown("""
    **How to use:**
    1. Fill in your **Personal Info**.
    2. Add your **Skills**.
    3. Paste your **Experience** (Simple bullets).
    4. Provide a **Target Job** (Optional).
    5. Click **Generate**!
    """)
    st.markdown("---")
    st.caption("Developed by [Islam Nasser](https://www.linkedin.com/in/islam-nasser1/)")

# Check Connection
if not api_key:
    st.warning("⚠️ Please enter an API Key in the sidebar or configure secrets.")
    st.stop()

client = Groq(api_key=api_key)
MODEL_NAME = "llama-3.3-70b-versatile"

# --- Helper Functions (Formatting) ---
def create_docx(text):
    doc = Document()
    sections = doc.sections
    for section in sections:
        section.top_margin = Inches(0.5)
        section.bottom_margin = Inches(0.5)
        section.left_margin = Inches(0.5)
        section.right_margin = Inches(0.5)

    # Clean markdown
    text = text.replace("**", "").replace("##", "")

    for line in text.split('\n'):
        line = line.strip()
        if not line: continue
        
        # Logic to detect headers based on Uppercase + Length
        line_no_num = re.sub(r'^\d+\.\s*', '', line)
        
        if line_no_num.isupper() and len(line_no_num) < 60 and "|" not in line:
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(12)
            p.paragraph_format.space_after = Pt(6)
            run = p.add_run(line_no_num)
            run.bold = True
            run.font.size = Pt(12)
            p.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER if "NAME" not in line else WD_PARAGRAPH_ALIGNMENT.LEFT
            
        elif "|" in line and "@" in line:
            p = doc.add_paragraph(line)
            p.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
            p.paragraph_format.space_after = Pt(12)
            
        elif "|" in line and "@" not in line:
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(8) 
            run = p.add_run(line)
            run.bold = True 
            run.font.size = Pt(11)
            p.alignment = WD_PARAGRAPH_ALIGNMENT.LEFT
            
        elif line.startswith('-') or line.startswith('•'):
            clean_line = line.replace('•', '').replace('-', '').strip()
            p = doc.add_paragraph(clean_line, style='List Bullet')
            p.paragraph_format.space_after = Pt(2) 
            
        else:
            p = doc.add_paragraph(line)
            p.paragraph_format.space_after = Pt(2)

    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

def create_pdf(text):
    class PDF(FPDF):
        def header(self): pass
        def footer(self): pass
            
    pdf = PDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    # Text Cleanups
    text = text.replace("**", "").replace("##", "")
    replacements = {
        u'\u2013': '-', u'\u2014': '-', u'\u2018': "'", u'\u2019': "'",
        u'\u201c': '"', u'\u201d': '"', '•': '-', '–': '-'
    }
    for k, v in replacements.items(): text = text.replace(k, v)
        
    try:
        text = text.encode('latin-1', 'replace').decode('latin-1')
    except:
        text = text # Fallback
    
    for line in text.split('\n'):
        line = line.strip()
        if not line: continue
        if "___" in line: continue

        line_no_num = re.sub(r'^\d+\.\s*', '', line)

        if line_no_num.isupper() and len(line_no_num) < 60 and "|" not in line:
            pdf.ln(6)
            pdf.set_font("Arial", 'B', size=12)
            pdf.cell(0, 6, line_no_num, ln=True, align='C')
            x = pdf.get_x()
            y = pdf.get_y()
            pdf.line(x + 10, y, 200, y)
            pdf.ln(4)
            
        elif "|" in line and "@" in line:
            pdf.set_font("Arial", size=9) 
            pdf.multi_cell(0, 5, line, align='C')
            pdf.ln(4)
            
        elif "|" in line and "@" not in line:
            pdf.ln(4)
            pdf.set_font("Arial", 'B', size=10)
            pdf.cell(0, 6, line, ln=True, align='L')
            pdf.ln(2)
            
        elif line.startswith('-'):
            pdf.set_font("Arial", size=10)
            clean_line = line.replace('-', '').strip()
            pdf.multi_cell(0, 5, chr(149) + " " + clean_line) 
            pdf.ln(2)
            
        else:
            pdf.set_font("Arial", size=10)
            pdf.multi_cell(0, 5, line)
            pdf.ln(1)
            
    buffer = io.BytesIO()
    pdf_output = pdf.output(dest='S').encode('latin-1')
    buffer.write(pdf_output)
    buffer.seek(0)
    return buffer

def safe_generate(prompt_text):
    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "You are a Senior HR Recruiter. Output strict, clean text. Do NOT use markdown bold (**). Do NOT number the sections."},
                {"role": "user", "content": prompt_text}
            ],
            temperature=0.3,
            max_tokens=3500,
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"Error: {str(e)}"

# --- Session State ---
if 'step' not in st.session_state: st.session_state.step = 1
if 'cv_data' not in st.session_state: st.session_state.cv_data = {}
for key in ['final_cv', 'cover_letter', 'ats_analysis']:
    if key not in st.session_state: st.session_state[key] = ""

if st.session_state.step > 6: st.session_state.step = 1; st.rerun()

def next_step(): st.session_state.step += 1
def prev_step(): st.session_state.step -= 1

# --- UI Header ---
st.title("🚀 Elite CV Builder")
st.markdown("##### Build an ATS-Optimized Resume in Minutes using AI")

if st.session_state.step < 6: st.progress(st.session_state.step / 6)

# STEP 1: Personal Info
if st.session_state.step == 1:
    st.header("1️⃣ Personal Info")
    st.info("🔒 Your data is processed securely and not stored.")
    with st.form("step1"):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Full Name", st.session_state.cv_data.get('name', ''))
            email = st.text_input("Email", st.session_state.cv_data.get('email', ''))
            city = st.text_input("City, Country", st.session_state.cv_data.get('city', ''))
            portfolio = st.text_input("Portfolio Link", st.session_state.cv_data.get('portfolio', ''))
        with col2:
            phone = st.text_input("Phone", st.session_state.cv_data.get('phone', ''))
            linkedin = st.text_input("LinkedIn Link", st.session_state.cv_data.get('linkedin', ''))
            github = st.text_input("GitHub Link", st.session_state.cv_data.get('github', ''))
        
        st.markdown("---")
        target_title = st.text_input("Target Job Title (e.g. Data Scientist)", st.session_state.cv_data.get('target_title', ''))
        
        c1, c2, c3 = st.columns(3)
        with c1: university = st.text_input("University", st.session_state.cv_data.get('university', ''))
        with c2: degree = st.text_input("Degree", st.session_state.cv_data.get('degree', ''))
        with c3: grad_year = st.text_input("Graduation Year", st.session_state.cv_data.get('grad_year', ''))

        if st.form_submit_button("Next Step ➡️"):
            if name and email and target_title:
                st.session_state.cv_data.update({
                    'name':name, 'email':email, 'phone':phone, 'linkedin':linkedin, 'city':city, 
                    'portfolio':portfolio, 'github':github, 
                    'target_title':target_title, 'university':university, 'degree':degree, 'grad_year':grad_year
                })
                next_step(); st.rerun()
            else: st.warning("⚠️ Name, Email, and Target Job are required!")

# STEP 2: Skills
elif st.session_state.step == 2:
    st.header("2️⃣ Skills")
    with st.form("step2"):
        st.write("List your technical skills (e.g. Python, SQL, Tableau). The AI will organize them.")
        skills = st.text_area("Skills", st.session_state.cv_data.get('skills', ''), height=150)
        languages = st.text_input("Languages (e.g. Arabic Native, English Fluent)", st.session_state.cv_data.get('languages', ''))
        
        col1, col2 = st.columns([1, 5])
        with col1: 
            if st.form_submit_button("⬅️ Back"): prev_step(); st.rerun()
        with col2:
            if st.form_submit_button("Next Step ➡️"):
                st.session_state.cv_data.update({'skills':skills, 'languages':languages})
                next_step(); st.rerun()

# STEP 3: Experience
elif st.session_state.step == 3:
    st.header("3️⃣ Experience")
    with st.form("step3"):
        st.info("💡 **Tip:** Just write what you did. The AI will add action verbs and metrics.")
        raw_experience = st.text_area("Paste your experience here:", st.session_state.cv_data.get('raw_experience', ''), height=200, placeholder="Example:\nData Analyst at Company X (2022-2023)\n- Cleaned data using Python\n- Created dashboards")
        
        col1, col2 = st.columns([1, 5])
        with col1: 
            if st.form_submit_button("⬅️ Back"): prev_step(); st.rerun()
        with col2:
            if st.form_submit_button("Next Step ➡️"):
                st.session_state.cv_data['raw_experience'] = raw_experience
                next_step(); st.rerun()

# STEP 4: Projects & Extras
elif st.session_state.step == 4:
    st.header("4️⃣ Projects & Extras")
    with st.form("step4"):
        projects = st.text_area("Projects", st.session_state.cv_data.get('projects', ''))
        certs = st.text_area("Certifications", st.session_state.cv_data.get('certs', ''))
        volunteering = st.text_area("Volunteering", st.session_state.cv_data.get('volunteering', ''))
        
        col1, col2 = st.columns([1, 5])
        with col1: 
            if st.form_submit_button("⬅️ Back"): prev_step(); st.rerun()
        with col2:
            if st.form_submit_button("Next Step ➡️"):
                st.session_state.cv_data.update({'projects':projects, 'certs':certs, 'volunteering':volunteering})
                next_step(); st.rerun()

# STEP 5: Target Job
elif st.session_state.step == 5:
    st.header("5️⃣ Target Job Analysis")
    with st.form("step5"):
        st.write("Paste the Job Description (JD) you are applying for. The AI will tailor your CV keywords to match it.")
        target_job = st.text_area("Job Description (Optional but Recommended)", st.session_state.cv_data.get('target_job', ''), height=150)
        
        col1, col2 = st.columns([1, 5])
        with col1: 
            if st.form_submit_button("⬅️ Back"): prev_step(); st.rerun()
        with col2:
            if st.form_submit_button("🚀 Generate CV"):
                st.session_state.cv_data['target_job'] = target_job
                next_step(); st.rerun()

# STEP 6: Result Dashboard
elif st.session_state.step == 6:
    st.success("🎉 CV Generated Successfully!")
    
    # Create Dynamic File Name
    safe_name = re.sub(r'[^a-zA-Z0-9]', '_', st.session_state.cv_data.get('name', 'User'))
    file_name = f"{safe_name}_CV.pdf"
    word_file_name = f"{safe_name}_CV.docx"

    t1, t2, t3 = st.tabs(["📄 Resume Preview", "✉️ Cover Letter", "📊 ATS Score"])
    jd = st.session_state.cv_data.get('target_job', '')

    with t1:
        if not st.session_state.final_cv:
            with st.spinner("🤖 AI is writing your resume..."):
                
                # Logic to build Prompt
                contact_parts = [st.session_state.cv_data[k] for k in ['phone', 'city', 'email', 'linkedin', 'github', 'portfolio'] if st.session_state.cv_data.get(k)]
                contact_line = " | ".join(contact_parts)

                optional_prompt = ""
                if st.session_state.cv_data.get('projects'):
                    optional_prompt += f"\n5. **PROJECTS**\n   - Projects: {st.session_state.cv_data['projects']}\n   - Rule: Include ALL projects. Format: **Name | Stack**\n   - Description: Concise bullet with impact."
                if st.session_state.cv_data.get('certs'): optional_prompt += f"\n6. **CERTIFICATIONS**\n   - {st.session_state.cv_data['certs']}"
                if st.session_state.cv_data.get('volunteering'): optional_prompt += f"\n7. **VOLUNTEERING**\n   - {st.session_state.cv_data['volunteering']}"

                prompt_cv = f"""
                Act as a Senior Resume Expert. Write a professional CV based on this data.
                
                **RULES:**
                1. Clean Text Only (No markdown bold like **).
                2. No Section Numbers (Just "PROFESSIONAL EXPERIENCE").
                3. Metrics: Add numbers (%, $) to experience bullets.
                4. Dates: Use "Mon YYYY" format.
                
                **HEADER:**
                {st.session_state.cv_data['name'].upper()}
                {contact_line}
                
                **SECTIONS:**
                PROFESSIONAL SUMMARY (3 lines, tailored to {st.session_state.cv_data['target_title']})
                
                TECHNICAL SKILLS (Grouped: Languages, Tools, etc. Include ALL user skills: {st.session_state.cv_data['skills']})
                
                PROFESSIONAL EXPERIENCE (Role | Company | Dates)
                User Data: {st.session_state.cv_data['raw_experience']}
                
                EDUCATION ({st.session_state.cv_data['degree']}, {st.session_state.cv_data['university']}, {st.session_state.cv_data['grad_year']})
                
                {optional_prompt}
                
                LANGUAGES ({st.session_state.cv_data['languages']})
                """
                
                generated_text = safe_generate(prompt_cv)
                
                # Error Handling in UI
                if "Error:" in generated_text:
                    st.error(f"⚠️ AI Generation Failed: {generated_text}")
                    if using_shared_key:
                        st.info("💡 The shared server might be busy. Please check 'Use my own API Key' in the sidebar to proceed.")
                else:
                    st.session_state.final_cv = generated_text
                    st.rerun()

        if st.session_state.final_cv:
            st.text_area("Editor (You can tweak text here before downloading)", st.session_state.final_cv, height=500)
            
            c1, c2, c3 = st.columns(3)
            # Custom File Name Logic
            c1.download_button("⬇️ Download PDF", create_pdf(st.session_state.final_cv), file_name, "application/pdf")
            c2.download_button("⬇️ Download Word", create_docx(st.session_state.final_cv), word_file_name, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
            if c3.button("🔄 Regenerate"):
                st.session_state.final_cv = ""
                st.rerun()
        
    with t2:
        if st.button("✨ Generate Cover Letter"):
            with st.spinner("Writing..."):
                prompt_cl = f"Write a cover letter for {st.session_state.cv_data['name']} for {st.session_state.cv_data['target_title']} role."
                st.session_state.cover_letter = safe_generate(prompt_cl)
                st.rerun()

        if st.session_state.cover_letter:
            st.text_area("Cover Letter", st.session_state.cover_letter, height=400)
            st.download_button("⬇️ Download Letter", create_docx(st.session_state.cover_letter), "Cover_Letter.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    
    with t3:
        if st.button("🔍 Check ATS Score"):
            with st.spinner("Analyzing..."):
                prompt_ats = f"Analyze this CV against this Job Description: {jd}. Give a Score out of 100 and list missing keywords."
                st.session_state.ats_analysis = safe_generate(prompt_ats)
                st.rerun()

        if st.session_state.ats_analysis:
            st.write(st.session_state.ats_analysis)

    st.markdown("---")
    if st.button("Start Over"):
        st.session_state.step = 1; st.session_state.cv_data = {}; st.session_state.final_cv = ""; st.rerun()
