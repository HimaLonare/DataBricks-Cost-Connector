def collect_warehouse_events(connection):
    cursor = connection.cursor()

    try:
        cursor.execute("""
            SELECT *
            FROM system.compute.warehouse_events
        """)

        rows = cursor.fetchall()

        return rows

    finally:
        cursor.close()


def collect_warehouses(connection):
    cursor = connection.cursor()

    try:
        cursor.execute("""
            SELECT *
            FROM system.compute.warehouses
        """)

        rows = cursor.fetchall()

        return rows

    finally:
        cursor.close()


def collect_node_types(connection):
    cursor = connection.cursor()

    try:
        cursor.execute("""
            SELECT *
            FROM system.compute.node_types
        """)

        rows = cursor.fetchall()

        return rows

    finally:
        cursor.close()