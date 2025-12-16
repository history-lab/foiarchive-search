import streamlit as st

@st.cache_resource
def get_conn():
    return st.connection("postgresql", type="sql", ttl="1d",
        dialect="postgresql",  
        username=st.secrets["postgresql"]["username"],
        password=st.secrets["postgresql"]["password"],
        host=st.secrets["postgresql"]["host"],
        port=st.secrets["postgresql"]["port"],
        database=st.secrets["postgresql"]["database"]
    )

conn = get_conn()


def load(filename):
    with open(f'sql/{filename}.sql', 'r') as file:
        sql = file.read()
    return sql

def load_execute(filename):
    return conn.query(load(filename))

def execute(query):
    return conn.query(query)

def get_lov(filename, colname):
    lov_df = load_execute(filename)
    lov_list = lov_df[colname].to_list()
    return lov_list
