def collect_billing_usage(connection):
    cursor = connection.cursor()

    try:
        cursor.execute("""
            SELECT *
            FROM system.billing.usage
        """)

        rows = cursor.fetchall()

        return rows

    finally:
        cursor.close()