import pandas as pd
import os

def save_to_csv(data: dict, filename: str = "responses.csv"):
    df = pd.DataFrame([data])
    if not os.path.exists(filename):
        df.to_csv(filename, index=False, encoding="utf-8-sig")
    else:
        df.to_csv(filename, mode="a", index=False, encoding="utf-8-sig", header=False)
