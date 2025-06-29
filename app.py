import os
import requests
import streamlit as st

# ---------------------------------------------------------
# Entity Extraction Streamlit App using Dandelion API
# ---------------------------------------------------------
# Paste text → click a button → get back entities with direct
# links to their Wikidata items (when available).
# ---------------------------------------------------------
# 1. Install deps:  pip install streamlit requests
# 2. Put your Dandelion API token either
#    • in an env‑var        ⇒  export DANDELION_TOKEN="<TOKEN>"
#    • or in Streamlit secrets at .streamlit/secrets.toml
#         [default]
#         dandelion_token = "<TOKEN>"
# 3. Run the app:   streamlit run streamlit_app.py
# ---------------------------------------------------------

st.set_page_config(page_title="Entity Extractor (Dandelion)", page_icon="🔍")
st.title("🔍 Entity Extraction with Dandelion API")
st.markdown("Paste some text below and I'll pull out the entities with direct links to Wikidata.")

# -- Read API token
TOKEN = st.secrets.get("dandelion_token") or os.getenv("DANDELION_TOKEN")
if not TOKEN:
    st.warning("Add your Dandelion API token to **.streamlit/secrets.toml** as `dandelion_token = \"<TOKEN>\"` or set the environment variable **DANDELION_TOKEN** before running.")

# -- UI widgets
text_input = st.text_area("Text to analyze", height=250)
run_button = st.button("Extract entities")

# -- When user clicks the button
if run_button:
    if not TOKEN:
        st.stop()  # token missing, already warned above

    if not text_input.strip():
        st.error("Please enter some text first.")
        st.stop()

    with st.spinner("Contacting Dandelion…"):
        params = {
            "text": text_input,
            "token": TOKEN,
            # "include" decides which extra data we want back.
            # docs: https://dandelion.eu/docs/api/datatxt/nex/v1/
            "include": "lod,types,abstract"  # lod carries Wikidata IDs
        }
        try:
            resp = requests.get(
                "https://api.dandelion.eu/datatxt/nex/v1",
                params=params,
                timeout=15,
            )
        except requests.exceptions.RequestException as exc:
            st.error(f"Request failed: {exc}")
            st.stop()

    if resp.ok:
        data = resp.json()
        annotations = data.get("annotations", [])

        if not annotations:
            st.info("No entities found in the supplied text.")
        else:
            rows = []
            for ann in annotations:
                # Prefer title/label; fall back to the spotted substring.
                entity_label = ann.get("label") or ann.get("title") or ann.get("spot")
                confidence = ann.get("confidence", 0.0)

                # Locate Wikidata link inside the LOD block if present.
                wikidata_url = None
                for lod_match in ann.get("lod", []):
                    if (wikidata_id := lod_match.get("wikidata")):
                        wikidata_url = f"https://www.wikidata.org/wiki/{wikidata_id}"
                        break

                # Fallback: Dandelion returns a DBpedia URI by default.
                if not wikidata_url:
                    wikidata_url = ann.get("uri")

                rows.append(
                    {
                        "Entity": entity_label,
                        "Confidence": round(confidence, 3),
                        "Wikidata / URI": wikidata_url,
                    }
                )

            st.success(f"Found {len(rows)} entities:")
            st.dataframe(rows, use_container_width=True)
    else:
        st.error(f"Dandelion API error {resp.status_code}: {resp.text}")
