import streamlit as st
import configs as c 
c.page("Search")    # must be 1st streamlit cmd or strange behavior ensues
import datetime
import sqlgen as sg
import db

if c.config["info_msg"]:
    st.info(c.config["info_msg"]) 
st.header("FOIArchive Search")
f"""
First time here? Learn more about our collections 
[here]({c.config['collections_pg']}) and watch this
brief [screencast]({c.config['intro_screencast']}) to see how to use the 
search interface. More specific queries returning < {c.config['max_rows']}
documents run faster and return metadata and text.
"""

# GUI search widgets
# get values to populate values and ranges
classification_lovs = db.get_lov("classifications", "classification")
corpora_lovs = db.get_lov("corpora", "corpus")
MIN_AUTHORED = datetime.date(1861, 5, 1)
MAX_AUTHORED = datetime.date(2013, 7, 8)
entities_df = db.load_execute('entities')

#
# Search form
with st.form("search_form"):
    search_str = st.text_input(label_visibility="visible",
                               label="Full-Text",
                               placeholder="Enter search terms",
                               help=c.config['search_str_help'],
                               value=st.query_params.get('qry'))
    col1, col2 = st.columns(2)
    corpora = col1.multiselect("Corpus", 
                               corpora_lovs,
                               placeholder=c.config['corpus_placeholder'])    
    classifications = col2.multiselect("Original Classification", 
                                       classification_lovs,
                                       placeholder=
                                        c.config['classification_placeholder'],
                                       help=c.config['classification_help'])
    entities = col1.multiselect("People, Places, Organizations...",
                                entities_df['entity_dropdown_str'],
                                placeholder=c.config['entity_placeholder'],
                                help=c.config['entity_help'])
    dates = col2.date_input("Date Range", value=[], 
                            min_value=MIN_AUTHORED, max_value=MAX_AUTHORED,
                            help=c.config['date_help'])
    entities_all = col1.checkbox("All entities appear in document", value=True)
    null_date = col2.checkbox("Include documents without a date", value=True) 
    submitted = st.form_submit_button("Search", type="primary")

# Dynamic SQL generation
# build where clause
sql_predicates = []
display_predicates = []
if search_str:
    sg.add_predicate(sql_predicates, sg.search_predicate('full_text', search_str))
    sg.add_predicate(display_predicates, f"full_text('{search_str}')")
corpus_predicate = sg.lov_predicate('corpus', corpora)
sg.add_predicate(sql_predicates, corpus_predicate)
sg.add_predicate(display_predicates, corpus_predicate)
classification_predicate = sg.lov_predicate('classification', classifications)
sg.add_predicate(sql_predicates, classification_predicate)
sg.add_predicate(display_predicates, classification_predicate)
start_date, end_date = sg.convert_daterange(dates, "%Y/%m/%d")
date_predicate = sg.daterange_predicate('authored',
                                        start_date, end_date, null_date, 
                                        MIN_AUTHORED, MAX_AUTHORED)
sg.add_predicate(sql_predicates, date_predicate)
sg.add_predicate(display_predicates, date_predicate)
if entities:
    # TBD: code simplification by using entity_id throughout
    entities_nocnt = [s.rsplit(' (', 1)[0] for s in entities]
    entities_quoted = [s.replace("'", "''") for s in entities_nocnt]
    sg.add_predicate(sql_predicates, sg.entity_predicate(entities_quoted, entities_all))
    if entities_all:
        entity_function = "all_entities"
    else:
        entity_function = "any_entities"
    sg.add_predicate(display_predicates, f"{entity_function}{entities_nocnt}")

  
where_clause = sg.where_clause(predicates=sql_predicates)
query_display = sg.where_clause(predicates=display_predicates)

if where_clause:
    st.caption(":grey[Search Query]")
    if entities:
        st.warning(c.config['entity_warning'])
    st.code(f"{query_display}", language="sql")
    print(f'query|{datetime.datetime.now()}|{query_display}', flush=True)
    # display metrics
    metrics_sql = sg.query(template_name='metrics', table_name=c.config["table_name"], where_clause=where_clause)
    metrics_df = db.execute(metrics_sql)
    metrics = metrics_df.iloc[0] 
    st.metric(label="Documents Found", value=f"{metrics['doc_cnt']:,}", delta=None)
    # if there are results, execute bar_chart and possibly other queries 
    if metrics['doc_cnt']:
        aggdate, x_axis_label = sg.aggdate_expr('authored', metrics)
        bar_chart_sql = sg.aggquery('bar_chart', c.config["table_name"], 
                                    where_clause, aggdate)
        bar_chart_df = db.execute(bar_chart_sql)
        bar_chart_df.rename(columns={'Date': x_axis_label}, inplace=True)
        st.vega_lite_chart(bar_chart_df,
                            {"mark": {"type": "bar"},
                             "encoding": {
                                "x": {"field": x_axis_label, "type": "ordinal"},
                                "y": {"field": "Documents", "type": "quantitative"},
                                "color": {"field": "Corpus",   "type": "nominal",
                                          "legend": {"orient": "bottom"}}
                                },
                            }, use_container_width=True)  
        if metrics['doc_cnt'] > c.config["max_rows"]:
            st.markdown(f"##### Search results exceed downloadable document limit.")
            st.write(f"Download a sample of the results below with *{c.config['max_rows']}* out of *{metrics['doc_cnt']}* rows generated.")
            data_table_sql = sg.query(template_name='data_table', table_name=c.config["table_name"],
                                    where_clause=where_clause, limit_clause=c.config["max_rows"])
            data_table_df = db.execute(data_table_sql)
            data_table_df['docviewer_url'] = data_table_df['doc_id'].apply(
                lambda x: f"{c.config['docviewer_url']}?doc_id={x}")
            st.dataframe(data_table_df,
                         use_container_width=True, 
                         hide_index=True,
                         column_order=c.COLUMN_ORDER, 
                         column_config=c.COLUMN_CONFIGS)
            sample_limited_csv = data_table_df.to_csv(index=False).encode('utf-8')
            col1, col2, col3 = st.columns([4, 3, 4])
            with col2:
                st.download_button(
                    label="Download Sample",
                    data=sample_limited_csv,
                    file_name="foi_sample_limited_data.csv",
                    mime="text/csv",
                    key="download_sample"
                )

            st.write(f"Didn't get the expected results? \
                        [Let us know.]({c.search_results_email(query_display)})")

            # st.markdown(f"##### Limit results to < {c.config['max_rows']} \
            #            for downloadable metadata and text.")
        else:
            data_table_sql = sg.query(template_name='data_table', table_name=c.config["table_name"], 
                                    where_clause=where_clause)        
            data_table_df = db.execute(data_table_sql)
            data_table_df['docviewer_url'] = data_table_df['doc_id'].apply(
                lambda x: f"{c.config['docviewer_url']}?doc_id={x}")
            st.dataframe(data_table_df,
                         use_container_width=True, 
                         hide_index=True,
                         column_order=c.COLUMN_ORDER, 
                         column_config=c.COLUMN_CONFIGS)  
            csv_full_report = data_table_df.to_csv(index=False).encode('utf-8')
            col1, col2, col3 = st.columns([4, 3, 4])
            with col2:
                st.download_button(
                    label="Download Report",
                    data=csv_full_report,
                    file_name="foi_full_search_report.csv",
                    mime="text/csv",
                    key="download_sample"
                )
            st.write(f"Didn't get the expected results? \
                     [Let us know.]({c.search_results_email(query_display)})")      

st.markdown("<br><br><br>", unsafe_allow_html=True)
st.markdown(c.config["email_support"])
