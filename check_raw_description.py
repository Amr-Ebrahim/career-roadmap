import pandas as pd

needle = "MCSAServiceNow"
found = False

for batch in pd.read_csv(
    "data/raw/postings.csv",
    usecols=["title", "description"],
    chunksize=10000,
):
    matches = batch[
        batch["description"]
        .fillna("")
        .str.contains(needle, regex=False)
    ]

    if matches.empty:
        continue

    for _, row in matches.iterrows():
        text = row["description"]
        position = text.find(needle)

        print("Title:", row["title"])
        print("Original CSV excerpt:")
        print(repr(text[max(0, position - 150):position + 350]))
        print()

    found = True
    break

if not found:
    print("Exact phrase not found in the original CSV.")