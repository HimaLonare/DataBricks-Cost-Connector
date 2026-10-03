def collect_query_history(connection):
    """
    Collect query execution history from Databricks system tables.
    """

    cursor = connection.cursor()

    try:
        cursor.execute("""
            SELECT *
            FROM system.query.history
        """)

        rows = cursor.fetchall()

        return rows

    finally:
        cursor.close()