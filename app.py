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
from streamlit_mic_recorder import mic_recorder

# --- 1. إعدادات الصفحة ---
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
    2. **كسلان تكتب؟** استخدم "الفويس نوت" في خطوة الخبرة واحكي شغلك بصوتك.
    3. **مش عارف تعبر؟** استخدم زرار "اقتراحات" واحنا هنكتبلك مهام احترافية.
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

# التحقق من وجود المفتاح
if not api_key:
    st.warning("⚠️ يرجى إدخال مفتاح التشغيل في القائمة الجانبية.")
    st.stop()

client = Groq(api_key=api_key)
MODEL_NAME = "llama-3.3-70b-versatile"

# --- 3. دوال الذكاء الاصطناعي ومعالجة الملفات ---

def transcribe_audio(audio_bytes):
    """تحويل الصوت لنص باستخدام Groq Whisper"""
    try:
        audio_file = io.BytesIO(audio_bytes)
        audio_file.name = "recording.webm" # اسم وهمي عشان الـ API يقبله
        
        transcription = client.audio.transcriptions.create(
            file=(audio_file.name, audio_file.read()),
            model="whisper-large-v3",
            response_format="text",
            language="en" # ممكن تخليه "ar" لو عايز تتكلم عربي وهو يكتبه عربي
        )
        return transcription
    except Exception as e:
        return f"Error: {str(e)}"

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
    """استخراج البيانات من النص الخام"""
    prompt = f"""
    Extract the following details from this resume text:
    Name, Email, Phone, City, LinkedIn, Target Job Title (infer if not present), 
    Skills (as a comma-separated string), and Professional Experience (raw text).
    
    Resume Text:
    {text[:4000]} 
    
    Output ONLY a valid JSON object with these keys: 
    "name", "email", "phone", "city", "linkedin", "target_title", "skills", "experience".
    """
    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        return json.loads(completion.choices[0].message.content)
    except Exception as e:
        return None

def get_job_suggestions(role_title):
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

# --- 4. دوال إنشاء ملفات Word و PDF ---

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
            pdf.set_font("Arial", size=10); clean_line = line.replace('-', '').strip()
            pdf.multi_cell(0, 5, chr(149) + " " + clean_line); pdf.ln(2)
            
        else:
            pdf.set_font("Arial", size=10); pdf.multi_cell(0, 5, line); pdf.ln(1)
            
    buffer = io.BytesIO()
    pdf_output = pdf.output(dest='S').encode('latin-1')
    buffer.write(pdf_output)
    buffer.seek(0)
    return buffer

# --- 5. إدارة حالة التطبيق (Session State) ---
if 'step' not in st.session_state: st.session_state.step = 1
if 'cv_data' not in st.session_state: st.session_state.cv_data = {}
for key in ['final_cv', 'cover_letter', 'ats_analysis']:
    if key not in st.session_state: st.session_state[key] = ""

if st.session_state.step > 6: st.session_state.step = 1; st.rerun()

def next_step(): st.session_state.step += 1
def prev_step(): st.session_state.step -= 1

# --- 6. واجهة المستخدم (التطبيق الرئيسي) ---
st.title("🚀 Elite CV Builder")
st.markdown("##### مساعدك الذكي لعمل CV احترافي يتقبل في الشركات")

if st.session_state.step < 6: st.progress(st.session_state.step / 6)

# ==========================================
# STEP 1: Personal Info & Resume Parsing
# ==========================================
if st.session_state.step == 1:
    st.header("1️⃣ البيانات الشخصية")
    
    # --- ميزة رفع الـ CV ---
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
                        
                        parsed_data = parse_resume_with_ai(text)
                        
                        if parsed_data:
                            st.session_state.cv_data.update(parsed_data)
                            st.success("تم سحب البيانات بنجاح! كمل مراجعة تحت.")
                            st.rerun()
                        else:
                            st.error("مش قادر أقرأ الملف، حاول تملأ البيانات يدوي.")
                    except Exception as e:
                        st.error(f"حصل خطأ: {e}")
    # -----------------------

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
        target_title = st.text_input("🔴 المسمى الوظيفي المستهدف (مهم جداً)", st.session_state.cv_data.get('target_title', ''))
        
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

# ==========================================
# STEP 2: Skills
# ==========================================
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

# ==========================================
# STEP 3: Experience (WITH VOICE & AI SUGGESTIONS)
# ==========================================
elif st.session_state.step == 3:
    st.header("3️⃣ خبرة الشغل")
    
    st.info("💡 عندك 3 طرق للكتابة: اكتب بإيدك، أو سجل فويس، أو خلي الذكاء الاصطناعي يقترح عليك.")

    # --- أدوات المساعدة (فويس + اقتراحات) ---
    with st.container():
        c_voice, c_suggest = st.columns(2)
        
        # 1. Voice Input Section
        with c_voice:
            st.write("🎙️ **سجل فويس (إنجليزي أو عربي):**")
            audio = mic_recorder(
                start_prompt="بدء التسجيل ⏺️",
                stop_prompt="إنهاء ⏹️", 
                key='recorder',
                format="webm"
            )
            
            if audio:
                with st.spinner("جاري تحويل الصوت لنص..."):
                    transcribed_text = transcribe_audio(audio['bytes'])
                    current_text = st.session_state.cv_data.get('raw_experience', '')
                    # إضافة النص الجديد للنص القديم
                    st.session_state.cv_data['raw_experience'] = current_text + "\n" + transcribed_text
                    st.success("تمت إضافة الكلام!")
                    st.rerun()

        # 2. AI Suggestions Section
        with c_suggest:
            st.write("✨ **أو خليه يقترح عليك:**")
            role_name = st.session_state.cv_data.get('target_title', '')
            if st.button("اقتراح مهام لـ " + (role_name if role_name else "وظيفتي")):
                if role_name:
                    with st.spinner("الذكاء الاصطناعي بيفكر..."):
                        sugg = get_job_suggestions(role_name)
                        current_text = st.session_state.cv_data.get('raw_experience', '')
                        st.session_state.cv_data['raw_experience'] = current_text + "\n" + sugg
                        st.success("تم إضافة الاقتراحات!")
                        st.rerun()
                else:
                    st.warning("ارجع للخطوة 1 واكتب المسمى الوظيفي!")
    # ----------------------------------------

    with st.form("step3"):
        st.write("👇 الخبرة (تقدر تعدل الكلام هنا):")
        raw_experience = st.text_area("Experience:", st.session_state.cv_data.get('raw_experience', ''), height=250)
        
        col1, col2 = st.columns([1, 5])
        with col1: 
            if st.form_submit_button("رجوع"): prev_step(); st.rerun()
        with col2:
            if st.form_submit_button("التالي ⬅️"):
                st.session_state.cv_data['raw_experience'] = raw_experience
                next_step(); st.rerun()

# ==========================================
# STEP 4: Projects & Extras
# ==========================================
elif st.session_state.step == 4:
    st.header("4️⃣ مشاريع وكورسات")
    with st.form("step4"):
        projects = st.text_area("مشاريع:", st.session_state.cv_data.get('projects', ''))
        certs = st.text_area("شهادات وكورسات:", st.session_state.cv_data.get('certs', ''))
        volunteering = st.text_area("عمل تطوعي:", st.session_state.cv_data.get('volunteering', ''))
        
        col1, col2 = st.columns([1, 5])
        with col1: 
            if st.form_submit_button("رجوع"): prev_step(); st.rerun()
        with col2:
            if st.form_submit_button("التالي ⬅️"):
                st.session_state.cv_data.update({'projects':projects, 'certs':certs, 'volunteering':volunteering})
                next_step(); st.rerun()

# ==========================================
# STEP 5: Target Job (For ATS)
# ==========================================
elif st.session_state.step == 5:
    st.header("5️⃣ تفاصيل الوظيفة (عشان الـ ATS)")
    with st.form("step5"):
        st.write("لو معاك إعلان الوظيفة، انسخه هنا عشان الـ CV يطلع مظبوط عليه.")
        target_job = st.text_area("Job Description (اختياري):", st.session_state.cv_data.get('target_job', ''), height=150)
        
        col1, col2 = st.columns([1, 5])
        with col1: 
            if st.form_submit_button("رجوع"): prev_step(); st.rerun()
        with col2:
            if st.form_submit_button("🚀 اصنع الـ CV"):
                st.session_state.cv_data['target_job'] = target_job
                next_step(); st.rerun()

# ==========================================
# STEP 6: Result Dashboard
# ==========================================
elif st.session_state.step == 6:
    st.balloons()
    st.success("🎉 مبروك! الـ CV بتاعك جاهز.")
    
    safe_name = re.sub(r'[^a-zA-Z0-9]', '_', st.session_state.cv_data.get('name', 'User'))
    file_name = f"{safe_name}_CV.pdf"
    word_file_name = f"{safe_name}_CV.docx"

    t1, t2, t3 = st.tabs(["📄 الـ CV الجاهز", "✉️ Cover Letter", "📊 تقييم ATS"])
    jd = st.session_state.cv_data.get('target_job', '')

    # --- TAB 1: CV Preview & Download ---
    with t1:
        if not st.session_state.final_cv:
            with st.spinner("⏳ جاري كتابة الـ CV..."):
                contact_parts = [st.session_state.cv_data[k] for k in ['phone', 'city', 'email', 'linkedin', 'github', 'portfolio'] if st.session_state.cv_data.get(k)]
                contact_line = " | ".join(contact_parts)

                optional_prompt = ""
                if st.session_state.cv_data.get('projects'): optional_prompt += f"\n5. **PROJECTS**\n   - {st.session_state.cv_data['projects']}"
                if st.session_state.cv_data.get('certs'): optional_prompt += f"\n6. **CERTIFICATIONS**\n   - {st.session_state.cv_data['certs']}"
                if st.session_state.cv_data.get('volunteering'): optional_prompt += f"\n7. **VOLUNTEERING**\n   - {st.session_state.cv_data['volunteering']}"

                prompt_cv = f"""
                Act as a Senior Resume Expert. Write a professional CV based on this data.
                **RULES:**
                1. Clean Text Only (No markdown bold like **).
                2. No Section Numbers.
                3. Metrics: Add numbers to experience bullets.
                4. Dates: Use "Mon YYYY" format.
                5. Language: English Only (Translate if input is Arabic).
                
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
                
                generated_text = safe_generate(prompt_cv)
                if "Error:" in generated_text:
                    st.error(generated_text)
                else:
                    st.session_state.final_cv = generated_text
                    st.rerun()

        if st.session_state.final_cv:
            st.text_area("محرر النصوص (عدل هنا قبل التحميل)", st.session_state.final_cv, height=500)
            
            c1, c2, c3 = st.columns(3)
            c1.download_button("⬇️ تحميل PDF", create_pdf(st.session_state.final_cv), file_name, "application/pdf")
            c2.download_button("⬇️ تحميل Word", create_docx(st.session_state.final_cv), word_file_name, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
            if c3.button("🔄 إعادة صياغة"):
                st.session_state.final_cv = ""
                st.rerun()
    
    # --- TAB 2: Cover Letter ---
    with t2:
        if st.button("✨ اكتب لي Cover Letter"):
            with st.spinner("جاري الكتابة..."):
                prompt_cl = f"Write a professional cover letter for {st.session_state.cv_data['name']} applying for {st.session_state.cv_data['target_title']}."
                st.session_state.cover_letter = safe_generate(prompt_cl)
                st.rerun()

        if st.session_state.cover_letter:
            st.text_area("Cover Letter", st.session_state.cover_letter, height=400)
            st.download_button("⬇️ تحميل Letter", create_docx(st.session_state.cover_letter), "Cover_Letter.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    
    # --- TAB 3: ATS Check ---
    with t3:
        if st.button("🔍 افحص الـ CV (ATS Check)"):
            with st.spinner("جاري التحليل..."):
                context = jd if jd else st.session_state.cv_data['target_title']
                prompt_ats = f"Analyze this CV against this Job/Role: {context}. Give a Score out of 100, list Missing Keywords, and suggest Improvements."
                st.session_state.ats_analysis = safe_generate(prompt_ats)
                st.rerun()

        if st.session_state.ats_analysis:
            st.write(st.session_state.ats_analysis)

    st.markdown("---")
    if st.button("البدء من جديد"):
        st.session_state.step = 1; st.session_state.cv_data = {}; st.session_state.final_cv = ""; st.rerun()
