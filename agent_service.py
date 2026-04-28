"""
agent_service.py
================
Importable resume-generation agent service.
Wraps linkedin_agent.py logic into a callable function with log callbacks.
"""

import os
import re
import json
import pandas as pd
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_community.document_loaders import TextLoader
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document
from langchain_core.runnables import RunnableParallel, RunnableLambda
from dotenv import load_dotenv
from utils.resume_filler_modular2 import fill_resume

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ── Prompt templates ──────────────────────────────────────────────────────

PROJECTS_PROMPT = PromptTemplate(
    template="""You are a resume optimization assistant.

Job Description:
{job_description}

Relevant Projects:
{retrieved_projects}

Rewrite the projects to align strongly with the job description.
Use keywords from job description naturally.

IMPORTANT: Respond ONLY with a valid JSON array, no extra text, no markdown.
Each item must have exactly these keys:
[
  {{
    "title": "Project Name",
    "description": "What was built and achieved. Go in depth about the project and use keywords from job description.",
    "tech": "comma-separated technologies",
    "year": "2024"
  }}
]""",
    input_variables=["job_description", "retrieved_projects"],
)

ABOUT_PROMPT = PromptTemplate(
    template="""You are a resume optimization assistant.

Job Description:
{job_description}

Relevant About:
{retrieved_About}

Rewrite the About Section optimized according to the job requirement.
Add keywords from job description to increase the similarity of resume
with job description.

IMPORTANT: Respond ONLY with a valid JSON array, no extra text, no markdown.
Each item must have exactly these keys:
[
  {{
    "About": "About Section"
  }}
]""",
    input_variables=["job_description", "retrieved_About"],
)


def _parse_json(llm_output: str):
    """Strip markdown fences and parse JSON."""
    cleaned = re.sub(r"```(?:json)?", "", llm_output).strip().strip("`").strip()
    return json.loads(cleaned)


def run_agent(csv_path, log_callback=None, output_dir=None):
    """
    Generate tailored resumes for every job in *csv_path*.

    Parameters
    ----------
    csv_path     : str – path to the scraped-jobs CSV
    log_callback : callable(str) – receives log messages
    output_dir   : str – folder for generated PDFs (default: <project>/output)

    Returns
    -------
    list[str] – filenames of generated PDFs
    """
    if output_dir is None:
        output_dir = os.path.join(BASE_DIR, "output")
    os.makedirs(output_dir, exist_ok=True)

    def log(msg):
        if log_callback:
            log_callback(str(msg))

    log("🚀 Initializing AI Resume Agent...")

    # ── LLM / embeddings ──────────────────────────────────────────────────
    llm = ChatOpenAI(model="gpt-4.1-mini")
    embedding = OpenAIEmbeddings()
    parser = StrOutputParser()

    # ── Vector stores ─────────────────────────────────────────────────────
    vs_projects = Chroma(
        embedding_function=embedding,
        persist_directory=os.path.join(BASE_DIR, "my_chroma_db"),
        collection_name="projects",
    )
    vs_about = Chroma(
        embedding_function=embedding,
        persist_directory=os.path.join(BASE_DIR, "my_chroma_db"),
        collection_name="About",
    )

    # ── Retrievers ────────────────────────────────────────────────────────
    retriever_projects = vs_projects.as_retriever(
        search_type="similarity", search_kwargs={"k": 4}
    )
    retriever_about = vs_about.as_retriever(
        search_type="similarity", search_kwargs={"k": 1}
    )

    # ── LangChain pipelines ───────────────────────────────────────────────
    project_pipeline = (
        RunnableLambda(lambda x: {
            "job_description": x["job_description"],
            "retrieved_projects": x["retrieved_projects"],
        })
        | PROJECTS_PROMPT
        | llm
        | parser
    )
    about_pipeline = (
        RunnableLambda(lambda x: {
            "job_description": x["job_description"],
            "retrieved_About": x["retrieved_About"],
        })
        | ABOUT_PROMPT
        | llm
        | parser
    )
    chain = RunnableParallel(
        project_output=project_pipeline,
        About_output=about_pipeline,
    )

    # ── Read CSV ──────────────────────────────────────────────────────────
    log(f"📂 Reading CSV: {os.path.basename(csv_path)}")
    df = pd.read_csv(csv_path)
    log(f"📊 Found {len(df)} jobs to process")

    input_pdf = os.path.join(BASE_DIR, "resume(3.0).pdf")
    if not os.path.exists(input_pdf):
        log("⚠️ Base resume PDF not found – trying resume(2.0).pdf")
        input_pdf = os.path.join(BASE_DIR, "resume(2.0).pdf")

    generated_pdfs = []

    for idx, row in df.iterrows():
        job_description = str(row.get("job_description", ""))
        job_url = str(row.get("job_url", ""))

        if not job_description or job_description == "nan":
            log(f"  ⚠️ Row {idx+1}: empty description — skipping")
            continue

        match = re.search(r"/jobs/view/(\d+)/", job_url)
        if not match:
            log(f"  ⚠️ Row {idx+1}: could not extract job ID — skipping")
            continue

        job_id = match.group(1)
        log(f"\n{'='*55}")
        log(f"  📝 Processing job {idx+1}/{len(df)}:  ID {job_id}")
        log(
            f"  📌 {row.get('job_title', 'N/A')} "
            f"@ {row.get('company_name', 'N/A')}"
        )

        try:
            # retrieve context
            docs_p = retriever_projects.invoke(job_description)
            text_projects = "\n\n".join(d.page_content for d in docs_p)

            docs_a = retriever_about.invoke(job_description)
            text_about = "\n\n".join(d.page_content for d in docs_a)

            log("  🤖 Running AI optimization...")

            output = chain.invoke({
                "job_description": job_description,
                "retrieved_projects": text_projects,
                "retrieved_About": text_about,
            })

            projects = _parse_json(output["project_output"])
            about = _parse_json(output["About_output"])[0]["About"]

            pdf_name = f"{job_id}.pdf"
            pdf_path = os.path.join(output_dir, pdf_name)

            fill_resume(
                input_pdf=input_pdf,
                output_pdf=pdf_path,
                projects=projects,
                about=about,
            )

            generated_pdfs.append(pdf_name)
            df.loc[idx, "resume_updated"] = pdf_name
            log(f"  ✅ Generated resume: {pdf_name}")

        except Exception as e:
            log(f"  ❌ Error processing job {job_id}: {e}")
            continue

    # ── Save updated CSV ──────────────────────────────────────────────────
    updated_csv = os.path.join(output_dir, "Final_Resume_update.csv")
    df.to_csv(updated_csv, index=False)
    log(f"\n📁 Updated CSV saved → Final_Resume_update.csv")
    log(f"🏁 Done! Generated {len(generated_pdfs)} resume(s).")

    return generated_pdfs
