from django.db.backends.signals import connection_created


def configure_sqlite_connection(sender, connection, **kwargs):
    if connection.vendor != "sqlite":
        return
    with connection.cursor() as cursor:
        cursor.execute("PRAGMA journal_mode=OFF;")


connection_created.connect(configure_sqlite_connection)

