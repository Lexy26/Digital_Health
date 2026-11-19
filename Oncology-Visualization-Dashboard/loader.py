import os
import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

FOLDER = os.path.join(BASE_DIR, "DATASET")
CLINICAL_SAMPLE_FILE = os.path.join(FOLDER, "data_clinical_sample.csv")
CLINICAL_PATIENT_FILE = os.path.join(FOLDER, "data_clinical_patient.csv")


def load_data():
    needed_sample_cols = [
        "PATIENT_ID",
        "CANCER_TYPE",
        "METASTATIC_SITE",
        "ONCOTREE_CODE",
        "SAMPLE_TYPE"
    ]

    needed_patient_cols = [
        "PATIENT_ID",
        "GENDER",
        "CURRENT_AGE_DEID",
        "STAGE_HIGHEST_RECORDED",
        "OS_STATUS",
        "OS_MONTHS"
    ]

    sample = pd.read_csv(CLINICAL_SAMPLE_FILE, low_memory=False)
    patient = pd.read_csv(CLINICAL_PATIENT_FILE, low_memory=False)

    sample = sample[needed_sample_cols].copy()
    patient = patient[needed_patient_cols].copy()

    bad = {"", "nan", "NaN", "None", "Unknown"} # Not Applicable

    sample = sample[
        (sample["PATIENT_ID"].notna()) &
        ~sample["PATIENT_ID"].isin(bad) &
        ~sample["CANCER_TYPE"].isin(bad) &
        ~sample["METASTATIC_SITE"].isin(bad)
    ].copy()

    patient = patient[
        (patient["PATIENT_ID"].notna()) &
        ~patient["PATIENT_ID"].isin(bad) &
        ~patient["GENDER"].isin(bad)
    ].copy()

    df = sample.merge(patient, on="PATIENT_ID", how="left")

    return df