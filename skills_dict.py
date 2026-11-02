# canonical name: (category, [regex aliases, matched case-insensitively])
SKILLS = {
    # languages
    "Python": ("language", [r"python"]),
    "Java": ("language", [r"java"]),
    "JavaScript": ("language", [r"javascript", r"ecmascript", r"es6"]),
    "TypeScript": ("language", [r"typescript"]),
    "C++": ("language", [r"c\+\+", r"cpp"]),
    "C#": ("language", [r"c#", r"c sharp"]),
    "Go": ("language", [r"golang"]),
    "Kotlin": ("language", [r"kotlin"]),
    "PHP": ("language", [r"php"]),
    "Scala": ("language", [r"scala"]),
    "SQL": ("language", [r"sql", r"t-sql", r"pl/sql"]),
    "Bash": ("language", [r"bash", r"shell scripting"]),
    "PowerShell": ("language", [r"powershell"]),

    # frontend
    "HTML/CSS": ("frontend", [r"html5?", r"css3?"]),
    "React": ("frontend", [r"react\.?js"]),
    "Angular": ("frontend", [r"angular(?:js)?"]),
    "Vue.js": ("frontend", [r"vue(?:\.?js)?"]),
    "Next.js": ("frontend", [r"next\.?js"]),

    # backend
    "Node.js": ("backend", [r"node\.?js"]),
    "Django": ("backend", [r"django"]),
    "Flask": ("backend", [r"flask"]),
    "FastAPI": ("backend", [r"fastapi"]),
    "Spring": ("backend", [r"spring ?boot", r"spring framework"]),
    ".NET": ("backend", [r"\.net(?: core)?", r"asp\.net", r"dotnet"]),
    "APIs (REST)": ("backend", [r"restful", r"rest apis?", r"apis?", r"api development"]),  # CHANGED
    "GraphQL": ("backend", [r"graphql"]),
    "Microservices": ("backend", [r"micro-?services?"]),
    "JSON/XML": ("backend", [r"json", r"xml"]),  # NEW
    "SOAP": ("backend", [r"soap"]),  # NEW
    "MVC": ("backend", [r"mvc"]),  # NEW

    # databases
    "PostgreSQL": ("database", [r"postgres(?:ql)?"]),
    "MySQL": ("database", [r"mysql"]),
    "SQL Server": ("database", [r"sql server", r"mssql"]),
    "Oracle Database": ("database", [r"oracle db", r"oracle database"]),
    "MongoDB": ("database", [r"mongo(?:db)?"]),
    "Redis": ("database", [r"redis"]),
    "NoSQL": ("database", [r"nosql", r"dynamodb", r"cassandra"]),  # CHANGED
    "Elasticsearch": ("database", [r"elastic ?search"]),
    "Relational Databases": ("database", [r"rdbms", r"relational databases?"]),  # NEW

    # cloud
    "AWS": ("cloud", [r"aws", r"amazon web services"]),
    "Azure": ("cloud", [r"azure"]),
    "GCP": ("cloud", [r"gcp", r"google cloud(?: platform)?"]),

    # devops
    "Docker": ("devops", [r"docker"]),
    "Kubernetes": ("devops", [r"kubernetes", r"k8s"]),
    "Terraform": ("devops", [r"terraform"]),
    "Infrastructure as Code": ("devops", [r"iac", r"infrastructure as code", r"cloudformation",
                                          r"pulumi", r"bicep"]),  # NEW
    "Ansible": ("devops", [r"ansible"]),
    "CI/CD": ("devops", [r"ci ?/ ?cd", r"continuous integration", r"continuous (?:delivery|deployment)"]),
    "Jenkins": ("devops", [r"jenkins"]),
    "GitHub Actions": ("devops", [r"github actions"]),
    "Git": ("devops", [r"git", r"github", r"gitlab", r"bitbucket"]),
    "Linux": ("devops", [r"linux", r"unix", r"ubuntu", r"red ?hat", r"rhel"]),
    "Prometheus": ("devops", [r"prometheus"]),
    "Grafana": ("devops", [r"grafana"]),

    # data
    "Pandas": ("data", [r"pandas"]),
    "NumPy": ("data", [r"numpy"]),
    "Apache Spark": ("data", [r"apache spark", r"pyspark", r"spark sql"]),
    "Kafka": ("data", [r"kafka"]),
    "Airflow": ("data", [r"airflow"]),
    "dbt": ("data", [r"dbt"]),
    "Hadoop": ("data", [r"hadoop", r"hive", r"hdfs"]),
    "ETL": ("data", [r"etl", r"elt"]),
    "SSIS/SSRS": ("data", [r"ssis", r"ssrs"]),  # NEW
    "Data Warehousing": ("data", [r"data warehous\w*"]),
    "Snowflake": ("data", [r"snowflake"]),
    "Databricks": ("data", [r"databricks"]),
    "BigQuery": ("data", [r"big ?query"]),
    "Power BI": ("data", [r"power ?bi"]),
    "Tableau": ("data", [r"tableau"]),
    "Statistics": ("data", [r"statistic(?:s|al)"]),

    # AI / ML
    "Machine Learning": ("ml_ai", [r"machine learning", r"ml"]),
    "Deep Learning": ("ml_ai", [r"deep learning", r"neural networks?"]),
    "PyTorch": ("ml_ai", [r"pytorch", r"torch"]),
    "TensorFlow": ("ml_ai", [r"tensorflow"]),
    "Keras": ("ml_ai", [r"keras"]),
    "scikit-learn": ("ml_ai", [r"scikit-?learn", r"sklearn"]),
    "NLP": ("ml_ai", [r"nlp", r"natural language processing"]),
    "Computer Vision": ("ml_ai", [r"computer vision", r"opencv"]),
    "LLMs": ("ml_ai", [r"llms?", r"large language models?", r"generative ai", r"genai", r"gen ai"]),
    "RAG": ("ml_ai", [r"rag", r"retrieval[- ]augmented generation"]),
    "LangChain": ("ml_ai", [r"langchain"]),
    "LangGraph": ("ml_ai", [r"langgraph"]),
    "Hugging Face": ("ml_ai", [r"hugging ?face"]),
    "Vector Databases": ("ml_ai", [r"vector (?:databases?|stores?|db)", r"pinecone", r"chromadb",
                                   r"faiss", r"weaviate", r"qdrant", r"pgvector"]),
    "Prompt Engineering": ("ml_ai", [r"prompt engineering"]),
    "MLOps": ("ml_ai", [r"mlops", r"mlflow", r"kubeflow"]),
    "AI Agents": ("ml_ai", [r"ai agents?", r"agentic", r"multi-agent"]),

    # security
    "SIEM": ("security", [r"siem", r"splunk", r"qradar"]),
    "Penetration Testing": ("security", [r"penetration testing", r"pen ?test\w*"]),
    "Vulnerability Management": ("security", [r"vulnerability (?:management|assessments?|scanning)"]),
    "Identity & Access Management": ("security", [r"iam", r"identity and access management", r"okta"]),
    "Network Security": ("security", [r"network security", r"firewalls?", r"ids/ips"]),
    "Incident Response": ("security", [r"incident response"]),
    "Security Frameworks": ("security", [r"nist", r"iso 27001", r"soc 2", r"pci[- ]dss"]),
    "DevSecOps": ("security", [r"devsecops"]),  # NEW

    # networking & IT support
    "Networking Fundamentals": ("networking", [r"tcp/ip", r"tcp", r"udp", r"dns", r"dhcp", r"subnetting",
                                               r"osi model", r"lan", r"wan", r"vpns?"]),  # CHANGED
    "Routing & Switching": ("networking", [r"routing (?:and|&) switching", r"bgp", r"ospf", r"eigrp", r"vlans?"]),
    "Cisco": ("networking", [r"cisco", r"ccna", r"ccnp"]),
    "Active Directory": ("it_support", [r"active directory"]),
    "Windows Server": ("it_support", [r"windows server"]),
    "Microsoft 365": ("it_support", [r"office 365", r"microsoft 365", r"o365", r"m365"]),
    "SharePoint": ("it_support", [r"sharepoint"]),  # NEW
    "ITIL / ITSM": ("it_support", [r"itil", r"itsm"]),  # CHANGED
    "ServiceNow": ("it_support", [r"servicenow"]),
    "VMware": ("it_support", [r"vmware", r"vsphere", r"esxi"]),

    # enterprise platforms  (NEW category)
    "SAP": ("enterprise", [r"sap", r"abap"]),
    "Salesforce": ("enterprise", [r"salesforce", r"sfdc"]),
    "PeopleSoft": ("enterprise", [r"peoplesoft"]),

    # embedded  (NEW category)
    "Embedded Systems": ("embedded", [r"embedded (?:systems?|software|c)", r"rtos", r"firmware",
                                      r"microcontrollers?"]),

    # mobile
    "Android": ("mobile", [r"android"]),
    "Flutter": ("mobile", [r"flutter"]),
    "React Native": ("mobile", [r"react native"]),

    # testing
    "Selenium": ("testing", [r"selenium"]),
    "Cypress": ("testing", [r"cypress"]),
    "Unit Testing": ("testing", [r"unit tests?", r"unit testing", r"pytest", r"junit", r"jest"]),
    "Test Automation": ("testing", [r"test automation", r"automated testing"]),
    "TDD": ("testing", [r"tdd", r"test[- ]driven development"]),  # NEW

    # certifications  (NEW category)
    "CompTIA Certifications": ("certification", [r"comptia", r"a\+", r"network\+", r"security\+"]),
    "Security Certifications": ("certification", [r"cissp", r"cism", r"cisa", r"ceh", r"oscp"]),

    # practices
    "Agile": ("practice", [r"agile", r"scrum", r"kanban"]),
    "Jira": ("practice", [r"jira"]),
    "DevOps": ("practice", [r"devops"]),  # NEW
    "SDLC": ("practice", [r"sdlc", r"software development life ?cycle"]),  # NEW
    "Site Reliability Engineering": ("practice", [r"sre", r"site reliability"]),  # NEW
    "System Design": ("practice", [r"system design", r"distributed systems"]),
    "Data Structures & Algorithms": ("practice", [r"data structures", r"dsa", r"algorithm design"]),
    "Troubleshooting": ("practice", [r"troubleshoot\w*"]),
}

# Ambiguous names: matched with EXACT capitalization (and context for R / Go)
CASE_SENSITIVE = {
    "R": ("language", [r"R(?=\s*(?:programming|language|studio|,|/|\)))"]),
    "Go": ("language", [r"Go(?=\s*(?:programming|language|,|/|\)))"]),
    "React": ("frontend", [r"React(?!\s*Native)"]),
    "APIs (REST)": ("backend", [r"REST"]),  # NEW: "REST" capitals = the API style, "rest" = a break
    "Apache Spark": ("data", [r"Spark"]),
    "Excel": ("data", [r"Excel"]),
    "SAS": ("data", [r"SAS"]),  # NEW: exact "SAS", so "SaaS" doesn't match
    "Swift": ("mobile", [r"Swift"]),
    "Rust": ("language", [r"Rust"]),
    "Ruby": ("language", [r"Ruby"]),
    "iOS": ("mobile", [r"iOS"]),
}