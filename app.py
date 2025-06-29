import requests
import streamlit as st
from urllib.parse import urlparse

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

# -- Helper to normalize wikidata values (could be full URL or bare ID)
def to_wikidata_url(value: str | None) -> str | None:
    if not value:
        return None
    # If it's already a full URL, return as‑is (replace http with https).
    if value.startswith("http"):
        parsed = urlparse(value)
        # Ensure we have https scheme
        return f"https://{parsed.netloc}{parsed.path}"
    # Else assume it's an ID like "Q42".
    return f"https://www.wikidata.org/wiki/{value}"

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
                lod_field = ann.get("lod", {})
                # If lod is a dict (most common)
                if isinstance(lod_field, dict):
                    wikidata_url = to_wikidata_url(lod_field.get("wikidata"))
                # If lod is a list (edge‑case API variant)
                elif isinstance(lod_field, list):
                    for lod_match in lod_field:
                        if isinstance(lod_match, dict):
                            wikidata_url = to_wikidata_url(lod_match.get("wikidata"))
                            if wikidata_url:
                                break

                # Fallback: Dandelion returns a DBpedia URI by default.
                if not wikidata_url:
                    wikidata_url = ann.get("uri")

                # Get type(s) of entity if available
                types = ann.get("types")
                if isinstance(types, list):
                    entity_type = ", ".join(types)
                elif isinstance(types, str):
                    entity_type = types
                else:
                    entity_type = "-"

                rows.append(
                    {
                        "Entity": entity_label,
                        "Type": entity_type,
                        "Confidence": round(confidence, 3),
                        "Wikidata / URI": wikidata_url,
                    }
                )

            st.success(f"Found {len(rows)} entities:")
            st.dataframe(rows, use_container_width=True)
    else:
        st.error(f"Dandelion API error {resp.status_code}: {resp.text}")
