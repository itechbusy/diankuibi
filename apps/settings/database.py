DATABASE_SETTING = {
    "default": {
        'ENGINE': 'dj_db_conn_pool.backends.postgresql',
        "NAME": "diankuibi",
        "USER": "postgres",
        "PASSWORD": "123456",
        "HOST": "host.docker.internal",
        "PORT": "5432",
        'POOL_OPTIONS': {
            'POOL_SIZE': 10,
            'MAX_OVERFLOW': 25,
            'RECYCLE': 1800,
            'TIMEOUT': 15
        },
        'CONN_MAX_AGE': 0,
        'OPTIONS': {
            'connect_timeout': 5,
            'sslmode': 'disable',
            'charset': 'utf8mb4',
            'client_encoding': 'UTF8'
        }
    }
}
