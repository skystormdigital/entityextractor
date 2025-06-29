import requests
import streamlit as st

# ---------------------------------------------------------
# Entity Extraction Streamlit App using Dandelion API
# ---------------------------------------------------------
# Paste text → click button → get entities with Wikidata links.
# ---------------------------------------------------------
# 1. Install deps:  pip install streamlit requests
# 2. 🔑  Put your Dandelion API token below. **Never commit real secrets to public repos.**
# 3. Run the app:   streamlit run streamlit_app.py
# ---------------------------------------------------------

# === Your API token (replace the placeholder string) ===
DANDELION_TOKEN = "928aeec989914427a4a2c1ddc0f5edf1"

st.set_page_config(page_title="Entity Extractor (Dandelion)", page_icon="🔍")
st.title("🔍 Entity Extraction with Dandelion API")
st.markdown("Paste some text below and I'll pull out the entities with direct links to Wikidata.")

if DANDELION_TOKEN == "YOUR_API_TOKEN_HERE" or not DANDELION_TOKEN.strip():
    st.error("⚠️ Please set your Dandelion API token in the variable `DANDELION_TOKEN` inside *streamlit_app.py*.")
    st.stop()

# -- UI widgets
text_input = st.text_area("Text to analyze", height=250)
run_button = st.button("Extract entities")

# -- When user clicks the button
if run_button:
    if not text_input.strip():
        st.error("Please enter some text first.")
        st.stop()

    with st.spinner("Contacting Dandelion…"):
        params = {
            "text": text_input,
            "token": DANDELION_TOKEN,
            "include": "lod,types,abstract",  # lod carries Wikidata IDs
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
                lod_data = ann.get("lod", {})
                if isinstance(lod_data, dict):
                    wikidata_id = lod_data.get("wikidata")
                    if wikidata_id:
                        wikidata_url = f"https://www.wikidata.org/wiki/{wikidata_id}"

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
