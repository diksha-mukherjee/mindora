
import streamlit as st
from tavily import TavilyClient

client = TavilyClient(api_key=st.secrets["TAVILY_API_KEY"])



def search_web(query):
    result = client.search(query=query, max_results=5)
    return result["results"]

