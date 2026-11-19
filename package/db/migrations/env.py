from alembic import context

# migrate.py がロックを取った接続を使い、テーブル変更と適用済みの版の記録をまとめて確定する。
connection = context.config.attributes["connection"]
context.configure(connection=connection)
with context.begin_transaction():
    context.run_migrations()
