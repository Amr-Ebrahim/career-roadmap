from datetime import datetime
from retrieval import retrieve


def show(question, **kwargs):
    print(f"QUERY: {question}   {kwargs}")
    for r in retrieve(question, **kwargs):
        date = datetime.fromtimestamp(r["posted_ts"]).date()
        print(f"  score {r['score']:.3f} = sim {r['similarity']:.3f} + fresh {r['freshness']:.2f}"
              f" | {r['title']} | {r['level']} | {r['source']} | {date}")
    print()


show("cloud engineer with AWS and Terraform", role_family="devops_cloud", level="entry")
show("cloud engineer with AWS and Terraform", role_family="devops_cloud", level="entry", recency_weight=0)

show("engineer building LLM applications with RAG and agents", role_family="ai_ml")
show("engineer building LLM applications with RAG and agents", role_family="ai_ml", recency_weight=0)

show("backend engineer building microservices with Python, Kubernetes and PostgreSQL", level="senior")
show("backend engineer building microservices with Python, Kubernetes and PostgreSQL", level="senior", recency_weight=0)

show("data engineer building pipelines with Spark, Airflow and dbt", role_family="data")
show("data engineer building pipelines with Spark, Airflow and dbt", role_family="data", recency_weight=0)