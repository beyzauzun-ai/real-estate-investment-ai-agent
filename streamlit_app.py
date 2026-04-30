from google.cloud import bigquery
from google.oauth2 import service_account
import streamlit as st

credentials = service_account.Credentials.from_service_account_info(
    st.secrets["gcp_service_account"]
)

client = bigquery.Client(
    credentials=credentials,
    project=credentials.project_id
)

import streamlit as st
import subprocess
import re

st.set_page_config(page_title="Real Estate AI Agent", page_icon="🏡", layout="centered")

st.title("🏡 Real Estate Investment AI Agent")
st.caption("BigQuery + Gemini + Google ADK tabanlı emlak yatırım analizi")

def clean_output(text):
    patterns = [
        r"Log setup complete:.*\n",
        r"To access latest log:.*\n",
        r"MCP Toolset configured.*\n",
        r"Running agent.*\n",
        r"\[user\]:.*\n",
        r"\[real_estate_advisor\]:",
    ]
    for p in patterns:
        text = re.sub(p, "", text)
    return text.strip()

def ask_agent(question):
    cmd = f'printf "%s\n" "{question}" | adk run mcp_bakery_app'
    result = subprocess.run(
        cmd,
        shell=True,
        capture_output=True,
        text=True,
        timeout=300
    )
    return clean_output(result.stdout), result.stderr

def get_recommendation(text):
    text = text.lower()
    if "buy" in text or "satın al" in text:
        return "🟢 BUY"
    elif "hold" in text or "bekle" in text:
        return "🟡 HOLD"
    elif "avoid" in text or "kaçın" in text:
        return "🔴 AVOID"
    return "🟡 HOLD"


def get_real_data(city):
    from google.cloud import bigquery
    client = bigquery.Client()

   
    if city is None:
        return None

    city_lower = city.lower()

    query = f"""
    SELECT *
    FROM `real_estate.investment_data`
    WHERE LOWER(city) LIKE '%{city_lower}%'
    LIMIT 1
    """

    result = client.query(query).to_dataframe()

    if not result.empty:
        return result.iloc[0]
    return None

def extract_metrics(text):
    import re

    metrics = {
        "Market Demand": 60,
        "Price Growth": 60,
        "Safety": 60
    }

    numbers = re.findall(r"\d+", text)

    if len(numbers) >= 3:
        metrics["Market Demand"] = int(numbers[0])
        metrics["Price Growth"] = int(numbers[1])
        metrics["Safety"] = int(numbers[2])

    return metrics


if "messages" not in st.session_state:
    st.session_state.messages = []

st.markdown("### Örnek Sorular")
c1, c2, c3 = st.columns(3)

example_question = None
with c1:
    if st.button("Santa Monica"):
        example_question = "Santa Monica 90401 için kısa yatırım analizi yap."
with c2:
    if st.button("Los Angeles"):
        example_question = "Los Angeles 90001 için yatırım açısından kısa yorum yap."
with c3:
    if st.button("Tavsiye Al"):
        example_question = "Bu bölge için satın al, bekle ya da kaçın tavsiyesi ver."

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

prompt = st.chat_input("Bir bölge veya posta kodu için yatırım sorusu yaz...")

st.markdown("### 📊 Örnek Kullanım")
st.info("Örn: 'New York Manhattan yatırım analizi yap ve BUY/HOLD/AVOID öner'")

if example_question:
    prompt = example_question

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

with st.chat_message("assistant"):
    with st.spinner("Agent analiz yapıyor..."):
        
        data = get_real_data(prompt)
        if data is not None:
            enriched_prompt = f"""
            Location: {data['city']}
            Avg Price: {data['avg_price']}
            Price Growth: {data['price_growth']}
            Safety: {data['safety_score']}
            Demand: {data['market_demand']}

            Based on this data, give investment recommendation: BUY / HOLD / AVOID and explain.
            """
        else:
            enriched_prompt = prompt

        answer, error = ask_agent(enriched_prompt)

        if answer:
            st.markdown(answer)

            # --- Investment Score ---
            score = 75
            st.markdown("### 📈 Investment Score")
            st.progress(score / 100)
            st.metric(label="Investment Potential", value=f"{score}%")

            metrics = extract_metrics(answer)

            order = ["Market Demand", "Price Growth", "Safety"]

            data = get_real_data(str(prompt))

            if data is not None:
                chart_data = {
                    "Metric": ["Price Growth", "Safety", "Market Demand"],
                    "Score": [
                        data["price_growth"],
                        data["safety_score"],
                        data["market_demand"]
                    ]
                }

                score = int((data["price_growth"] + data["safety_score"] + data["market_demand"]) / 3)
            else:
                chart_data = {
                    "Metric": ["Price Growth", "Safety", "Market Demand"],
                    "Score": [70, 70, 70]
                }
                score = 70


            st.bar_chart(chart_data, x="Metric", y="Score")

            rec = get_recommendation(answer)

            if "BUY" in rec:
                st.success(f"💰 Tavsiye: {rec}")
            elif "HOLD" in rec:
                st.warning(f"⚖️ Tavsiye: {rec}")
            elif "AVOID" in rec:
                st.error(f"🚫 Tavsiye: {rec}")
            else:
                st.info(f"📊 Tavsiye: {rec}")
            st.subheader("📍 Lokasyon")
            place_type = st.selectbox(
                "Yatırım kriteri seç:",
                {
                    "Günlük yaşam (Market)": "market",
                    "Eğitim (School)": "school",
                    "Sağlık (Hospital)": "hospital",
                    "Ulaşım (Metro)": "metro"
                }
            )

            location_query = prompt if prompt else example_question
            location_query = location_query if location_query else "New York Manhattan"
            map_url = f"https://www.google.com/maps?q={place_type}+near+{location_query}&output=embed"
            st.components.v1.iframe(map_url, height=400) 

        else:
            st.warning("Cevap alınamadı.")
            if error:
                st.text(error)
