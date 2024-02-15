


def get_clean_sql_schema(schema_version):
    schema_commands,  sql_command = [], ''
    sql_file = open(f'./utilities/schema_{schema_version}.sql','r')
    for line in sql_file:
        if not line.startswith('--') and line.strip('\n'):
            sql_command += line.strip('\n')
            if sql_command.endswith(';'):
                schema_commands.append(sql_command[:-1])
                sql_command = ''
    return schema_commands


def get_new_db_statements():
    schema_commands = []
    sql_file = open(f'./utilities/new_db_entries.sql', 'r')
    for line in sql_file:
        schema_commands.append(line)
    return schema_commands