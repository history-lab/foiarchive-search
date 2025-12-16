import streamlit as st
import configs as c
doc_id = st.query_params.get('doc_id') 
c.page(f"{doc_id}")    # must be 1st streamlit cmd or strange behavior ensues
import datetime
import sqlgen as sg
import db
from collections import Counter
import re
from stopwords import get_stopwords
import pandas as pd
from textblob import TextBlob
#from prompt_llm import call_deepseek_model
#from similar_docs_idx.find_similar_docs import get_top_five_results
import concurrent.futures


STOP_WORDS = set(get_stopwords("en"))

def display_similar_documents(doc):

    results = get_top_five_results(doc)

    if results:
        st.sidebar.markdown("#### Similar Documents")

        for similar_id in results:
            url = f"https://docviewer.history-lab.org/?doc_id={similar_id}"
            st.sidebar.markdown(f"* [{similar_id}]({url})", unsafe_allow_html=True)
    else:
        st.sidebar.markdown("No similar documents found.")


def display_date(date):
    if date:
        if date.time() == datetime.time(0, 0):
            date_str = f"{date.date().strftime('%b %d, %Y')}"
        else:
            date_str = f"{date.strftime('%b %d, %Y %H:%M:%S')}"
        st.markdown(f"**{date_str}**") 

def display_citation(title, corpus_name, doc_id):
    date_str = f"{datetime.date.today().strftime('%b %d, %Y')}"
    st.sidebar.markdown(f"### Citation:")
    citation_str = (f"{title}, _{corpus_name}_, Document ID Number: {doc_id}, "
                    f"http://www.history-lab.org [Accessed: {date_str}]")
    st.sidebar.markdown(citation_str)

def display_year_references(doc):
    matches = re.findall(r'\b(1[5-9]\d{2}|20[0-2]\d)\b', doc.body)
    year_counts = Counter(matches).most_common()
    if year_counts:
        df = pd.DataFrame(year_counts, columns=["Year", "Mentions"])
        st.write("###### Referenced Years")
        st.dataframe(df, hide_index=True, use_container_width=True, height=150)
    else:
        st.write("###### Referenced Years")
        st.write("No referenced years detected in the document.")

def display_entities(doc_id):
    doc_entities_sql = sg.by_doc_id('doc_entities', doc_id)
    edf = db.execute(doc_entities_sql)
    entity_list = edf.iloc[0]['entity_list']
    if entity_list:
        st.sidebar.markdown("### Entities:")
        st.sidebar.write(entity_list)  


def display_summary(doc_body):
    message = f"""
        Summarize the following text in a clear, objective, and concise way. Aim for a summary between **50 and 100 words**. Avoid including extraneous details, personal opinions, or stylistic flourishes.

        Use plain, academic language and keep the summary to 50 words about. Just focus on the core ideas and key information.

        Document:
        {doc_body}
    """

    response = None
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future = executor.submit(call_deepseek_model, message)
        try:
            response = future.result(timeout=10) 
        except concurrent.futures.TimeoutError:
            response = "Failed to generate"

    st.sidebar.markdown("### Document Summary:")
    st.sidebar.write(response)


def display_sentiment(doc):
    blob = TextBlob(doc.body)
    polarity = blob.sentiment.polarity
    subjectivity = blob.sentiment.subjectivity
    st.sidebar.write("###### Document Sentiment")
    st.sidebar.write(f"* **Polarity:** {polarity:.2f}")
    st.sidebar.write(f"* **Subjectivity:** {subjectivity:.2f}")

def display_topics(doc_id):
    doc_topics_sql = sg.by_doc_id('doc_topics', doc_id)
    tdf = db.execute(doc_topics_sql)
    if not tdf.empty:
        st.sidebar.markdown("### Topic(s):")
        st.sidebar.dataframe(tdf, hide_index=True)

def display_source(source):
    if source:
        st.markdown(f"[Source Document PDF]({source})")

def display_frus_body(id):
    qry = sg.by_doc_id('docviewer_frus', doc_id)
    results = db.execute(qry)
    source = results.iloc[0]['source']
    body = results.iloc[0]['body']
    st.markdown(f"[US State Department, Office of the Historian]({source})")
    st.markdown(body, unsafe_allow_html=True)

def display_body(doc):
    if doc.body:
        if doc.corpus == 'frus':
            display_frus_body(doc.doc_id)
        else:
            st.text(doc.body)
    else:
        st.write("No document body")
 
def display_cnt(type, cnt):
    if cnt:
        st.sidebar.markdown(f"### {type}: {cnt}")

def display_common_words(doc):
    words = re.findall(r'\b\w+\b', doc.body.lower())
    filtered_words = [word for word in words if word not in STOP_WORDS and len(word) >= 5]
    word_counts = Counter(filtered_words).most_common(5)
    df = pd.DataFrame(word_counts, columns=["Word", "Count"])
    #st.write("###### Most Common Words")
    #st.dataframe(df, hide_index=True, use_container_width=True, height=200)
    st.sidebar.markdown('### Most common words:')
    st.sidebar.dataframe(df, hide_index=True)

def display_doc(doc):
    #col1, col2, col3 = st.columns([10, 1, 5])
    #with col1:
    st.subheader(doc.title)
    display_date(doc.authored)
    display_source(doc.source)
    display_body(doc)
    display_citation(doc.title, doc.corpus_title, doc.doc_id)
    
    #with col3:
    #    st.subheader("Document NLP Analytics")
    #    #display_common_words(doc)
    #    display_sentiment(doc)
    #    display_year_references(doc)


    # Move sidebar content outside of the columns
    st.sidebar.markdown(f"### Original Classification: {doc.classification}") 
    display_entities(doc.doc_id)
    display_topics(doc.doc_id)
    display_cnt('Pages', doc.pg_cnt)
    display_cnt('Words', doc.word_cnt)
    st.sidebar.subheader('Document NLP Analytics')
    display_common_words(doc)
    display_sentiment(doc)
    #display_similar_documents(doc)
    #display_summary(doc.body[0:5000])

print(f'viewer|{datetime.datetime.now()}|{doc_id}', flush=True)    # logging

if doc_id:
    doc_sql = sg.by_doc_id('docviewer', doc_id)
    doc_df = db.execute(doc_sql)
    if doc_df.empty:
        st.warning(f"Warning: No document with ID {doc_id} found")
    else:                   # doc exists, display it
        display_doc(doc_df.iloc[0])
else:
    st.error("Error: No document ID provided")
c.footer()
