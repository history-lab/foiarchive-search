def load_dynamic(filename):
    with open(f'sql/{filename}.dsql', 'r') as file:
        sql = file.read()
    return sql
    
def convert_daterange(dates, format):
    """Convert pair of datetime.date to string equivalents"""
    try:
        start_date = dates[0].strftime('%Y/%m/%d')
    except IndexError:
        start_date = None
        pass
    try:
        end_date = dates[1].strftime('%Y/%m/%d')
    except IndexError:
        end_date = None
        pass
    return start_date, end_date

def lov_predicate(colname, values):
    if not values:     # return empty string if no values
        return None
    lov = f"{colname} in ("
    for v in values:
        lov = lov + f"'{v}', "
    lov = lov[:-2] + ')'
    return lov

def compare_predicate(colname, operator, value, is_value_str=True):
    if value:
        if is_value_str:
            return f"{colname} {operator} '{value}'"
        else:
            return f"{colname} {operator} {value}"
    
def search_predicate(colname, searchstr):
    if searchstr:
        if searchstr[0] == "'":         # replace single quote with double
            searchstr = '"' + searchstr[1:-1:] + '"'
        searchstr = searchstr.replace("'", "''")
        return f"{colname} @@ websearch_to_tsquery('english', '{searchstr}')"

def daterange_predicate(colname, start_date, end_date, null_date, 
                        min_date, max_date):
    if (start_date == min_date or start_date is None) and \
       (end_date == max_date or end_date is None):
       if null_date: 
           return None # no predicate needed default state
       else:
           return f"{colname} is not null"
    else:
        daterange = "("
        if start_date:
            daterange += f"{compare_predicate(colname, ' >= ', start_date)}"
            if end_date:
                daterange += " and "
        if end_date:
            daterange += f"{compare_predicate(colname, ' <= ', end_date)}"
        if null_date:
            daterange += f" or {colname} is null)"
        else:
            daterange += ")"
    return daterange 

def entity_predicate(entities, all_entities):
    if not entities:
        return None
    quoted_entities = [f"'{entity}'" for entity in entities]
    entity_subquery = "doc_id in (select doc_id " + \
                "from entity_docs ed join entities e on ed.entity_id = e.entity_id " + \
                f"where e.entity in ({', '.join(quoted_entities)}) "
    if all_entities:
        entity_subquery += f"group by doc_id having count(*) = {len(entities)}"
    entity_subquery += ")"
    return entity_subquery

def add_predicate(predicates, text):
    if text:
        predicates.append(text)


def where_clause(predicates):
    if predicates:
        where = f"where {predicates[0]}"
    else:
        return ""
    for p in predicates[1:]:
        where += f" and {p}"

    return where

def query(template_name, table_name, where_clause, limit_clause=None):
    template = load_dynamic(template_name)
    limit_clause = f"limit {limit_clause}" if limit_clause else ""
    return template.format(table_name=table_name, where_clause=where_clause, limit_clause=limit_clause)


MAX_BARS = 90
def aggdate_expr(column_name, metrics):
    if metrics['day_cnt'] <= MAX_BARS:
        expr = f"to_char({column_name}, 'YYYY-MM-DD')"
        date_type = 'Date'
    elif metrics['mon_cnt'] <= MAX_BARS:
        expr = f"to_char({column_name}, 'YYYY-MM')"
        date_type = 'Month'
    elif metrics['yr_cnt'] <= MAX_BARS:
        expr = f"to_char({column_name}, 'YYYY')"
        date_type = 'Year'
    else:
        expr = f"to_char(date_trunc('decade', {column_name}), 'YYYY')"
        date_type = 'Decade'
    return expr, date_type

def aggquery(template_name, table_name, where_clause, agg_column):
    template = load_dynamic(template_name)
    return template.format(table_name=table_name, where_clause=where_clause,
                           agg_column=agg_column)

def by_doc_id(template_name, doc_id):
    template = load_dynamic(template_name)
    return template.format(doc_id=doc_id)
