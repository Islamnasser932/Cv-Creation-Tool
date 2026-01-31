import streamlit as st
import os
from groq import Groq
from docx import Document
from docx.shared import Pt, Inches, RGBColor
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
    page_icon="👔",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================
# 2. FONT SETUP
# ==========================================
FONT_URL = "https://github.com/google/fonts/raw/main/ofl/amiri/Amiri-Regular.ttf"
FONT_BOLD_URL = "https://github.com/google/fonts/raw/main/ofl/amiri/Amiri-Bold.ttf"
FONT_PATH = "Amiri-Regular.ttf"
FONT_BOLD_PATH = "Amiri-Bold.ttf"

def check_and_download_font():
    if not os.path.exists(FONT_PATH) or os.path.getsize(FONT_PATH) < 1000:
        try: requests.get(FONT_URL, timeout=10).content; open(FONT_PATH, "wb").write(requests.get(FONT_URL).content)
        except: pass
    if not os.path.exists(FONT_BOLD_PATH) or os.path.getsize(FONT_BOLD_PATH) < 1000:
        try: requests.get(FONT_BOLD_URL, timeout=10).content; open(FONT_BOLD_PATH, "wb").write(requests.get(FONT_BOLD_URL).content)
        except: pass

check_and_download_font()

# ==========================================
# 3. API & SIDEBAR
# ==========================================
api_key = None
if "GROQ_API_KEY" in st.secrets: api_key = st.secrets["GROQ_API_KEY"]

with st.sidebar:
    st.title("🎨 Elite CV Builder")
    use_own_key = st.checkbox("Use my own API Key")
    if use_own_key: api_key = st.text_input("Groq API Key", type="password")

if not api_key: st.stop()
client = Groq(api_key=api_key)
MODEL_NAME = "llama-3.3-70b-versatile"

# ==========================================
# 4. HELPER FUNCTIONS
# ==========================================
def process_text_for_pdf(text):
    if not text: return ""
    try: return get_display(arabic_reshaper.reshape(text))
    except: return text

def extract_text_from_pdf(file):
    reader = PdfReader(file); text = "" 
    for page in reader.pages: text += page.extract_text()
    return text

def extract_text_from_docx(file):
    doc = Document(file); return "\n".join([para.text for para in doc.paragraphs])

def parse_resume_with_ai(text):
    prompt = f"Extract details. Source: {text[:6000]}. Output JSON: name, email, phone, city, linkedin, portfolio, github, target_title, skills, experience, education_list."
    try:
        completion = client.chat.completions.create(model=MODEL_NAME, messages=[{"role": "user", "content": prompt}], response_format={"type": "json_object"})
        return json.loads(completion.choices[0].message.content)
    except: return None

def get_job_suggestions(role_title):
    try:
        completion = client.chat.completions.create(model=MODEL_NAME, messages=[{"role": "user", "content": f"Give 5 English resume bullet points for {role_title} with metrics."}])
        return completion.choices[0].message.content
    except: return "Error."

def safe_generate(prompt_text):
    try:
        completion = client.chat.completions.create(model=MODEL_NAME, messages=[{"role": "system", "content": "You are a Resume Expert."}, {"role": "user", "content": prompt_text}], temperature=0.3)
        return completion.choices[0].message.content
    except Exception as e: return f"Error: {str(e)}"

# ==========================================
# 5. PROFESSIONAL PDF GENERATOR (MANUAL HEADER)
# ==========================================
class ProfessionalPDF(FPDF):
    def header(self): pass 

def create_pdf(text, user_data):
    # Setup PDF
    pdf = ProfessionalPDF(orientation='P', unit='mm', format='A4')
    pdf.set_margins(left=10, top=10, right=10) 
    pdf.add_page()
    
    try:
        pdf.add_font('Amiri', '', FONT_PATH, uni=True)
        pdf.add_font('Amiri-Bold', '', FONT_BOLD_PATH, uni=True)
    except:
        pdf.add_font('Arial', '', '', uni=True)

    # ---------------------------------------------------------
    # 1. PYTHON-GENERATED HEADER (100% Control - No AI Errors)
    # ---------------------------------------------------------
    # Name
    pdf.set_font('Amiri-Bold', '', 24)
    pdf.set_text_color(0, 0, 0)
    name = user_data.get('name', 'Name')
    pdf.cell(0, 10, process_text_for_pdf(name), ln=True, align='C')
    
    # Contact Info Construction
    parts = []
    if user_data.get('phone'): parts.append(user_data['phone'])
    if user_data.get('city'): parts.append(user_data['city'])
    if user_data.get('email'): parts.append(user_data['email'])
    if user_data.get('linkedin'): parts.append(user_data['linkedin'])
    if user_data.get('portfolio'): parts.append(user_data['portfolio'])
    if user_data.get('github'): parts.append(user_data['github'])
    
    contact_line = " | ".join(parts)
    
    pdf.set_font('Amiri', '', 9)
    pdf.set_text_color(0, 0, 0) # Black
    pdf.multi_cell(0, 5, process_text_for_pdf(contact_line), align='C')
    pdf.ln(3)
    
    # Line Separator
    pdf.set_draw_color(0, 0, 0)
    pdf.set_line_width(0.5)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(5)

    # ---------------------------------------------------------
    # 2. AI-GENERATED BODY (Parsed Line by Line)
    # ---------------------------------------------------------
    lines = text.split('\n')
    
    for line in lines: 
        line = line.strip()
        if not line: continue
        
        # Remove markdown bold if AI adds it
        clean_text = line.replace("**", "").replace("##", "")
        display_line = process_text_for_pdf(clean_text)
        
        # --- HEADERS (### Section) ---
        if "###" in line:
            pdf.ln(4)
            pdf.set_font('Amiri-Bold', '', 14)
            clean_header = line.replace("###", "").strip().upper()
            pdf.cell(0, 8, clean_header, ln=True, align='L')
            
            # Underline
            pdf.set_line_width(0.5) 
            pdf.line(10, pdf.get_y(), 200, pdf.get_y())
            pdf.set_line_width(0.2)
            pdf.ln(2)
            
        # --- SUB-HEADERS (Bold roles) ---
        # Detect lines that look like "Role | Company" or have specific keywords
        elif "|" in line and not line.startswith("-"):
            pdf.ln(1)
            pdf.set_font('Amiri-Bold', '', 11)
            pdf.cell(0, 5, display_line, ln=True)
            
        # --- BULLET POINTS (Experience/Projects) ---
        elif line.startswith("-") or line.startswith("•"):
            pdf.set_font('Amiri', '', 10)
            clean_bullet = line.replace("-", "").replace("•", "").strip()
            pdf.set_x(12) 
            pdf.multi_cell(188, 5, "• " + process_text_for_pdf(clean_bullet))
            
        # --- NORMAL TEXT (Summary/Skills) ---
        else:
            pdf.set_font('Amiri', '', 10)
            pdf.multi_cell(0, 5, display_line)
            pdf.ln(1)

    buffer = io.BytesIO()
    buffer.write(pdf.output(dest='S').encode("latin1"))
    buffer.seek(0)
    return buffer

def create_docx(text, user_data):
    doc = Document()
    style = doc.styles['Normal']; style.font.name = 'Arial'; style.font.size = Pt(10)
    
    # 1. Python Header
    head = doc.add_paragraph()
    head.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    run = head.add_run(user_data.get('name', ''))
    run.bold = True; run.font.size = Pt(22); run.font.color.rgb = RGBColor(0,0,0)
    
    # Contact
    parts = [user_data.get(k) for k in ['phone','city','email','linkedin','portfolio','github'] if user_data.get(k)]
    contact_p = doc.add_paragraph(" | ".join(parts))
    contact_p.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    contact_p.runs[0].font.size = Pt(9)

    # 2. Body
    lines = text.split('\n')
    for line in lines:
        line = line.strip(); 
        if not line: continue
        clean_text = line.replace("**", "").replace("##", "").replace("###", "").strip()
        
        if "###" in line:
            p = doc.add_paragraph(); p.paragraph_format.space_before = Pt(12)
            run = p.add_run(clean_text.upper()); run.bold = True; run.font.size = Pt(14)
        elif "|" in line and not line.startswith("-"):
            p = doc.add_paragraph(); p.paragraph_format.space_before = Pt(6)
            run = p.add_run(clean_text); run.bold = True
        elif line.startswith("-") or line.startswith("•"):
            doc.add_paragraph(clean_text.replace("-", "").replace("•", "").strip(), style='List Bullet')
        else:
            doc.add_paragraph(clean_text)
            
    buffer = io.BytesIO(); doc.save(buffer); buffer.seek(0)
    return buffer

# ==========================================
# 6. SESSION INIT
# ==========================================
if 'step' not in st.session_state: st.session_state.step = 1
if 'cv_data' not in st.session_state: st.session_state.cv_data = {}
if 'education_entries' not in st.session_state.cv_data: st.session_state.cv_data['education_entries'] = [{'uni': '', 'col': '', 'deg': '', 'year': ''}]
if 'project_entries' not in st.session_state.cv_data: st.session_state.cv_data['project_entries'] = []
if 'cert_entries' not in st.session_state.cv_data: st.session_state.cv_data['cert_entries'] = []
if 'vol_entries' not in st.session_state.cv_data: st.session_state.cv_data['vol_entries'] = []
for k in ['final_cv', 'cover_letter', 'ats_analysis']:
    if k not in st.session_state: st.session_state[k] = ""
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
    with st.form("s1"):
        c1, c2 = st.columns(2)
        with c1: 
            name = st.text_input("Name", st.session_state.cv_data.get('name', ''))
            email = st.text_input("Email", st.session_state.cv_data.get('email', ''))
            city = st.text_input("City", st.session_state.cv_data.get('city', ''))
            portfolio = st.text_input("Portfolio Link", st.session_state.cv_data.get('portfolio', ''))
        with c2: 
            phone = st.text_input("Phone", st.session_state.cv_data.get('phone', ''))
            linkedin = st.text_input("LinkedIn", st.session_state.cv_data.get('linkedin', ''))
            github = st.text_input("GitHub", st.session_state.cv_data.get('github', ''))
        
        st.markdown("---"); target_title = st.text_input("🔴 Target Job Title", st.session_state.cv_data.get('target_title', ''))
        st.write(""); submitted = st.form_submit_button("Save Info")
        if submitted: st.session_state.cv_data.update({'name':name, 'email':email, 'phone':phone, 'linkedin':linkedin, 'city':city, 'portfolio':portfolio, 'github':github, 'target_title':target_title})

    st.markdown("### 🎓 Education"); 
    for i, entry in enumerate(st.session_state.cv_data['education_entries']):
        with st.container(border=True):
            cols = st.columns([3, 3, 3, 2, 1])
            with cols[0]: entry['uni'] = st.text_input(f"University", entry.get('uni',''), key=f"uni_{i}")
            with cols[1]: entry['col'] = st.text_input(f"College/Faculty", entry.get('col',''), key=f"col_{i}")
            with cols[2]: entry['deg'] = st.text_input(f"Degree", entry.get('deg',''), key=f"deg_{i}")
            with cols[3]: entry['year'] = st.text_input(f"Year", entry.get('year',''), key=f"year_{i}")
            with cols[4]: st.write(""); 
            if st.button("🗑️", key=f"del_edu_{i}"): st.session_state.cv_data['education_entries'].pop(i); st.rerun()
    if st.button("➕ Add Education"): st.session_state.cv_data['education_entries'].append({'uni': '', 'col': '', 'deg': '', 'year': ''}); st.rerun()
    
    st.markdown("---")
    if st.button("Next Step ➡️"):
        if st.session_state.cv_data.get('name') and st.session_state.cv_data.get('target_title'): next_step(); st.rerun()
        else: st.warning("Name & Job Title required!")

# STEP 2
elif st.session_state.step == 2:
    st.header("2️⃣ Skills")
    with st.form("s2"):
        skills = st.text_area("Skills", st.session_state.cv_data.get('skills', ''))
        langs = st.text_input("Languages", st.session_state.cv_data.get('languages', ''))
        c1, c2 = st.columns([1, 5]); 
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
            with st.spinner("..."): sugg = get_job_suggestions(role); st.session_state.cv_data['raw_experience'] = st.session_state.cv_data.get('raw_experience', '') + "\n" + sugg; st.rerun()
    with st.form("s3"):
        exp = st.text_area("Experience:", st.session_state.cv_data.get('raw_experience', ''), height=200)
        c1, c2 = st.columns([1, 5]); 
        with c1: 
            if st.form_submit_button("Back"): prev_step(); st.rerun()
        with c2:
            if st.form_submit_button("Next ➡️"): st.session_state.cv_data['raw_experience'] = exp; next_step(); st.rerun()

# STEP 4
elif st.session_state.step == 4:
    st.header("4️⃣ Projects & Extras")
    t1, t2, t3 = st.tabs(["Projects", "Certifications", "Volunteering"])
    with t1:
        for i, proj in enumerate(st.session_state.cv_data['project_entries']):
            with st.container(border=True):
                c1, c2 = st.columns([1, 1])
                with c1: proj['title'] = st.text_input(f"Title #{i+1}", proj.get('title',''), key=f"pj_t_{i}")
                with c2: proj['link'] = st.text_input(f"Link", proj.get('link',''), key=f"pj_l_{i}")
                proj['desc'] = st.text_area(f"Description", proj.get('desc',''), key=f"pj_d_{i}")
                if st.button("🗑️", key=f"del_pj_{i}"): st.session_state.cv_data['project_entries'].pop(i); st.rerun()
        if st.button("➕ Add Project"): st.session_state.cv_data['project_entries'].append({'title': '', 'link': '', 'desc': ''}); st.rerun()
    with t2:
        for i, cert in enumerate(st.session_state.cv_data['cert_entries']):
            with st.container(border=True):
                c1, c2, c3 = st.columns([4, 4, 1])
                with c1: cert['title'] = st.text_input(f"Name #{i+1}", cert.get('title',''), key=f"ct_t_{i}")
                with c2: cert['auth'] = st.text_input(f"Issuer", cert.get('auth',''), key=f"ct_a_{i}")
                with c3: st.write(""); 
                if st.button("🗑️", key=f"del_ct_{i}"): st.session_state.cv_data['cert_entries'].pop(i); st.rerun()
        if st.button("➕ Add Certificate"): st.session_state.cv_data['cert_entries'].append({'title': '', 'auth': ''}); st.rerun()
    with t3:
        for i, vol in enumerate(st.session_state.cv_data['vol_entries']):
            with st.container(border=True):
                vol['role'] = st.text_input(f"Role #{i+1}", vol.get('role',''), key=f"vl_r_{i}")
                vol['org'] = st.text_input(f"Organization", vol.get('org',''), key=f"vl_o_{i}")
                vol['desc'] = st.text_area(f"Description", vol.get('desc',''), key=f"vl_d_{i}")
                if st.button("🗑️", key=f"del_vl_{i}"): st.session_state.cv_data['vol_entries'].pop(i); st.rerun()
        if st.button("➕ Add Volunteering"): st.session_state.cv_data['vol_entries'].append({'role': '', 'org': '', 'desc': ''}); st.rerun()
    st.markdown("---"); c_back, c_next = st.columns([1, 5])
    if c_back.button("Back"): prev_step(); st.rerun()
    if c_next.button("Next Step ➡️"): next_step(); st.rerun()

# STEP 5
elif st.session_state.step == 5:
    st.header("5️⃣ Target Job")
    with st.form("s5"):
        jd = st.text_area("Job Description", st.session_state.cv_data.get('target_job', ''))
        c1, c2 = st.columns([1, 5]); 
        with c1: 
            if st.form_submit_button("Back"): prev_step(); st.rerun()
        with c2:
            if st.form_submit_button("Generate CV 🚀"): st.session_state.cv_data['target_job'] = jd; next_step(); st.rerun()

# STEP 6
elif st.session_state.step == 6:
    st.success("✅ CV Generated Successfully")
    raw_name = st.session_state.cv_data.get('name', 'User')
    safe_name = "".join([c if c.isalnum() or c==" " else "_" for c in raw_name]).strip().replace(" ", "_") or "CV"
    t1, t2, t3 = st.tabs(["Resume", "Cover Letter", "ATS Score"])
    jd = st.session_state.cv_data.get('target_job', '')
    
    with t1:
        if not st.session_state.final_cv:
            with st.spinner("Compiling Resume..."):
                # Education Loop
                edu_lines = []
                for e in st.session_state.cv_data['education_entries']:
                    if e.get('uni') or e.get('col'):
                        parts = [x for x in [e.get('deg'), e.get('col'), e.get('uni')] if x]
                        line = ", ".join(parts)
                        if e.get('year'): line += f" | {e.get('year')}"
                        edu_lines.append(f"- {line}")
                edu_block = "### EDUCATION\n" + "\n".join(edu_lines) if edu_lines else ""

                # Projects
                proj_lines = []
                for p in st.session_state.cv_data['project_entries']:
                    if p.get('title'):
                        head = p['title']
                        if p.get('link'): head += f" | {p['link']}"
                        proj_lines.append(f"{head}\n- {p.get('desc','')}") # Force bullet for desc
                proj_block = "### PROJECTS\n" + "\n".join(proj_lines) + "\n" if proj_lines else ""

                # Certs & Vol
                cert_lines = [f"- {c['title']} | {c.get('auth','')}" for c in st.session_state.cv_data['cert_entries'] if c.get('title')]
                cert_block = "### CERTIFICATIONS\n" + "\n".join(cert_lines) + "\n" if cert_lines else ""
                vol_lines = [f"{v['role']} | {v.get('org','')}\n- {v.get('desc','')}" for v in st.session_state.cv_data['vol_entries'] if v.get('role')]
                vol_block = "### VOLUNTEERING\n" + "\n".join(vol_lines) + "\n" if vol_lines else ""
                
                # Fixed: Languages in one line
                langs = f"### LANGUAGES\n{st.session_state.cv_data['languages']}" if st.session_state.cv_data.get('languages') else ""

                # PROMPT FIX: Force Bullet Points & Clean Structure
                prompt = f"""
                Act as a Resume Expert. Rewrite in Professional ENGLISH.
                
                CRITICAL RULES:
                1. **NO HEADER:** Do NOT output name/contact info. Start directly with Professional Summary.
                2. **EXPERIENCE:** Convert ALL experience descriptions into **BULLET POINTS** (- ). Do NOT use paragraphs.
                3. **METRICS:** Add realistic numbers/percentages to every bullet point.
                4. **ORDER:** Sort Experience REVERSE CHRONOLOGICAL (Newest First).
                5. **FORMAT:** Use "### " for Section Headers.
                6. **SKILLS/LANGUAGES:** Keep them as a comma-separated list in one paragraph.
                
                DATA TO PROCESS:
                
                ### PROFESSIONAL SUMMARY
                (Summary for {st.session_state.cv_data['target_title']})
                
                ### TECHNICAL SKILLS
                {st.session_state.cv_data['skills']}
                
                ### EXPERIENCE
                {st.session_state.cv_data['raw_experience']}
                
                {edu_block}
                {proj_block}
                {cert_block}
                {vol_block}
                {langs}
                """
                res = safe_generate(prompt)
                if "Error" in res: st.error(res)
                else: st.session_state.final_cv = res; st.rerun()

        if st.session_state.final_cv:
            st.text_area("Editor", st.session_state.final_cv, height=500)
            c1, c2, c3 = st.columns(3)
            # Pass user_data to create_pdf for the manual header
            c1.download_button("PDF", create_pdf(st.session_state.final_cv, st.session_state.cv_data), f"{safe_name}.pdf", "application/pdf")
            c2.download_button("Word", create_docx(st.session_state.final_cv, st.session_state.cv_data), f"{safe_name}.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
            if c3.button("Reset"): st.session_state.final_cv=""; st.rerun()

    with t2:
        if st.button("Generate Letter"):
            with st.spinner("..."): st.session_state.cover_letter = safe_generate(f"Write English Cover Letter for {st.session_state.cv_data['name']}, Role: {st.session_state.cv_data['target_title']}")
            st.rerun()
        if st.session_state.cover_letter: st.text_area("Letter", st.session_state.cover_letter); st.download_button("Download", create_docx(st.session_state.cover_letter, st.session_state.cv_data), "Cover.docx")

    with t3:
        if st.button("ATS Check"):
            if not jd: st.warning("No Job Description found!")
            else:
                with st.spinner("Analyzing..."): ats_res = safe_generate(f"Analyze CV against JD:\n\nCV:{st.session_state.final_cv}\n\nJD:{jd}\n\nOutput: Score/100, Missing Keywords, Tips.")
                st.session_state.ats_analysis = ats_res; st.rerun()
        if st.session_state.ats_analysis: st.info("ATS Result:"); st.write(st.session_state.ats_analysis)

    st.markdown("---"); 
    if st.button("Start Over"): st.session_state.step = 1; st.session_state.cv_data = {}; st.session_state.final_cv = ""; st.rerun()
