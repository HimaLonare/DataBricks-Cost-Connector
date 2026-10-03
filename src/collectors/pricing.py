def collect_list_prices(connection):
    cursor = connection.cursor()

    try:
        cursor.execute("""
            SELECT *
            FROM system.billing.list_prices
        """)

        rows = cursor.fetchall()

        return rows

    finally:
        cursor.close()