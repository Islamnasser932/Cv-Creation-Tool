import streamlit as st
import os
from groq import Groq
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
from fpdf import FPDF
import io
import re

# 1. إعدادات الصفحة
st.set_page_config(
    page_title="Elite CV Builder",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. القائمة الجانبية (شرح بسيط وتخطي التعقيدات التقنية) ---
api_key = None
using_shared_key = False

with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3135/3135715.png", width=50)
    st.title("💡 دليلك السريع")
    
    st.markdown("""
    **إزاي تعمل CV احترافي في دقيقتين؟**
    
    1. **بياناتك:** اكتب اسمك ورقمك وإيميلك.
    2. **مهاراتك:** اكتب كل الحاجات اللي بتعرف تعملها (حتى لو بالعربي).
    3. **خبرتك:** احكي اللي كنت بتعمله في شغلك القديم (بالعامية عادي)، وإحنا هنحوله لإنجليزي احترافي.
    4. **الوظيفة المستهدفة:** عشان الـ CV يطلع مظبوط على "الفرازة".
    5. **تحميل:** نزل الـ CV وروح قدم!
    """)
    
    st.divider()
    
    # --- إخفاء التعقيدات التقنية (Hybrid Logic Hidden) ---
    with st.expander("⚙️ إعدادات متقدمة (لو معاك مفتاح خاص)"):
        st.write("لو الموقع تقيل، ممكن تستخدم مفتاحك الخاص من Groq.")
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

    st.markdown("---")
    st.caption("تم التطوير بواسطة: [إسلام ناصر](https://www.linkedin.com/in/islam-nasser1/)")

# التأكد من الاتصال
if not api_key:
    st.warning("⚠️ يرجى إدخال مفتاح التشغيل في القائمة الجانبية.")
    st.stop()

client = Groq(api_key=api_key)
MODEL_NAME = "llama-3.3-70b-versatile"

# --- Helper Functions (نفس دوال التنسيق السابقة) ---
def create_docx(text):
    doc = Document()
    sections = doc.sections
    for section in sections:
        section.top_margin = Inches(0.5)
        section.bottom_margin = Inches(0.5)
        section.left_margin = Inches(0.5)
        section.right_margin = Inches(0.5)

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
    buffer = io.BytesIO(); pdf_output = pdf.output(dest='S').encode('latin-1'); buffer.write(pdf_output); buffer.seek(0)
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

# --- واجهة المستخدم (بالعربي البسيط) ---
st.title("🚀 Elite CV Builder")
st.markdown("##### مساعدك الذكي لعمل CV احترافي يتقبل في الشركات")

if st.session_state.step < 6: st.progress(st.session_state.step / 6)

# STEP 1: Personal Info
if st.session_state.step == 1:
    st.header("1️⃣ البيانات الشخصية")
    st.info("🔒 بياناتك بتتمسح أول ما تقفل الموقع، مش بنحتفظ بأي حاجة.")
    with st.form("step1"):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("الاسم بالكامل (إنجليزي)", st.session_state.cv_data.get('name', ''))
            email = st.text_input("البريد الإلكتروني (Email)", st.session_state.cv_data.get('email', ''))
            city = st.text_input("المدينة والدولة (Cairo, Egypt)", st.session_state.cv_data.get('city', ''))
            portfolio = st.text_input("لينك معرض الأعمال (Portfolio) - اختياري", st.session_state.cv_data.get('portfolio', ''))
        with col2:
            phone = st.text_input("رقم الموبايل", st.session_state.cv_data.get('phone', ''))
            linkedin = st.text_input("لينك بروفايل LinkedIn", st.session_state.cv_data.get('linkedin', ''))
            github = st.text_input("لينك GitHub (للمبرمجين فقط)", st.session_state.cv_data.get('github', ''))
        
        st.markdown("---")
        st.write("🔴 **أهم سؤال:** إيه المسمى الوظيفي اللي بتقدم عليه؟")
        target_title = st.text_input("مثال: Accountant, Sales Manager, Engineer", st.session_state.cv_data.get('target_title', ''))
        
        st.markdown("**🎓 التعليم:**")
        c1, c2, c3 = st.columns(3)
        with c1: university = st.text_input("اسم الجامعة", st.session_state.cv_data.get('university', ''))
        with c2: degree = st.text_input("الدرجة (بكالوريوس/ماجستير)", st.session_state.cv_data.get('degree', ''))
        with c3: grad_year = st.text_input("سنة التخرج", st.session_state.cv_data.get('grad_year', ''))

        if st.form_submit_button("التالي ⬅️"):
            if name and email and target_title:
                st.session_state.cv_data.update({
                    'name':name, 'email':email, 'phone':phone, 'linkedin':linkedin, 'city':city, 
                    'portfolio':portfolio, 'github':github, 
                    'target_title':target_title, 'university':university, 'degree':degree, 'grad_year':grad_year
                })
                next_step(); st.rerun()
            else: st.warning("⚠️ لازم تكتب الاسم، الإيميل، والمسمى الوظيفي!")

# STEP 2: Skills
elif st.session_state.step == 2:
    st.header("2️⃣ المهارات (Skills)")
    with st.form("step2"):
        st.markdown("""
        **اكتب كل المهارات اللي عندك.**
        - مش لازم ترتيب.
        - ممكن تكتب أسماء برامج (Word, Excel, Photoshop).
        - ممكن تكتب مهارات شخصية (Communication, Leadership).
        """)
        skills = st.text_area("اكتب مهاراتك هنا:", st.session_state.cv_data.get('skills', ''), height=150)
        languages = st.text_input("اللغات (مثال: Arabic Native, English Fluent)", st.session_state.cv_data.get('languages', ''))
        
        col1, col2 = st.columns([1, 5])
        with col1: 
            if st.form_submit_button("رجوع"): prev_step(); st.rerun()
        with col2:
            if st.form_submit_button("التالي ⬅️"):
                st.session_state.cv_data.update({'skills':skills, 'languages':languages})
                next_step(); st.rerun()

# STEP 3: Experience
elif st.session_state.step == 3:
    st.header("3️⃣ خبرة الشغل")
    with st.form("step3"):
        st.info("💡 **نصيحة:** اكتب اللي كنت بتعمله بالعامية أو برؤوس أقلام، والذكاء الاصطناعي هيحوله لكلام احترافي جداً!")
        st.markdown("**مثال للكتابة:**\n* اشتغلت محاسب في شركة كذا من 2020 لـ 2022.\n* كنت مسؤول عن حسابات العملاء.\n* قللت المصاريف بنسبة 10%.")
        
        raw_experience = st.text_area("احكي عن شغلك القديم هنا:", st.session_state.cv_data.get('raw_experience', ''), height=200)
        
        col1, col2 = st.columns([1, 5])
        with col1: 
            if st.form_submit_button("رجوع"): prev_step(); st.rerun()
        with col2:
            if st.form_submit_button("التالي ⬅️"):
                st.session_state.cv_data['raw_experience'] = raw_experience
                next_step(); st.rerun()

# STEP 4: Projects & Extras
elif st.session_state.step == 4:
    st.header("4️⃣ مشاريع وكورسات")
    with st.form("step4"):
        st.write("لو عندك مشاريع تخرج، كورسات خدتها، أو عمل تطوعي اكتبه هنا. لو مفيش سيبهم فاضيين.")
        projects = st.text_area("مشاريع قمت بيها:", st.session_state.cv_data.get('projects', ''))
        certs = st.text_area("شهادات وكورسات:", st.session_state.cv_data.get('certs', ''))
        volunteering = st.text_area("عمل تطوعي:", st.session_state.cv_data.get('volunteering', ''))
        
        col1, col2 = st.columns([1, 5])
        with col1: 
            if st.form_submit_button("رجوع"): prev_step(); st.rerun()
        with col2:
            if st.form_submit_button("التالي ⬅️"):
                st.session_state.cv_data.update({'projects':projects, 'certs':certs, 'volunteering':volunteering})
                next_step(); st.rerun()

# STEP 5: Target Job (Updated Guide)
elif st.session_state.step == 5:
    st.header("5️⃣ تفاصيل الوظيفة (عشان الـ ATS)")
    
    with st.expander("❓ يعني إيه وصف وظيفي (Job Description)؟", expanded=True):
        st.write("""
        ده "الإعلان" اللي الشركة منزلاه. بيكون مكتوب فيه هما طالبين إيه بالظبط.
        
        **ليه تحطه هنا؟**
        عشان الذكاء الاصطناعي يقرا الإعلان، وياخد منه "الكلمات السرية" (Keywords) ويحطها في الـ CV بتاعك. 
        ده بيخليك تعدي من نظام الفلترة الأوتوماتيكي (ATS) وتوصل للإنترفيو.
        """)
        
    with st.form("step5"):
        target_job = st.text_area("انسخ إعلان الوظيفة وحطه هنا (لو مش معاك سيبه فاضي):", st.session_state.cv_data.get('target_job', ''), height=150)
        
        col1, col2 = st.columns([1, 5])
        with col1: 
            if st.form_submit_button("رجوع"): prev_step(); st.rerun()
        with col2:
            label = "🚀 ابدأ صنع الـ CV" if target_job else "🚀 ابدأ (بدون وصف وظيفي)"
            if st.form_submit_button(label):
                st.session_state.cv_data['target_job'] = target_job
                next_step(); st.rerun()

# STEP 6: Result Dashboard
elif st.session_state.step == 6:
    st.balloons()
    st.success("🎉 مبروك! الـ CV بتاعك جاهز.")
    
    safe_name = re.sub(r'[^a-zA-Z0-9]', '_', st.session_state.cv_data.get('name', 'User'))
    file_name = f"{safe_name}_CV.pdf"
    word_file_name = f"{safe_name}_CV.docx"

    t1, t2, t3 = st.tabs(["📄 الـ CV الجاهز", "✉️ جواب التقديم (Cover Letter)", "📊 تقييم الـ CV"])
    jd = st.session_state.cv_data.get('target_job', '')

    with t1:
        if not st.session_state.final_cv:
            with st.spinner("⏳ جاري كتابة الـ CV... (ممكن ياخد ثواني)"):
                
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
                3. Metrics: Add numbers (%, $) to experience bullets where possible.
                4. Dates: Use "Mon YYYY" format.
                5. Language: English Only (Translate if input is Arabic).
                
                **HEADER:**
                {st.session_state.cv_data['name'].upper()}
                {contact_line}
                
                **SECTIONS:**
                PROFESSIONAL SUMMARY (3 lines, tailored to {st.session_state.cv_data['target_title']})
                
                TECHNICAL SKILLS (Grouped: Languages, Tools, etc. Include ALL user skills: {st.session_state.cv_data['skills']})
                
                PROFESSIONAL EXPERIENCE (Role | Company | Dates)
                User Data (Translate to Professional English): {st.session_state.cv_data['raw_experience']}
                
                EDUCATION ({st.session_state.cv_data['degree']}, {st.session_state.cv_data['university']}, {st.session_state.cv_data['grad_year']})
                
                {optional_prompt}
                
                LANGUAGES ({st.session_state.cv_data['languages']})
                """
                
                generated_text = safe_generate(prompt_cv)
                
                if "Error:" in generated_text:
                    st.error(f"⚠️ حصل مشكلة: {generated_text}")
                    if using_shared_key:
                        st.info("💡 السيرفر المجاني مشغول. جرب تاني كمان شوية أو استخدم مفتاحك الخاص.")
                else:
                    st.session_state.final_cv = generated_text
                    st.rerun()

        if st.session_state.final_cv:
            st.text_area("محرر النصوص (تقدر تعدل أي كلمة هنا قبل التحميل)", st.session_state.final_cv, height=500)
            
            c1, c2, c3 = st.columns(3)
            c1.download_button("⬇️ تحميل PDF", create_pdf(st.session_state.final_cv), file_name, "application/pdf")
            c2.download_button("⬇️ تحميل Word", create_docx(st.session_state.final_cv), word_file_name, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
            if c3.button("🔄 إعادة صياغة"):
                st.session_state.final_cv = ""
                st.rerun()
        
    with t2:
        if st.button("✨ اكتب لي Cover Letter"):
            with st.spinner("جاري الكتابة..."):
                prompt_cl = f"Write a professional cover letter for {st.session_state.cv_data['name']} applying for {st.session_state.cv_data['target_title']}. Use a professional yet passionate tone."
                st.session_state.cover_letter = safe_generate(prompt_cl)
                st.rerun()

        if st.session_state.cover_letter:
            st.text_area("Cover Letter", st.session_state.cover_letter, height=400)
            st.download_button("⬇️ تحميل Letter", create_docx(st.session_state.cover_letter), "Cover_Letter.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    
    with t3:
        if st.button("🔍 قيّم الـ CV (ATS Check)"):
            with st.spinner("جاري تحليل الـ CV..."):
                if jd:
                    prompt_ats = f"Analyze this CV against this Job Description: {jd}. Give a Score out of 100, list Missing Keywords, and suggest Improvements."
                else:
                    prompt_ats = f"Analyze this CV for a {st.session_state.cv_data['target_title']} role. Give a generic score and suggest general improvements."
                
                st.session_state.ats_analysis = safe_generate(prompt_ats)
                st.rerun()

        if st.session_state.ats_analysis:
            st.write(st.session_state.ats_analysis)

    st.markdown("---")
    if st.button("البدء من جديد"):
        st.session_state.step = 1; st.session_state.cv_data = {}; st.session_state.final_cv = ""; st.rerun()
