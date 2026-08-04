"""
flow.py
Orchestration du pipeline oil_gas avec Prefect.
Équivalent d'un DAG Airflow : extract -> clean -> transform -> load
"""

from prefect import flow, task

from scripts.extract import extract
from scripts.clean import clean
from scripts.transform import transform
from scripts.load import load


@task(retries=2, retry_delay_seconds=30, name="extract")
def extract_task():
    return extract()


@task(retries=1, name="clean")
def clean_task(raw_data):
    return clean(raw_data)


@task(retries=1, name="transform")
def transform_task(cleaned_data):
    return transform(cleaned_data)


@task(retries=2, retry_delay_seconds=30, name="load")
def load_task(transformed_data):
    load(transformed_data)


@flow(name="oil_gas_pipeline")
def oil_gas_pipeline():
    raw = extract_task()
    cleaned = clean_task(raw)
    transformed = transform_task(cleaned)
    load_task(transformed)


if __name__ == "__main__":
    oil_gas_pipeline()
