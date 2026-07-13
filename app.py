import streamlit as st
import chromadb
import pathlib
import tempfile
from docx import Document
from openai import OpenAI

# 1. Page config
st.set_page_config(page_title="AI Recruitment Agent", page_icon="🧑‍💼", layout="wide")
st.title("🧑‍💼 AI Recruitment Agent")
st.markdown("Upload resumes and find the best candidate for your job description.")

# 2. OpenRouter client
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key="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"
)

# 3. ChromaDB
chroma_client = chromadb.PersistentClient(path="./resumes_db")
col = chroma_client.get_or_create_collection("resumes")

# 4. DOCX okuma
def read_docx(path):
    doc = Document(path)
    return "\n".join([p.text for p in doc.paragraphs if p.text.strip()])

# 5. Sidebar - Resume Upload
with st.sidebar:
    st.header("📁 Upload Resumes")
    uploaded_files = st.file_uploader(
        "Upload DOCX resumes",
        type=["docx"],
        accept_multiple_files=True
    )

    if uploaded_files:
        if st.button("📥 Index Resumes", use_container_width=True):
            with st.spinner("Indexing resumes..."):
                for f in uploaded_files:
                    try:
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
                            tmp.write(f.read())
                            tmp_path = tmp.name
                        text = read_docx(tmp_path)
                        if text:
                            # Zaten varsa ekleme
                            existing = col.get(ids=[f.name])
                            if not existing["ids"]:
                                col.add(
                                    ids=[f.name],
                                    documents=[text],
                                    metadatas=[{"src": f.name}]
                                )
                    except Exception as e:
                        st.error(f"Error: {f.name} - {e}")

            st.success(f"✅ {col.count()} resumes indexed!")

    st.divider()
    st.metric("📄 Total Resumes", col.count())

# 6. Ana alan - Job Description
st.header("📋 Job Description")
job_description = st.text_area(
    "Enter the job description",
    height=200,
    placeholder="""We are looking for a Senior Data Scientist with:
- 5+ years of experience in machine learning
- Strong Python and SQL skills
- Experience with NLP and deep learning
- Team leadership experience"""
)

n_candidates = st.slider("Number of candidates to compare", 1, 5, 3)

# 7. Analiz butonu
if st.button("🔍 Find Best Candidate", type="primary", use_container_width=True):
    if not job_description.strip():
        st.warning("Please enter a job description.")
    elif col.count() == 0:
        st.warning("Please upload and index resumes first.")
    else:
        with st.spinner("Analyzing candidates..."):
            results = col.query(query_texts=[job_description], n_results=min(n_candidates, col.count()))

            candidates = ""
            for i, (doc, meta) in enumerate(zip(results["documents"][0], results["metadatas"][0])):
                candidates += f"\n--- Candidate {i+1}: {meta['src']} ---\n{doc[:1000]}\n"

            prompt = f"""
You are a senior HR recruitment specialist.
Analyze the candidates below and match them to the job description.
Format your response as:

## Job Summary
## Top Candidate
- Name/File
- Key Matching Skills
- Experience Match
- Strengths
- Weaknesses

## Ranking (1st, 2nd, 3rd)
## Final Recommendation

Job Description:
{job_description}

Candidates:
{candidates}
"""

            r = client.chat.completions.create(
                model="openrouter/free",
                messages=[{"role": "user", "content": prompt}]
            )

            result = r.choices[0].message.content

        st.divider()
        st.header("🏆 Analysis Result")
        st.markdown(result)

        # İndirilebilir rapor
        st.download_button(
            label="📥 Download Report",
            data=result,
            file_name="recruitment_report.md",
            mime="text/markdown"
        )
