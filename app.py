import streamlit as st
from core import run

st.set_page_config(page_title="Mindora 🧠", page_icon="🧠", layout="wide")

# 🚫 HIDE STREAMLIT BRANDING (THIS IS THE FIX)

st.markdown(
    """
    <style>
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    .viewerBadge_container__1QSob {display: none !important;}
    .stAppDeployButton {display: none !important;}
    </style>
    """,
    unsafe_allow_html=True
)
st.title("🧠 Mindora")
# =========================
# SESSION STATE
# =========================
if "messages" not in st.session_state:
    st.session_state.messages = []

if "image_bytes" not in st.session_state:
    st.session_state.image_bytes = None


# =========================
# CHAT HISTORY
# =========================
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])


# =========================
# INPUT ROW (📎 + INPUT SIDE BY SIDE)
# =========================
col1, col2 = st.columns([0.85, 0.15])

with col1:
    query = st.chat_input("Ask anything")

with col2:
    image_file = st.file_uploader(
        "📎",
        label_visibility="collapsed",
        type=["png", "jpg", "jpeg"]
    )


# =========================
# STORE IMAGE
# =========================
if image_file is not None:
    st.session_state.image_bytes = image_file.read()


# =========================
# IMAGE PREVIEW
# =========================
if st.session_state.image_bytes:
    st.image(
        st.session_state.image_bytes,
        caption="Uploaded image",
        use_container_width=True
    )


# =========================
# RUN MODEL
# =========================
if query:
    st.session_state.messages.append({"role": "user", "content": query})

    with st.chat_message("user"):
        st.write(query)

    with st.chat_message("assistant"):
        with st.spinner("Thinking... 🧠"):
            answer, sources = run(query, st.session_state.image_bytes)

        st.write(answer)

        st.session_state.messages.append(
            {"role": "assistant", "content": answer}
        )

        if sources:
            st.caption("Sources:")
            for s in sources:
                st.write(s)

    # clear image after sending
    st.session_state.image_bytes = None