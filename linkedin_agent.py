from langchain_openai import ChatOpenAI,OpenAIEmbeddings
from langchain.messages import HumanMessage , SystemMessage , ToolMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.document_loaders import BaseLoader
from langchain_community.document_loaders import TextLoader , CSVLoader ,json_loader,JSONLoader
from langchain_community.vectorstores import Chroma
from langchain_text_splitters import CharacterTextSplitter
from langchain_core.documents import Document
from dotenv import load_dotenv
import pandas as pd
from utils.resume_filler_modular2 import fill_resume
import json, re
from langchain_core.runnables import RunnableParallel , RunnableLambda


load_dotenv()

llm = ChatOpenAI(model="gpt-4.1-mini")

embedding=OpenAIEmbeddings()

vector_store=Chroma(
    embedding_function=embedding,
    persist_directory="my_chroma_db",
    collection_name="projects"

)

vector_store_2=Chroma(
    embedding_function=embedding,
    persist_directory="my_chroma_db",
    collection_name="About"
)

parser=StrOutputParser()

loader_projects = TextLoader(file_path=r"D:\LANGCHAIN\langchain_Resume_Builder\projects.text" , encoding="utf-8")

loader_About = TextLoader(file_path="D:\LANGCHAIN\langchain_Resume_Builder\About.text" , encoding="utf-8")

docs_projects=loader_projects.load()

docs_About=loader_About.load()

all_text_projects="\n\n".join([doc.page_content for doc in docs_projects])

all_text_About="\n\n".join([doc.page_content for doc in docs_About])

chunks_projects=all_text_projects.split("\n\n")

chunks_About=all_text_About.split("\n\n")

# print(chunks)



vector_docs_project= [Document(page_content=part) for part in chunks_projects ]


vector_docs_About= [Document(page_content=part) for part in chunks_About ]





# vector_store_2.add_documents(vector_docs_About)



data = vector_store._collection.get(include=["embeddings", "documents"])



prompt = PromptTemplate(template="""You are a resume optimization assistant.

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
    "description": "What was built and achieved This is the Part where u will go in depth about the project and use keywords from job description as described earlier.",
    "tech": "comma-separated technologies",
    "year": "2024"
  }}
]""",
input_variables=["job_description", "retrieved_projects"])


prompt2 =PromptTemplate(
    template="""You are a resume optimization assistant.

Job Description:
{job_description}

Relevant About:
{retrieved_About}

Rewrite the About Section that i am giving you but u need to make sure that optimized according to the job requirement u can add keywords given in job description to increase the similarity of resume with job description.

IMPORTANT: Respond ONLY with a valid JSON array, no extra text, no markdown.
Each item must have exactly these keys:
[
  {{
    "About": "About Section }} ]""" , input_variables= ["job_description" , "retrieved_About"]
)




def parse_projects(llm_output):
    cleaned = re.sub(r"```(?:json)?", "", llm_output).strip().strip("`").strip()
    return json.loads(cleaned)


df=pd.read_csv(r"D:\LANGCHAIN\langchain_Resume_Builder\dataset.csv")

retriver_projects = vector_store.as_retriever(
    search_type="similarity",
    search_kwargs={"k":4}
    
)

retriver_About=vector_store_2.as_retriever(
    search_type="similarity",
    search_kwargs={"k":1}

    
)

project_pipeline= RunnableLambda( lambda x :{ "job_description":x["job_description"] ,"retrieved_projects" :x["retrieved_projects"]}) | prompt | llm | parser

About_pipeline= RunnableLambda( lambda x :{ "job_description" :x["job_description"] ,"retrieved_About":x["retrieved_About"]}) | prompt2 | llm | parser

chain = RunnableParallel(
    project_output = project_pipeline ,
    About_output = About_pipeline
)
id=0
for job_description, job_url in zip(df["job_description"], df["job_url"]):
    job_id = re.search(r'/jobs/view/(\d+)/', job_url).group(1)
    docs_projects= retriver_projects.invoke(job_description)
    retrived_text_projects="\n\n".join([doc.page_content for doc in docs_projects])

    docs_About = retriver_About.invoke(job_description)
    retrived_text_About="\n\n".join([doc.page_content for doc in docs_About])
    
    output = chain.invoke({"job_description": job_description, "retrieved_projects": retrived_text_projects , "retrieved_About" : retrived_text_About})

    output_projects = parse_projects(output["project_output"])

    output_about = parse_projects(output["About_output"])[0]["About"]




    output_pdf=fill_resume(input_pdf=r"D:\LANGCHAIN\langchain_Resume_Builder\resume(3.0).pdf" ,output_pdf=f"{job_id}.pdf" , projects=output_projects ,about=output_about)

    df.loc[id , "resume_updated"] = f"{str(job_id)}.pdf"
    id +=1


df.to_csv("Final_Resume_update" ,index=False)
    










