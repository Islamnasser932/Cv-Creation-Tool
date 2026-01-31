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
# 2. FONT SETUP
# ==========================================
FONT_URL = "https://github.com/google/fonts/raw/main/ofl/amiri/Amiri-Regular.ttf"
FONT_PATH = "Amiri-Regular.ttf"

def check_and_download_font():
    if not os.path.exists(FONT_PATH):
        try:
            response = requests.get(FONT_URL)
            with open(FONT_PATH, "wb") as f:
                f.write(response.content)
        except: pass

check_and_download_font()

# ==========================================
# 3. API SETUP
# ==========================================
api_key = None
if "GROQ_API_KEY" in st.secrets:
    api_key = st.secrets["GROQ_API_KEY"]

with st.sidebar:
    st.title("💡 Quick Guide")
    st.markdown("1. Upload Old CV or Fill Manually.\n2. Add multiple Education/Projects using buttons.\n3. Output is always Professional English.")
    
    use_own_key = st.checkbox("Use my own API Key")
    if use_own_key:
        api_key = st.text_input("Groq API Key", type="password")

if not api_key:
    st.warning("⚠️ Please configure API Key.")
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
    reader = PdfReader(file); text = ""
    for page in reader.pages: text += page.extract_text()
    return text

def extract_text_from_docx(file):
    doc = Document(file); return "\n".join([para.text for para in doc.paragraphs])

def parse_resume_with_ai(text):
    # Simplified parser - structured data handling would require complex parsing logic
    # For now, we extract raw text and put it into the first entry or raw fields
    prompt = f"Extract resume details and TRANSLATE to English. Source: {text[:4000]}. Output JSON keys: name, email, phone, city, linkedin, target_title, skills, raw_experience."
    try:
        completion = client.chat.completions.create(model=MODEL_NAME, messages=[{"role": "user", "content": prompt}], response_format={"type": "json_object"})
        return json.loads(completion.choices[0].message.content)
    except: return None

def get_job_suggestions(role_title):
    try:
        completion = client.chat.completions.create(model=MODEL_NAME, messages=[{"role": "user", "content": f"Give 5 English resume bullet points for {role_title}."}])
        return completion.choices[0].message.content
    except: return "Error."

def safe_generate(prompt_text):
    try:
        completion = client.chat.completions.create(model=MODEL_NAME, messages=[{"role": "system", "content": "You are a Senior HR Recruiter."}, {"role": "user", "content": prompt_text}], temperature=0.3)
        return completion.choices[0].message.content
    except Exception as e: return f"Error: {str(e)}"

# ==========================================
# 5. FILE GENERATORS
# ==========================================
def create_pdf(text):
    class PDF(FPDF):
        def header(self): pass
        def footer(self): pass
    pdf = PDF(); pdf.add_page(); pdf.add_font('Amiri', '', FONT_PATH, uni=True); pdf.set_font('Amiri', '', 11)
    
    text = text.replace("**", "").replace("##", "")
    for line in text.split('\n'):
        line = line.strip()
        if not line or "___" in line: continue
        line = process_text_for_pdf(line)
        
        is_header = False
        if len(line) < 50 and "|" not in line and "." not in line and not line.startswith("-") and not line.startswith("•"):
             if re.search(r'[A-Z]', line) and line.isupper(): is_header = True

        if is_header:
            pdf.ln(5); pdf.set_font("Amiri", '', 13); pdf.cell(0, 6, line, ln=True, align='C'); 
            x = pdf.get_x(); y = pdf.get_y(); pdf.line(10, y, 200, y); pdf.ln(3); pdf.set_font("Amiri", '', 11)
        elif "|" in line and "@" in line:
            pdf.set_font("Amiri", '', 10); pdf.multi_cell(0, 5, line, align='C'); pdf.ln(3)
        elif "|" in line and "@" not in line:
            pdf.ln(3); pdf.set_font("Amiri", '', 11); pdf.cell(0, 6, line, ln=True, align='L'); pdf.ln(1)
        elif line.startswith('-') or line.startswith('•'):
            pdf.set_font("Amiri", '', 11); pdf.multi_cell(0, 5, "  " + line, align='L'); pdf.ln(1)
        else:
            pdf.set_font("Amiri", '', 11); pdf.multi_cell(0, 5, line, align='L'); pdf.ln(1)
            
    buffer = io.BytesIO(); buffer.write(pdf.output(dest='S').encode("latin1")); buffer.seek(0)
    return buffer

def create_docx(text):
    doc = Document()
    for s in doc.sections: s.top_margin = Inches(0.5); s.bottom_margin = Inches(0.5); s.left_margin = Inches(0.5); s.right_margin = Inches(0.5)
    text = text.replace("**", "").replace("##", "")
    for line in text.split('\n'):
        line = line.strip(); if not line: continue
        if line.isupper() and len(line) < 60 and "|" not in line:
            p = doc.add_paragraph(); run = p.add_run(line); run.bold = True; run.font.size = Pt(12); p.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
        elif "|" in line and "@" in line:
            p = doc.add_paragraph(line); p.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
        elif "|" in line:
            p = doc.add_paragraph(); p.paragraph_format.space_before = Pt(6); run = p.add_run(line); run.bold = True
        elif line.startswith('-') or line.startswith('•'):
            doc.add_paragraph(line.replace('-', '').replace('•', '').strip(), style='List Bullet')
        else:
            doc.add_paragraph(line)
    buffer = io.BytesIO(); doc.save(buffer); buffer.seek(0)
    return buffer

# ==========================================
# 6. SESSION STATE INITIALIZATION
# ==========================================
if 'step' not in st.session_state: st.session_state.step = 1
if 'cv_data' not in st.session_state: st.session_state.cv_data = {}

# Initialize Structured Lists if not present
if 'education_entries' not in st.session_state.cv_data:
    st.session_state.cv_data['education_entries'] = [{'uni': '', 'col': '', 'deg': '', 'year': ''}] # Start with 1 empty
if 'project_entries' not in st.session_state.cv_data:
    st.session_state.cv_data['project_entries'] = []
if 'cert_entries' not in st.session_state.cv_data:
    st.session_state.cv_data['cert_entries'] = []
if 'vol_entries' not in st.session_state.cv_data:
    st.session_state.cv_data['vol_entries'] = []

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

# --- STEP 1: PERSONAL INFO & EDUCATION ---
if st.session_state.step == 1:
    st.header("1️⃣ Personal Info & Education")
    
    with st.expander("📄 Auto-Fill from Old CV"):
        f = st.file_uploader("PDF/Word", type=['pdf', 'docx'])
        if f and st.button("Extract Data"):
            with st.spinner("Processing..."):
                try:
                    text = extract_text_from_pdf(f) if f.name.endswith('.pdf') else extract_text_from_docx(f)
                    data = parse_resume_with_ai(text)
                    if data: 
                        st.session_state.cv_data.update(data)
                        # We don't auto-fill complex lists in this simple version to avoid breaking structure
                        st.success("Basic info extracted! Please fill Education manually.")
                        st.rerun()
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
        
        # --- DYNAMIC EDUCATION SECTION ---
        st.markdown("### 🎓 Education")
        # Logic to add/remove entries needs to happen outside form or via session state manipulation
        # Since we are inside a form, we iterate what we have. Adding/Removing requires button outside form normally, 
        # or we use a clever rerun trick. For simplicity, we keep buttons outside form or use form_submit to update.
        # Let's keep input inside form, but add/remove buttons ABOVE the form or make form submit handle navigation only.
        
        # ACTUALLY: To make dynamic buttons work nicely, it's better NOT to put them inside a huge single form.
        # Let's use separate forms or just inputs for better interactivity.
        
    # Moving Education OUT of the main form to allow dynamic Add/Remove
    for i, entry in enumerate(st.session_state.cv_data['education_entries']):
        with st.container(border=True):
            cols = st.columns([3, 3, 3, 2, 1])
            with cols[0]: entry['uni'] = st.text_input(f"University #{i+1}", entry['uni'], key=f"uni_{i}")
            with cols[1]: entry['col'] = st.text_input(f"College #{i+1}", entry['col'], key=f"col_{i}")
            with cols[2]: entry['deg'] = st.text_input(f"Degree #{i+1}", entry['deg'], key=f"deg_{i}")
            with cols[3]: entry['year'] = st.text_input(f"Year #{i+1}", entry['year'], key=f"year_{i}")
            with cols[4]: 
                st.write("") # Spacer
                st.write("") 
                if st.button("🗑️", key=f"del_edu_{i}"):
                    st.session_state.cv_data['education_entries'].pop(i)
                    st.rerun()

    if st.button("➕ Add Education"):
        st.session_state.cv_data['education_entries'].append({'uni': '', 'col': '', 'deg': '', 'year': ''})
        st.rerun()

    st.markdown("---")
    if st.button("Next Step ➡️"):
        # Save simple fields manually since we removed the big form
        st.session_state.cv_data.update({
            'name':name, 'email':email, 'phone':phone, 'linkedin':linkedin, 'city':city, 
            'portfolio':portfolio, 'github':github, 'target_title':target_title
        })
        if name and target_title: next_step(); st.rerun()
        else: st.warning("Name & Job Title required!")

# --- STEP 2: SKILLS ---
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

# --- STEP 3: EXPERIENCE ---
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
        exp = st.text_area("Experience:", st.session_state.cv_data.get('raw_experience', ''), height=200)
        c1, c2 = st.columns([1, 5])
        with c1: 
            if st.form_submit_button("Back"): prev_step(); st.rerun()
        with c2:
            if st.form_submit_button("Next ➡️"): st.session_state.cv_data['raw_experience'] = exp; next_step(); st.rerun()

# --- STEP 4: PROJECTS & EXTRAS (STRUCTURED) ---
elif st.session_state.step == 4:
    st.header("4️⃣ Projects & Extras")
    
    t1, t2, t3 = st.tabs(["Projects", "Certifications", "Volunteering"])
    
    # 1. PROJECTS TAB
    with t1:
        st.info("Add your technical or personal projects.")
        for i, proj in enumerate(st.session_state.cv_data['project_entries']):
            with st.container(border=True):
                c1, c2 = st.columns([1, 1])
                with c1: proj['title'] = st.text_input(f"Project Title #{i+1}", proj.get('title',''), key=f"pj_t_{i}")
                with c2: proj['link'] = st.text_input(f"Link (GitHub/Demo)", proj.get('link',''), key=f"pj_l_{i}")
                proj['desc'] = st.text_area(f"Description #{i+1}", proj.get('desc',''), key=f"pj_d_{i}")
                if st.button("🗑️ Remove Project", key=f"del_pj_{i}"):
                    st.session_state.cv_data['project_entries'].pop(i)
                    st.rerun()
        
        if st.button("➕ Add Project"):
            st.session_state.cv_data['project_entries'].append({'title': '', 'link': '', 'desc': ''})
            st.rerun()

    # 2. CERTIFICATIONS TAB
    with t2:
        for i, cert in enumerate(st.session_state.cv_data['cert_entries']):
            with st.container(border=True):
                c1, c2, c3 = st.columns([4, 4, 1])
                with c1: cert['title'] = st.text_input(f"Certificate Name #{i+1}", cert.get('title',''), key=f"ct_t_{i}")
                with c2: cert['auth'] = st.text_input(f"Issuer/Organization", cert.get('auth',''), key=f"ct_a_{i}")
                with c3: 
                    st.write("")
                    if st.button("🗑️", key=f"del_ct_{i}"):
                        st.session_state.cv_data['cert_entries'].pop(i)
                        st.rerun()
        if st.button("➕ Add Certificate"):
            st.session_state.cv_data['cert_entries'].append({'title': '', 'auth': ''})
            st.rerun()

    # 3. VOLUNTEERING TAB
    with t3:
        for i, vol in enumerate(st.session_state.cv_data['vol_entries']):
            with st.container(border=True):
                vol['role'] = st.text_input(f"Role #{i+1}", vol.get('role',''), key=f"vl_r_{i}")
                vol['org'] = st.text_input(f"Organization", vol.get('org',''), key=f"vl_o_{i}")
                vol['desc'] = st.text_area(f"Description", vol.get('desc',''), key=f"vl_d_{i}")
                if st.button("🗑️ Remove", key=f"del_vl_{i}"):
                    st.session_state.cv_data['vol_entries'].pop(i)
                    st.rerun()
        if st.button("➕ Add Volunteering"):
            st.session_state.cv_data['vol_entries'].append({'role': '', 'org': '', 'desc': ''})
            st.rerun()

    st.markdown("---")
    c_back, c_next = st.columns([1, 5])
    if c_back.button("Back"): prev_step(); st.rerun()
    if c_next.button("Next Step ➡️"): next_step(); st.rerun()

# --- STEP 5: TARGET JOB ---
elif st.session_state.step == 5:
    st.header("5️⃣ Target Job")
    with st.form("s5"):
        jd = st.text_area("Job Description", st.session_state.cv_data.get('target_job', ''))
        c1, c2 = st.columns([1, 5])
        with c1: 
            if st.form_submit_button("Back"): prev_step(); st.rerun()
        with c2:
            if st.form_submit_button("Generate CV 🚀"): st.session_state.cv_data['target_job'] = jd; next_step(); st.rerun()

# --- STEP 6: RESULT ---
elif st.session_state.step == 6:
    st.balloons(); st.success("CV Ready!")
    
    raw_name = st.session_state.cv_data.get('name', 'User')
    safe_name = "".join([c if c.isalnum() or c==" " else "_" for c in raw_name]).strip().replace(" ", "_") or "CV"
    
    t1, t2, t3 = st.tabs(["Resume", "Cover Letter", "ATS Score"])
    jd = st.session_state.cv_data.get('target_job', '')
    
    with t1:
        if not st.session_state.final_cv:
            with st.spinner("Formatting..."):
                # 1. Contact
                info = [st.session_state.cv_data[k] for k in ['phone', 'city', 'email', 'linkedin', 'github', 'portfolio'] if st.session_state.cv_data.get(k)]
                c_line = " | ".join(info)
                
                # 2. Construct Education Block from List
                edu_lines = []
                for item in st.session_state.cv_data['education_entries']:
                    if item['uni'] or item['col']:
                        line = f"- {item['deg']}, {item['col']}, {item['uni']}"
                        if item['year']: line += f" | {item['year']}"
                        edu_lines.append(line)
                edu_block = "EDUCATION\n" + "\n".join(edu_lines) if edu_lines else ""

                # 3. Construct Projects Block
                proj_lines = []
                for p in st.session_state.cv_data['project_entries']:
                    if p['title']:
                        # Format: Title | Link -> Description
                        header = p['title']
                        if p['link']: header += f" | {p['link']}"
                        proj_lines.append(f"**{header}**\n{p['desc']}")
                extras = ""
                if proj_lines: extras += "PROJECTS\n" + "\n\n".join(proj_lines) + "\n"

                # 4. Construct Certs
                cert_lines = []
                for c in st.session_state.cv_data['cert_entries']:
                    if c['title']: cert_lines.append(f"- {c['title']} | {c['auth']}")
                if cert_lines: extras += "\nCERTIFICATIONS\n" + "\n".join(cert_lines) + "\n"

                # 5. Construct Volunteering
                vol_lines = []
                for v in st.session_state.cv_data['vol_entries']:
                    if v['role']: vol_lines.append(f"**{v['role']} | {v['org']}**\n{v['desc']}")
                if vol_lines: extras += "\nVOLUNTEERING\n" + "\n".join(vol_lines) + "\n"
                
                langs = ""
                if st.session_state.cv_data.get('languages'): langs = f"LANGUAGES ({st.session_state.cv_data['languages']})"

                prompt = f"""
                Act as a Resume Expert. Rewrite in Professional ENGLISH.
                RULES:
                1. Translate Arabic to English.
                2. Do not invent data.
                3. Clean Text (No Markdown Bold). No Numbered Sections.
                
                HEADER: {st.session_state.cv_data['name'].upper()} \n {c_line}
                SUMMARY (Target: {st.session_state.cv_data['target_title']})
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
        if st.button("Generate Letter"):
            with st.spinner("..."):
                st.session_state.cover_letter = safe_generate(f"Write English Cover Letter for {st.session_state.cv_data['name']}, Role: {st.session_state.cv_data['target_title']}")
                st.rerun()
        if st.session_state.cover_letter:
            st.text_area("Letter", st.session_state.cover_letter)
            st.download_button("Download", create_docx(st.session_state.cover_letter), "Cover.docx")

    with t3:
        if st.button("ATS Check"):
            if not jd: st.warning("No Job Description found!")
            else:
                with st.spinner("Analyzing..."):
                    ats_res = safe_generate(f"Analyze CV against JD:\n\nCV:{st.session_state.final_cv}\n\nJD:{jd}\n\nOutput: Score/100, Missing Keywords, Tips.")
                    st.session_state.ats_analysis = ats_res
                    st.rerun()
        if st.session_state.ats_analysis: st.info("ATS Result:"); st.write(st.session_state.ats_analysis)

    st.markdown("---")
    if st.button("Start Over"):
        st.session_state.step = 1; st.session_state.cv_data = {}; st.session_state.final_cv = ""; st.rerun()
