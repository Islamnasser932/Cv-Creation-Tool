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
from pypdf import PdfReader # مكتبة جديدة لقراءة الـ PDF

# 1. إعدادات الصفحة
st.set_page_config(
    page_title="Elite CV Builder",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. إعدادات الـ API والقائمة الجانبية ---
api_key = None
using_shared_key = False

with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3135/3135715.png", width=50)
    st.title("💡 دليلك السريع")
    
    st.markdown("""
    **إزاي تعمل CV احترافي؟**
    1. **عندك CV قديم؟** ارفعه في الخطوة الأولى واحنا هنسحب البيانات منه!
    2. **مش عارف تكتب إيه في الخبرة؟** استخدم زرار "اقترح مهام" واحنا هنكتبلك كلام زي الفل.
    3. **في الآخر:** نزل الـ CV وقدم وانت مطمن.
    """)
    
    st.divider()
    
    with st.expander("⚙️ إعدادات متقدمة"):
        use_own_key = st.checkbox("استخدم مفتاحي الخاص", value=False)
        if use_own_key:
            user_input_key = st.text_input("Groq API Key", type="password")
            if user_input_key:
                api_key = user_input_key
                using_shared_key = False
        else:
            if "GROQ_API_KEY" in st.secrets:
                api_key = st.secrets["GROQ_API_KEY"]
                using_shared_key = True
                st.success("✅ متصل بالسيرفر المجاني")
            else:
                st.warning("⚠️ مفيش مفتاح متسجل")

if not api_key:
    st.warning("⚠️ يرجى إدخال مفتاح التشغيل.")
    st.stop()

client = Groq(api_key=api_key)
MODEL_NAME = "llama-3.3-70b-versatile"

# --- دوال المساعدة (Helpers) ---

def extract_text_from_pdf(file):
    reader = PdfReader(file)
    text = ""
    for page in reader.pages:
        text += page.extract_text()
    return text

def extract_text_from_docx(file):
    doc = Document(file)
    return "\n".join([para.text for para in doc.paragraphs])

def parse_resume_with_ai(text):
    """وظيفة لاستخراج البيانات من النص باستخدام الذكاء الاصطناعي"""
    prompt = f"""
    Extract the following details from this resume text:
    Name, Email, Phone, City, LinkedIn, Target Job Title (infer if not present), 
    Skills (as a comma-separated string), and Professional Experience (raw text).
    
    Resume Text:
    {text[:4000]} 
    
    Output ONLY a valid JSON object with these keys: 
    "name", "email", "phone", "city", "linkedin", "target_title", "skills", "experience".
    Do NOT add any markdown formatting like ```json. Just the raw JSON string.
    """
    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            response_format={"type": "json_object"} # ميزة جديدة لضمان خروج JSON
        )
        return json.loads(completion.choices[0].message.content)
    except Exception as e:
        return None

def get_job_suggestions(role_title):
    """وظيفة لاقتراح مهام وظيفية"""
    prompt = f"""
    Give me 5 professional, metric-driven bullet points for a "{role_title}" resume.
    Write them in English. Start with strong action verbs.
    Output ONLY the bullet points.
    """
    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        return completion.choices[0].message.content
    except:
        return "Error generating suggestions."

# --- دوال إنشاء الملفات (PDF/Docx) ---
# (نفس الدوال السابقة بدون تغيير لعدم الإطالة، تأكد إنك ناسخها)
def create_docx(text):
    doc = Document()
    sections = doc.sections
    for section in sections:
        section.top_margin = Inches(0.5); section.bottom_margin = Inches(0.5); section.left_margin = Inches(0.5); section.right_margin = Inches(0.5)
    text = text.replace("**", "").replace("##", "")
    for line in text.split('\n'):
        line = line.strip()
        if not line: continue
        line_no_num = re.sub(r'^\d+\.\s*', '', line)
        if line_no_num.isupper() and len(line_no_num) < 60 and "|" not in line:
            p = doc.add_paragraph(); p.paragraph_format.space_before = Pt(12); p.paragraph_format.space_after = Pt(6)
            run = p.add_run(line_no_num); run.bold = True; run.font.size = Pt(12)
            p.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER if "NAME" not in line else WD_PARAGRAPH_ALIGNMENT.LEFT
        elif "|" in line and "@" in line:
            p = doc.add_paragraph(line); p.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER; p.paragraph_format.space_after = Pt(12)
        elif "|" in line and "@" not in line:
            p = doc.add_paragraph(); p.paragraph_format.space_before = Pt(8); run = p.add_run(line); run.bold = True; run.font.size = Pt(11); p.alignment = WD_PARAGRAPH_ALIGNMENT.LEFT
        elif line.startswith('-') or line.startswith('•'):
            clean_line = line.replace('•', '').replace('-', '').strip(); p = doc.add_paragraph(clean_line, style='List Bullet'); p.paragraph_format.space_after = Pt(2)
        else:
            p = doc.add_paragraph(line); p.paragraph_format.space_after = Pt(2)
    buffer = io.BytesIO(); doc.save(buffer); buffer.seek(0)
    return buffer

def create_pdf(text):
    class PDF(FPDF):
        def header(self): pass
        def footer(self): pass
    pdf = PDF(); pdf.add_page(); pdf.set_auto_page_break(auto=True, margin=15)
    text = text.replace("**", "").replace("##", "")
    replacements = {u'\u2013': '-', u'\u2014': '-', u'\u2018': "'", u'\u2019': "'", u'\u201c': '"', u'\u201d': '"', '•': '-', '–': '-'}
    for k, v in replacements.items(): text = text.replace(k, v)
    try: text = text.encode('latin-1', 'replace').decode('latin-1')
    except: text = text 
    for line in text.split('\n'):
        line = line.strip()
        if not line: continue
        if "___" in line: continue
        line_no_num = re.sub(r'^\d+\.\s*', '', line)
        if line_no_num.isupper() and len(line_no_num) < 60 and "|" not in line:
            pdf.ln(6); pdf.set_font("Arial", 'B', size=12); pdf.cell(0, 6, line_no_num, ln=True, align='C')
            x = pdf.get_x(); y = pdf.get_y(); pdf.line(x + 10, y, 200, y); pdf.ln(4)
        elif "|" in line and "@" in line:
            pdf.set_font("Arial", size=9); pdf.multi_cell(0, 5, line, align='C'); pdf.ln(4)
        elif "|" in line and "@" not in line:
            pdf.ln(4); pdf.set_font("Arial", 'B', size=10); pdf.cell(0, 6, line, ln=True, align='L'); pdf.ln(2)
        elif line.startswith('-'):
            pdf.set_font("Arial", size=10); clean_line = line.replace('-', '').strip(); pdf.multi_cell(0, 5, chr(149) + " " + clean_line); pdf.ln(2)
        else:
            pdf.set_font("Arial", size=10); pdf.multi_cell(0, 5, line); pdf.ln(1)
    buffer = io.BytesIO(); pdf_output = pdf.output(dest='S').encode('latin-1'); buffer.write(pdf_output); buffer.seek(0)
    return buffer

def safe_generate(prompt_text):
    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "You are a Senior HR Recruiter. Output strict, clean text."},
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

# --- التطبيق ---
st.title("🚀 Elite CV Builder")

if st.session_state.step < 6: st.progress(st.session_state.step / 6)

# STEP 1: Personal Info & Resume Parsing
if st.session_state.step == 1:
    st.header("1️⃣ البيانات الشخصية")
    
    # --- الميزة الجديدة رقم 1: رفع الـ CV ---
    with st.expander("📄 كسلان تكتب؟ ارفع الـ CV القديم هنا (اختياري)", expanded=False):
        uploaded_file = st.file_uploader("ارفع ملف PDF أو Word", type=['pdf', 'docx', 'doc'])
        if uploaded_file is not None:
            if st.button("🧠 استخراج البيانات بالذكاء الاصطناعي"):
                with st.spinner("جاري قراءة الملف..."):
                    try:
                        if uploaded_file.name.endswith('.pdf'):
                            text = extract_text_from_pdf(uploaded_file)
                        else:
                            text = extract_text_from_docx(uploaded_file)
                        
                        # استخراج البيانات
                        parsed_data = parse_resume_with_ai(text)
                        
                        if parsed_data:
                            st.session_state.cv_data.update(parsed_data)
                            st.success("تم سحب البيانات بنجاح! كمل مراجعة تحت.")
                            st.rerun()
                        else:
                            st.error("مش قادر أقرأ الملف، حاول تملأ البيانات يدوي.")
                    except Exception as e:
                        st.error(f"حصل خطأ: {e}")
    # ---------------------------------------

    st.info("أو املأ البيانات يدوي:")
    with st.form("step1"):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("الاسم بالكامل", st.session_state.cv_data.get('name', ''))
            email = st.text_input("البريد الإلكتروني", st.session_state.cv_data.get('email', ''))
            city = st.text_input("المدينة", st.session_state.cv_data.get('city', ''))
            portfolio = st.text_input("Portfolio Link", st.session_state.cv_data.get('portfolio', ''))
        with col2:
            phone = st.text_input("رقم الموبايل", st.session_state.cv_data.get('phone', ''))
            linkedin = st.text_input("LinkedIn", st.session_state.cv_data.get('linkedin', ''))
            github = st.text_input("GitHub", st.session_state.cv_data.get('github', ''))
        
        st.markdown("---")
        target_title = st.text_input("🔴 المسمى الوظيفي المستهدف (Target Job Title)", st.session_state.cv_data.get('target_title', ''))
        
        c1, c2, c3 = st.columns(3)
        with c1: university = st.text_input("الجامعة", st.session_state.cv_data.get('university', ''))
        with c2: degree = st.text_input("الدرجة", st.session_state.cv_data.get('degree', ''))
        with c3: grad_year = st.text_input("سنة التخرج", st.session_state.cv_data.get('grad_year', ''))

        if st.form_submit_button("التالي ⬅️"):
            if name and target_title:
                st.session_state.cv_data.update({
                    'name':name, 'email':email, 'phone':phone, 'linkedin':linkedin, 'city':city, 
                    'portfolio':portfolio, 'github':github, 
                    'target_title':target_title, 'university':university, 'degree':degree, 'grad_year':grad_year
                })
                next_step(); st.rerun()
            else: st.warning("الاسم والمسمى الوظيفي مطلوبين!")

# STEP 2: Skills
elif st.session_state.step == 2:
    st.header("2️⃣ المهارات (Skills)")
    with st.form("step2"):
        st.write("اكتب مهاراتك هنا:")
        skills = st.text_area("Skills", st.session_state.cv_data.get('skills', ''), height=150)
        languages = st.text_input("اللغات", st.session_state.cv_data.get('languages', ''))
        
        col1, col2 = st.columns([1, 5])
        with col1: 
            if st.form_submit_button("رجوع"): prev_step(); st.rerun()
        with col2:
            if st.form_submit_button("التالي ⬅️"):
                st.session_state.cv_data.update({'skills':skills, 'languages':languages})
                next_step(); st.rerun()

# STEP 3: Experience & Suggestions
elif st.session_state.step == 3:
    st.header("3️⃣ خبرة الشغل")
    
    # --- الميزة الجديدة رقم 2: اقتراحات الذكاء الاصطناعي ---
    st.info("💡 مش عارف تكتب إيه؟ اكتب اسم الوظيفة تحت ودوس 'غششني'")
    c_s1, c_s2 = st.columns([3, 1])
    with c_s1:
        suggestion_role = st.text_input("اكتب مسمى وظيفي للاقتراح (مثلاً: Sales Manager)", label_visibility='collapsed', placeholder="اكتب اسم الوظيفة هنا...")
    with c_s2:
        if st.button("✨ غششني مهام"):
            if suggestion_role:
                with st.spinner("بيفكر..."):
                    suggestions = get_job_suggestions(suggestion_role)
                    st.success("خد الكلام ده كوبي وحطه في الخبرة وعدل عليه:")
                    st.code(suggestions, language='text')
            else:
                st.warning("اكتب اسم الوظيفة الأول!")
    # ----------------------------------------------------

    with st.form("step3"):
        st.write("خبرتك الحالية:")
        raw_experience = st.text_area("Paste your experience here:", st.session_state.cv_data.get('raw_experience', ''), height=200)
        
        col1, col2 = st.columns([1, 5])
        with col1: 
            if st.form_submit_button("رجوع"): prev_step(); st.rerun()
        with col2:
            if st.form_submit_button("التالي ⬅️"):
                st.session_state.cv_data['raw_experience'] = raw_experience
                next_step(); st.rerun()

# STEP 4: Projects
elif st.session_state.step == 4:
    st.header("4️⃣ مشاريع وكورسات")
    with st.form("step4"):
        projects = st.text_area("مشاريع:", st.session_state.cv_data.get('projects', ''))
        certs = st.text_area("شهادات:", st.session_state.cv_data.get('certs', ''))
        volunteering = st.text_area("تطوع:", st.session_state.cv_data.get('volunteering', ''))
        
        col1, col2 = st.columns([1, 5])
        with col1: 
            if st.form_submit_button("رجوع"): prev_step(); st.rerun()
        with col2:
            if st.form_submit_button("التالي ⬅️"):
                st.session_state.cv_data.update({'projects':projects, 'certs':certs, 'volunteering':volunteering})
                next_step(); st.rerun()

# STEP 5: Target Job
elif st.session_state.step == 5:
    st.header("5️⃣ تفاصيل الوظيفة (عشان الـ ATS)")
    with st.form("step5"):
        target_job = st.text_area("إعلان الوظيفة (اختياري):", st.session_state.cv_data.get('target_job', ''), height=150)
        
        col1, col2 = st.columns([1, 5])
        with col1: 
            if st.form_submit_button("رجوع"): prev_step(); st.rerun()
        with col2:
            if st.form_submit_button("🚀 اصنع الـ CV"):
                st.session_state.cv_data['target_job'] = target_job
                next_step(); st.rerun()

# STEP 6: Result
elif st.session_state.step == 6:
    st.balloons()
    st.success("🎉 الـ CV جاهز!")
    
    safe_name = re.sub(r'[^a-zA-Z0-9]', '_', st.session_state.cv_data.get('name', 'User'))
    file_name = f"{safe_name}_CV.pdf"
    word_file_name = f"{safe_name}_CV.docx"

    t1, t2, t3 = st.tabs(["📄 الـ CV", "✉️ Cover Letter", "📊 تقييم ATS"])

    with t1:
        if not st.session_state.final_cv:
            with st.spinner("جاري الكتابة..."):
                contact_parts = [st.session_state.cv_data[k] for k in ['phone', 'city', 'email', 'linkedin', 'github', 'portfolio'] if st.session_state.cv_data.get(k)]
                contact_line = " | ".join(contact_parts)
                
                optional_prompt = ""
                if st.session_state.cv_data.get('projects'): optional_prompt += f"\n5. **PROJECTS**\n   - {st.session_state.cv_data['projects']}"
                if st.session_state.cv_data.get('certs'): optional_prompt += f"\n6. **CERTIFICATIONS**\n   - {st.session_state.cv_data['certs']}"
                
                prompt_cv = f"""
                Act as a Senior Resume Expert. Write a professional CV.
                **RULES:** Clean Text. No markdown bold. No Numbered Sections. Use "Mon YYYY" format. English Only.
                
                **HEADER:**
                {st.session_state.cv_data['name'].upper()}
                {contact_line}
                
                **SECTIONS:**
                PROFESSIONAL SUMMARY (Tailored to {st.session_state.cv_data['target_title']})
                TECHNICAL SKILLS ({st.session_state.cv_data['skills']})
                PROFESSIONAL EXPERIENCE (Role | Company | Dates)
                User Data: {st.session_state.cv_data['raw_experience']}
                EDUCATION ({st.session_state.cv_data['degree']}, {st.session_state.cv_data['university']}, {st.session_state.cv_data['grad_year']})
                {optional_prompt}
                LANGUAGES ({st.session_state.cv_data['languages']})
                """
                st.session_state.final_cv = safe_generate(prompt_cv)
                st.rerun()

        if st.session_state.final_cv:
            st.text_area("محرر", st.session_state.final_cv, height=500)
            c1, c2, c3 = st.columns(3)
            c1.download_button("PDF", create_pdf(st.session_state.final_cv), file_name, "application/pdf")
            c2.download_button("Word", create_docx(st.session_state.final_cv), word_file_name, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
            if c3.button("🔄 إعادة"): st.session_state.final_cv = ""; st.rerun()

    with t2:
        if st.button("✨ Cover Letter"):
            prompt_cl = f"Write a cover letter for {st.session_state.cv_data['name']} for {st.session_state.cv_data['target_title']}."
            st.session_state.cover_letter = safe_generate(prompt_cl)
            st.rerun()
        if st.session_state.cover_letter:
            st.text_area("Cover Letter", st.session_state.cover_letter)
            st.download_button("Download Letter", create_docx(st.session_state.cover_letter), "Cover.docx")

    with t3:
        if st.button("🔍 ATS Check"):
            prompt_ats = f"Analyze CV for {st.session_state.cv_data['target_title']} role. Give Score /100 and Feedback."
            st.session_state.ats_analysis = safe_generate(prompt_ats)
            st.rerun()
        if st.session_state.ats_analysis: st.write(st.session_state.ats_analysis)

    st.markdown("---")
    if st.button("البدء من جديد"):
        st.session_state.step = 1; st.session_state.cv_data = {}; st.session_state.final_cv = ""; st.rerun()
