import streamlit as st
import os
from groq import Groq
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
from fpdf import FPDF
import io
import re
import json
from pypdf import PdfReader
import requests
import arabic_reshaper
from bidi.algorithm import get_display

# ==========================================
# 1. PAGE CONFIGURATION
# ==========================================
st.set_page_config(
    page_title="Elite CV Builder",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================
# 2. FONT SETUP (ARABIC SUPPORT)
# ==========================================
FONT_URL = "https://github.com/google/fonts/raw/main/ofl/amiri/Amiri-Regular.ttf"
FONT_PATH = "Amiri-Regular.ttf"

def check_and_download_font():
    if not os.path.exists(FONT_PATH):
        with st.spinner("Downloading fonts..."):
            try:
                response = requests.get(FONT_URL)
                with open(FONT_PATH, "wb") as f:
                    f.write(response.content)
            except Exception as e:
                st.error(f"Font download failed: {e}")

check_and_download_font()

# ==========================================
# 3. API & SIDEBAR
# ==========================================
api_key = None
using_shared_key = False

with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3135/3135715.png", width=50)
    st.title("💡 Quick Guide")
    st.markdown("""
    **Rules:**
    1. **Fill Data:** Upload old CV or write manually.
    2. **Language:** You can write in **Arabic** or **English**.
    3. **Output:** Final CV will be in **English** & ATS-Friendly.
    4. **Education:** Will be formatted in one line (Degree, College, Uni | Year).
    """)
    st.divider()
    with st.expander("⚙️ Settings"):
        use_own_key = st.checkbox("Use my own API Key", value=False)
        if use_own_key:
            user_input_key = st.text_input("Groq API Key", type="password")
            if user_input_key: api_key = user_input_key
        else:
            if "GROQ_API_KEY" in st.secrets: api_key = st.secrets["GROQ_API_KEY"]

if not api_key:
    st.warning("⚠️ Please configure the API Key.")
    st.stop()

client = Groq(api_key=api_key)
MODEL_NAME = "llama-3.3-70b-versatile"

# ==========================================
# 4. HELPER FUNCTIONS
# ==========================================
def process_text_for_pdf(text):
    if not text: return ""
    try:
        return get_display(arabic_reshaper.reshape(text))
    except: return text

def extract_text_from_pdf(file):
    reader = PdfReader(file); text = ""; 
    for page in reader.pages: text += page.extract_text()
    return text

def extract_text_from_docx(file):
    doc = Document(file); return "\n".join([para.text for para in doc.paragraphs])

def parse_resume_with_ai(text):
    prompt = f"""
    You are a Data Extraction Assistant.
    Task: Extract resume details and TRANSLATE values to English.
    Source: {text[:4000]}
    
    Rules:
    1. Arabic inputs must become English (e.g. "تجارة" -> "Commerce").
    2. "طالب" -> "Student".
    
    Output JSON keys: 
    "name", "email", "phone", "city", "linkedin", "target_title", "skills", "experience", 
    "university", "college", "degree", "grad_year".
    """
    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        return json.loads(completion.choices[0].message.content)
    except: return None

def get_job_suggestions(role_title):
    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": f"Give 5 English resume bullet points for {role_title}."}]
        )
        return completion.choices[0].message.content
    except: return "Error."

def safe_generate(prompt_text):
    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "system", "content": "You are a Senior HR Recruiter."}, {"role": "user", "content": prompt_text}],
            temperature=0.3
        )
        return completion.choices[0].message.content
    except Exception as e: return f"Error: {str(e)}"

# ==========================================
# 5. FILE GENERATORS
# ==========================================
def create_docx(text):
    doc = Document()
    for s in doc.sections: 
        s.top_margin = Inches(0.5); s.bottom_margin = Inches(0.5)
        s.left_margin = Inches(0.5); s.right_margin = Inches(0.5)
    
    text = text.replace("**", "").replace("##", "")
    for line in text.split('\n'):
        line = line.strip(); if not line: continue
        line_no_num = re.sub(r'^\d+\.\s*', '', line)
        
        # Header Detection
        if line_no_num.isupper() and len(line_no_num) < 60 and "|" not in line:
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(12); p.paragraph_format.space_after = Pt(6)
            run = p.add_run(line_no_num); run.bold = True; run.font.size = Pt(12)
            p.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER if "NAME" not in line else WD_PARAGRAPH_ALIGNMENT.LEFT
        elif "|" in line and "@" in line:
            p = doc.add_paragraph(line); p.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
        elif "|" in line and "@" not in line: # Experience/Edu Header line
            p = doc.add_paragraph(); p.paragraph_format.space_before = Pt(8)
            run = p.add_run(line); run.bold = True; p.alignment = WD_PARAGRAPH_ALIGNMENT.LEFT
        elif line.startswith('-') or line.startswith('•'):
            p = doc.add_paragraph(line.replace('-', '').replace('•', '').strip(), style='List Bullet')
        else:
            p = doc.add_paragraph(line)
    
    buffer = io.BytesIO(); doc.save(buffer); buffer.seek(0)
    return buffer

def create_pdf(text):
    class PDF(FPDF):
        def header(self): pass
        def footer(self): pass
    pdf = PDF(); pdf.add_page(); pdf.add_font('Amiri', '', FONT_PATH, uni=True); pdf.set_font('Amiri', '', 11)
    
    text = text.replace("**", "").replace("##", "")
    for line in text.split('\n'):
        line = line.strip(); if not line: continue; if "___" in line: continue
        
        line = process_text_for_pdf(line)
        line_no_num = re.sub(r'^\d+\.\s*', '', line)
        
        is_header = False
        if len(line) < 50 and "|" not in line and "." not in line and not line.startswith("-") and not line.startswith("•"):
             if re.search(r'[A-Z]', line) and line.isupper(): is_header = True

        if is_header:
            pdf.ln(6); pdf.set_font("Amiri", '', 13); pdf.cell(0, 6, line, ln=True, align='C')
            x = pdf.get_x(); y = pdf.get_y(); pdf.line(10, y, 200, y); pdf.ln(4); pdf.set_font("Amiri", '', 11)
        elif "|" in line and "@" in line: # Contact
            pdf.set_font("Amiri", '', 10); pdf.multi_cell(0, 5, line, align='C'); pdf.ln(4)
        elif "|" in line and "@" not in line: # Edu/Exp Titles (Bold-ish)
            pdf.ln(4); pdf.set_font("Amiri", '', 11); pdf.cell(0, 6, line, ln=True, align='L'); pdf.ln(2)
        elif line.startswith('-') or line.startswith('•'):
            pdf.set_font("Amiri", '', 11)
            clean_line = line.replace('-', '').replace('•', '').strip()
            pdf.multi_cell(0, 5, "• " + clean_line, align='L'); pdf.ln(2)
        else:
            pdf.set_font("Amiri", '', 11); pdf.multi_cell(0, 5, line, align='L'); pdf.ln(1)
            
    buffer = io.BytesIO(); buffer.write(pdf.output(dest='S').encode("latin1")); buffer.seek(0)
    return buffer

# ==========================================
# 6. STATE & NAVIGATION
# ==========================================
if 'step' not in st.session_state: st.session_state.step = 1
if 'cv_data' not in st.session_state: st.session_state.cv_data = {}
for k in ['final_cv', 'cover_letter', 'ats_analysis']:
    if k not in st.session_state: st.session_state[k] = ""

if st.session_state.step > 6: st.session_state.step = 1; st.rerun()
def next_step(): st.session_state.step += 1
def prev_step(): st.session_state.step -= 1

# ==========================================
# 7. MAIN UI
# ==========================================
st.title("🚀 Elite CV Builder")
if st.session_state.step < 6: st.progress(st.session_state.step / 6)

# STEP 1
if st.session_state.step == 1:
    st.header("1️⃣ Personal Info")
    with st.expander("📄 Upload Old CV (Auto-Fill)"):
        f = st.file_uploader("PDF/Word", type=['pdf', 'docx'])
        if f and st.button("🧠 Extract Data"):
            with st.spinner("Processing..."):
                try:
                    text = extract_text_from_pdf(f) if f.name.endswith('.pdf') else extract_text_from_docx(f)
                    data = parse_resume_with_ai(text)
                    if data: st.session_state.cv_data.update(data); st.success("Done!"); st.rerun()
                except: st.error("Error parsing.")

    with st.form("s1"):
        c1, c2 = st.columns(2)
        with c1: 
            name = st.text_input("Name", st.session_state.cv_data.get('name', ''))
            email = st.text_input("Email", st.session_state.cv_data.get('email', ''))
            city = st.text_input("City", st.session_state.cv_data.get('city', ''))
            portfolio = st.text_input("Portfolio", st.session_state.cv_data.get('portfolio', ''))
        with c2: 
            phone = st.text_input("Phone", st.session_state.cv_data.get('phone', ''))
            linkedin = st.text_input("LinkedIn", st.session_state.cv_data.get('linkedin', ''))
            github = st.text_input("GitHub", st.session_state.cv_data.get('github', ''))
        
        st.markdown("---")
        target_title = st.text_input("🔴 Target Job Title", st.session_state.cv_data.get('target_title', ''))
        
        st.markdown("### 🎓 Education")
        d1, d2, d3, d4 = st.columns(4)
        with d1: uni = st.text_input("University", st.session_state.cv_data.get('university', ''))
        with d2: col = st.text_input("College", st.session_state.cv_data.get('college', ''))
        with d3: deg = st.text_input("Degree", st.session_state.cv_data.get('degree', ''))
        with d4: yr = st.text_input("Grad Year", st.session_state.cv_data.get('grad_year', ''))

        if st.form_submit_button("Next ➡️"):
            if name and target_title:
                st.session_state.cv_data.update({'name':name, 'email':email, 'phone':phone, 'linkedin':linkedin, 'city':city, 'portfolio':portfolio, 'github':github, 'target_title':target_title, 'university':uni, 'college':col, 'degree':deg, 'grad_year':yr})
                next_step(); st.rerun()
            else: st.warning("Name & Job Title required!")

# STEP 2
elif st.session_state.step == 2:
    st.header("2️⃣ Skills")
    with st.form("s2"):
        skills = st.text_area("Skills", st.session_state.cv_data.get('skills', ''))
        langs = st.text_input("Languages", st.session_state.cv_data.get('languages', ''))
        c1, c2 = st.columns([1, 5])
        with c1: 
            if st.form_submit_button("Back"): prev_step(); st.rerun()
        with c2:
            if st.form_submit_button("Next ➡️"): st.session_state.cv_data.update({'skills':skills, 'languages':langs}); next_step(); st.rerun()

# STEP 3
elif st.session_state.step == 3:
    st.header("3️⃣ Experience")
    c_in, c_bt = st.columns([3, 1])
    with c_in: role = st.text_input("Role Title", value=st.session_state.cv_data.get('target_title', ''), label_visibility='collapsed')
    with c_bt:
        if st.button("Get Suggestions 🧠", use_container_width=True):
            with st.spinner("..."): 
                sugg = get_job_suggestions(role)
                st.session_state.cv_data['raw_experience'] = st.session_state.cv_data.get('raw_experience', '') + "\n" + sugg
                st.rerun()

    with st.form("s3"):
        exp = st.text_area("Experience:", st.session_state.cv_data.get('raw_experience', ''), height=250)
        c1, c2 = st.columns([1, 5])
        with c1: 
            if st.form_submit_button("Back"): prev_step(); st.rerun()
        with c2:
            if st.form_submit_button("Next ➡️"): st.session_state.cv_data['raw_experience'] = exp; next_step(); st.rerun()

# STEP 4
elif st.session_state.step == 4:
    st.header("4️⃣ Projects")
    with st.form("s4"):
        proj = st.text_area("Projects", st.session_state.cv_data.get('projects', ''))
        cert = st.text_area("Certifications", st.session_state.cv_data.get('certs', ''))
        vol = st.text_area("Volunteering", st.session_state.cv_data.get('volunteering', ''))
        c1, c2 = st.columns([1, 5])
        with c1: 
            if st.form_submit_button("Back"): prev_step(); st.rerun()
        with c2:
            if st.form_submit_button("Next ➡️"): st.session_state.cv_data.update({'projects':proj, 'certs':cert, 'volunteering':vol}); next_step(); st.rerun()

# STEP 5
elif st.session_state.step == 5:
    st.header("5️⃣ Target Job")
    with st.form("s5"):
        jd = st.text_area("Job Description", st.session_state.cv_data.get('target_job', ''))
        c1, c2 = st.columns([1, 5])
        with c1: 
            if st.form_submit_button("Back"): prev_step(); st.rerun()
        with c2:
            if st.form_submit_button("Generate CV 🚀"): st.session_state.cv_data['target_job'] = jd; next_step(); st.rerun()

# STEP 6
elif st.session_state.step == 6:
    st.balloons(); st.success("CV Ready!")
    
    # Safe Filename
    raw_name = st.session_state.cv_data.get('name', 'User')
    safe_name = "".join([c if c.isalnum() or c==" " else "_" for c in raw_name]).strip().replace(" ", "_")
    if not safe_name: safe_name = "My_Resume"
    
    t1, t2, t3 = st.tabs(["📄 Resume", "✉️ Cover Letter", "📊 ATS Score"])
    jd = st.session_state.cv_data.get('target_job', '')
    
    with t1:
        if not st.session_state.final_cv:
            with st.spinner("Formatting..."):
                # 1. Contact Info
                info = [st.session_state.cv_data[k] for k in ['phone', 'city', 'email', 'linkedin', 'github', 'portfolio'] if st.session_state.cv_data.get(k)]
                c_line = " | ".join(info)
                
                # 2. Education (Formatted Horizontally)
                edu_block = ""
                if any(st.session_state.cv_data.get(k) for k in ['university', 'college', 'degree', 'grad_year']):
                    # Build list: Degree, College, University
                    edu_parts = []
                    if st.session_state.cv_data.get('degree'): edu_parts.append(st.session_state.cv_data['degree'])
                    if st.session_state.cv_data.get('college'): edu_parts.append(st.session_state.cv_data['college'])
                    if st.session_state.cv_data.get('university'): edu_parts.append(st.session_state.cv_data['university'])
                    
                    # Join with comma
                    edu_str = ", ".join(edu_parts)
                    # Add Year with pipe separator
                    if st.session_state.cv_data.get('grad_year'):
                        edu_str += f" | {st.session_state.cv_data['grad_year']}"
                    
                    edu_block = f"EDUCATION\n{edu_str}\n"

                # 3. Extras
                extras = ""
                if st.session_state.cv_data.get('projects'): extras += f"\nPROJECTS\n{st.session_state.cv_data['projects']}\n"
                if st.session_state.cv_data.get('certs'): extras += f"\nCERTIFICATIONS\n{st.session_state.cv_data['certs']}\n"
                if st.session_state.cv_data.get('volunteering'): extras += f"\nVOLUNTEERING\n{st.session_state.cv_data['volunteering']}\n"
                
                # 4. Languages
                langs = ""
                if st.session_state.cv_data.get('languages'): langs = f"LANGUAGES ({st.session_state.cv_data['languages']})"

                prompt = f"""
                Act as a Resume Expert. Rewrite in Professional ENGLISH.
                
                RULES:
                1. Translate Arabic to English (e.g. "تجارة" -> "Commerce").
                2. Education Format: Keep it in ONE LINE (Degree, College, Uni | Year).
                3. Clean Text. No Markdown Bold (**). No Numbered Sections.
                
                HEADER: {st.session_state.cv_data['name'].upper()} \n {c_line}
                SUMMARY (for {st.session_state.cv_data['target_title']})
                SKILLS ({st.session_state.cv_data['skills']})
                EXPERIENCE: {st.session_state.cv_data['raw_experience']}
                {edu_block}
                {extras}
                {langs}
                """
                res = safe_generate(prompt)
                if "Error" in res: st.error(res)
                else: st.session_state.final_cv = res; st.rerun()

        if st.session_state.final_cv:
            st.text_area("Editor", st.session_state.final_cv, height=500)
            c1, c2, c3 = st.columns(3)
            c1.download_button("PDF", create_pdf(st.session_state.final_cv), f"{safe_name}.pdf", "application/pdf")
            c2.download_button("Word", create_docx(st.session_state.final_cv), f"{safe_name}.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
            if c3.button("Reset"): st.session_state.final_cv=""; st.rerun()

    with t2:
        if st.button("Write Letter"):
            with st.spinner("..."):
                st.session_state.cover_letter = safe_generate(f"Write Cover Letter for {st.session_state.cv_data['name']} targeting {st.session_state.cv_data['target_title']}")
                st.rerun()
        if st.session_state.cover_letter:
            st.text_area("Letter", st.session_state.cover_letter)
            st.download_button("Download", create_docx(st.session_state.cover_letter), "Cover.docx")

    with t3:
        if st.button("ATS Check"):
            if not jd: st.warning("No Job Description found in Step 5!")
            else:
                with st.spinner("Analyzing..."):
                    ats_res = safe_generate(f"Analyze this CV against JD:\n\nCV:{st.session_state.final_cv}\n\nJD:{jd}\n\nOutput: Score/100, Missing Keywords, Tips.")
                    st.session_state.ats_analysis = ats_res
                    st.rerun()
        if st.session_state.ats_analysis: st.info("ATS Result:"); st.write(st.session_state.ats_analysis)

    st.markdown("---")
    if st.button("Start Over"):
        st.session_state.step = 1; st.session_state.cv_data = {}; st.session_state.final_cv = ""; st.rerun()
