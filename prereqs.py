# prereqs.py - which skills to learn BEFORE others. Hand-written, NOT from the job data:
# job posts say what employers want, not in which order people learn it.
# Each skill lists what it needs first. A tuple means "any ONE of these is enough".
# Names must match skills_dict.py exactly.
ANY_CLOUD = ("AWS", "Azure", "GCP")
ANY_CODE = ("Python", "Java", "JavaScript", "C#")

PREREQS = {
    # web
    "JavaScript": ["HTML/CSS"],
    "TypeScript": ["JavaScript"],
    "React": ["JavaScript"],
    "Angular": ["TypeScript"],
    "Vue.js": ["JavaScript"],
    "Next.js": ["React"],
    "React Native": ["React"],
    "Node.js": ["JavaScript"],
    # backend
    "Django": ["Python"],
    "Flask": ["Python"],
    "FastAPI": ["Python"],
    "Spring": ["Java"],
    ".NET": ["C#"],
    "Microservices": ["APIs (REST)"],
    "GraphQL": ["APIs (REST)"],
    # databases and data
    "PostgreSQL": ["SQL"],
    "MySQL": ["SQL"],
    "SQL Server": ["SQL"],
    "Oracle Database": ["SQL"],
    "SSIS/SSRS": ["SQL Server"],
    "Data Warehousing": ["SQL"],
    "ETL": ["SQL"],
    "dbt": ["SQL"],
    "Snowflake": ["SQL"],
    "BigQuery": ["SQL"],
    "Power BI": [("Excel", "SQL")],
    "Tableau": [("Excel", "SQL")],
    "Pandas": ["Python"],
    "NumPy": ["Python"],
    "Apache Spark": [("Python", "Scala", "Java"), "SQL"],
    "Databricks": ["Apache Spark"],
    "Airflow": ["Python"],
    # AI / ML
    "Machine Learning": ["Python", "Statistics"],
    "scikit-learn": ["Machine Learning"],
    "Deep Learning": ["Machine Learning"],
    "PyTorch": ["Deep Learning"],
    "TensorFlow": ["Deep Learning"],
    "Keras": ["Deep Learning"],
    "NLP": ["Machine Learning"],
    "Computer Vision": ["Deep Learning"],
    "LLMs": ["Python"],
    "RAG": ["LLMs"],
    "LangChain": ["LLMs"],
    "LangGraph": ["LangChain"],
    "AI Agents": ["LLMs"],
    "MLOps": ["Machine Learning", "Docker"],
    # devops and cloud
    "Bash": ["Linux"],
    "Docker": ["Linux"],
    "Kubernetes": ["Docker"],
    "Ansible": ["Linux"],
    "Terraform": [ANY_CLOUD],
    "Infrastructure as Code": [ANY_CLOUD],
    "CI/CD": ["Git"],
    "Jenkins": ["Git"],
    "GitHub Actions": ["Git"],
    "Grafana": ["Prometheus"],
    "DevSecOps": ["CI/CD"],
    # testing
    "Selenium": [ANY_CODE],
    "Cypress": ["JavaScript"],
    "Test Automation": [ANY_CODE],
    "TDD": ["Unit Testing"],
    # mobile
    "Android": [("Kotlin", "Java")],
    "iOS": ["Swift"],
    # networking and security
    "Routing & Switching": ["Networking Fundamentals"],
    "Cisco": ["Networking Fundamentals"],
    "Network Security": ["Networking Fundamentals"],
    "SIEM": ["Networking Fundamentals"],
    "Penetration Testing": ["Networking Fundamentals", "Linux"],
    "Incident Response": ["SIEM"],
}
