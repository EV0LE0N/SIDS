import duckdb
from utils import CORE_FEATURES

def main():
    con = duckdb.connect()
    # 构造取【中位数】的 SQL
    med_cols = ", ".join([f'median("{f}") as "{f}"' for f in CORE_FEATURES])
    query = f"SELECT {med_cols} FROM read_parquet('/app/data/processed/attack_data.parquet/*.parquet') WHERE Label = 2"
    
    df = con.execute(query).df()
    
    print("=== ATTACK_LABEL_MAP[2] 真实中位数基线 ===")
    for feat in CORE_FEATURES:
        val = df.iloc[0][feat]
        print(f'        "{feat}": {round(val, 4)},')

if __name__ == "__main__":
    main()