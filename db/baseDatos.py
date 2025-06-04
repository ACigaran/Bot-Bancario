import sqlite3
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DB_NAME = 'datos_del_usuario.db'

def setup_database_and_insert_examples():
    conn = None  
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        logger.info(f"Conectado a la base de datos '{DB_NAME}'.")

        # --- Eliminar tablas si existen (para poder re-ejecutar el script) ---
        logger.info("Eliminando tablas existentes (si las hay)...")
        cursor.execute("DROP TABLE IF EXISTS hmovimientos")
        cursor.execute("DROP TABLE IF EXISTS prestamos")
        cursor.execute("DROP TABLE IF EXISTS cuentas")
        cursor.execute("DROP TABLE IF EXISTS users")
        logger.info("Tablas anteriores eliminadas.")

        # --- Crear Tabla users ---
        cursor.execute('''
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                name TEXT,
                pin TEXT DEFAULT NULL  -- Nueva columna para el PIN (ej. '1234')
            )
        ''')
        logger.info("Tabla 'users' creada.")
        
        # --- Crear Tabla cuentas ---
        cursor.execute('''
            CREATE TABLE cuentas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                dinero REAL NOT NULL DEFAULT 0,
                currency TEXT,
                FOREIGN KEY (telegram_id) REFERENCES users (telegram_id)
            )
        ''')
        logger.info("Tabla 'cuentas' creada.")

        # --- Crear Tabla hmovimientos ---
        cursor.execute('''
            CREATE TABLE hmovimientos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL,
                account_id INTEGER NOT NULL,
                name TEXT NOT NULL, 
                dinero REAL NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (telegram_id) REFERENCES users (telegram_id),
                FOREIGN KEY (account_id) REFERENCES cuentas (id)
            )
        ''')
        logger.info("Tabla 'hmovimientos' creada.")

        # --- Crear Tabla prestamos ---
        cursor.execute('''
            CREATE TABLE prestamos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                dinero REAL NOT NULL,
                dineroEntregado REAL DEFAULT 0,
                due_date DATE,
                FOREIGN KEY (telegram_id) REFERENCES users (telegram_id)
            )
        ''')
        logger.info("Tabla 'prestamos' creada.")

        # --- Insertar datos de ejemplo ---
        logger.info("Insertando datos de ejemplo...")
        TU_TELEGRAM_ID_DE_PRUEBA = 1490296660
        user_name_prueba = "Agustin" 

        # 1. Insertar usuario de prueba
        cursor.execute("INSERT INTO users (telegram_id, name, pin) VALUES (?, ?, ?)",
                    (TU_TELEGRAM_ID_DE_PRUEBA, user_name_prueba, "1234")) 
        
        # 2. Insertar cuentas para el usuario de prueba
        cursor.execute("INSERT INTO cuentas (telegram_id, name, dinero, currency) VALUES (?, ?, ?, ?)",
                    (TU_TELEGRAM_ID_DE_PRUEBA, "Ahorro Pesos IceCash", 17000, "UYU"))
        cuenta_pesos_id = cursor.lastrowid # Obtenemos el ID de la cuenta recién insertada

        # Cuenta en Dólares
        cursor.execute("INSERT INTO cuentas (telegram_id, name, dinero, currency) VALUES (?, ?, ?, ?)",
                    (TU_TELEGRAM_ID_DE_PRUEBA, "Corriente Dólares IceCash", 550.75, "USD"))
        cuenta_dolares_id = cursor.lastrowid

        # 3. Insertar movimientos para la cuenta en pesos (usando cuenta_pesos_id)
        movimientos_data = [
            (TU_TELEGRAM_ID_DE_PRUEBA, cuenta_pesos_id, "Compra Supermercado", -1250.50),
            (TU_TELEGRAM_ID_DE_PRUEBA, cuenta_pesos_id, "Pago Factura Luz", -850.00),
            (TU_TELEGRAM_ID_DE_PRUEBA, cuenta_pesos_id, "Depósito Nómina", 25000.00),
            (TU_TELEGRAM_ID_DE_PRUEBA, cuenta_pesos_id, "Retiro Cajero", -2000.00),
        ]
        cursor.executemany("INSERT INTO hmovimientos (telegram_id, account_id, name, dinero) VALUES (?, ?, ?, ?)",
                        movimientos_data)

        # 4. Insertar préstamos para el usuario de prueba
        prestamos_data = [
            (TU_TELEGRAM_ID_DE_PRUEBA, "Préstamo Consumo Rápido", 50000, 10000, "2024-12-31"),
            (TU_TELEGRAM_ID_DE_PRUEBA, "Adelanto Vacaciones", 20000, 0, "2024-09-30")
        ]
        cursor.executemany("INSERT INTO prestamos (telegram_id, name, dinero, dineroEntregado, due_date) VALUES (?, ?, ?, ?, ?)",
                        prestamos_data)
        conn.commit()
        logger.info("Datos de ejemplo insertados y cambios guardados.")

    except sqlite3.Error as e:
        logger.error(f"Error de SQLite: {e}")
        if conn:
            conn.rollback() # Revertir cambios si algo falló
            logger.info("Rollback realizado debido a error.")
    except Exception as e:
        logger.error(f"Ocurrió un error inesperado: {e}")
        if conn:
            conn.rollback()
            logger.info("Rollback realizado debido a error inesperado.")
    finally:
        if conn:
            conn.close()
            logger.info(f"Conexión a la base de datos '{DB_NAME}' cerrada.")

if __name__ == "__main__":
    logger.info("Iniciando script de configuración de base de datos...")
    setup_database_and_insert_examples()
    logger.info(f"Script finalizado. La base de datos '{DB_NAME}' debería estar configurada.")
    logger.info(f"RECUERDA: Si no lo has hecho, cambia 'TU_TELEGRAM_ID_DE_PRUEBA' en el script por tu ID real.")