import os
import psycopg2
import psycopg2.extras
import json


class RedemptionCodeDB:

    DATABASE_CONFIG = {}

    def __init__(self):
        print("RedemptionCodeDB.__init__")

        self.DATABASE_CONFIG = {
            "host": os.environ['DATABASE_HOST'],
            "database": os.environ['DATABASE_NAME'],
            "user": os.environ['DATABASE_USER'],
            "password": os.environ['DATABASE_PASSWORD'],
            "sslmode": "require"
        }

        print("DATABASE_CONFIG: {0}".format(json.dumps(self.DATABASE_CONFIG, indent=4, sort_keys=True)))

    def dict_factory(self, cursor, row):
        d = {}
        for idx, col in enumerate(cursor.description):
            d[col[0]] = row[idx]
        return d

    def get_connection(self):
        print("get_connection()")
        conn = psycopg2.connect(**self.DATABASE_CONFIG)
        #conn.row_factory = self.dict_factory

        return conn

    def commit_close_connection(self, conn):
        print("commit_close_connection()")
        conn.commit()
        conn.close()

    def delete_redemption_code(self, redemption_code):
        print("delete_redemption_code()")
        result = "SUCCESS"
        conn = self.get_connection()
        cur = conn.cursor(cursor_factory = psycopg2.extras.RealDictCursor)
        params = (
            redemption_code,
        )
        cur.execute("""delete from redemption_code where "redeemCode"=%s;""", params)
        self.commit_close_connection(conn)

        return result

    def create_redemption_code(self, redemption_code, product_ref):
        print("create_redemption_code()")
        conn = self.get_connection()
        cur = conn.cursor(cursor_factory = psycopg2.extras.RealDictCursor)
        params = (
            redemption_code,
            product_ref,
        )
        cur.execute("""insert into redemption_code ("redeemCode", "productRef") values (%s, %s);""", params)
        cur.execute("""select * from redemption_code where "redeemCode"=%s;""", (redemption_code,))

        result = cur.fetchone()

        self.commit_close_connection(conn)

        return result

    def batch_create_redemption_code(self, params_list):
        print("batch_create_redemption_code()")
        conn = self.get_connection()
        cur = conn.cursor(cursor_factory = psycopg2.extras.RealDictCursor)
        sql = """insert into redemption_code ("redeemCode", "productRef") values ($1, $2)"""

        cur.execute("PREPARE stmt AS {0}".format(sql))
        psycopg2.extras.execute_batch(cur, "EXECUTE stmt (%s, %s)", params_list, page_size=100)
        cur.execute("DEALLOCATE stmt")

        print("Total Records Inserted")
        self.commit_close_connection(conn)

    def update_redemption_code(self, redemption_code_object):
        print("update_redemption_code()")
        conn = self.get_connection()
        cur = conn.cursor(cursor_factory = psycopg2.extras.RealDictCursor)
        params = (
            redemption_code_object["productRef"],
            redemption_code_object["firstName"],
            redemption_code_object["lastName"],
            redemption_code_object["address1"],
            redemption_code_object["address2"],
            redemption_code_object["city"],
            redemption_code_object["state"],
            redemption_code_object["postalCode"],
            redemption_code_object["country"],
            redemption_code_object["phone"],
            redemption_code_object["email"],
            redemption_code_object["tracking"],
            redemption_code_object["redeemCode"],
        )

        sql = """UPDATE redemption_code SET
            "productRef" = %s,
            "firstName" = %s,
            "lastName" = %s,
            "address1" = %s,
            "address2" = %s,
            "city" = %s,
            "state" = %s,
            "postalCode" = %s,
            "country" = %s,
            "phone" = %s,
            "email" = %s,
            "tracking" = %s,
            "updated" = CURRENT_TIMESTAMP
            WHERE "redeemCode" = %s;"""
        cur.execute(sql, params)
        cur.execute("""select * from redemption_code where "redeemCode"=%s;""", (redemption_code_object["redeemCode"],))

        result = cur.fetchone()

        self.commit_close_connection(conn)

        return result

    def get_redemption_code_by_code(self, redemption_code, conn=None):
        print("get_redemption_code_by_code()")
        sql = """select * from redemption_code where "redeemCode"=%s;"""
        result = None

        if(conn):
            cur = conn.cursor(cursor_factory = psycopg2.extras.RealDictCursor)
            cur.execute(sql, (redemption_code,))

            result = cur.fetchone()
        else:
            conn = self.get_connection()
            cur = conn.cursor(cursor_factory = psycopg2.extras.RealDictCursor)
            cur.execute(sql, (redemption_code,))

            result = cur.fetchone()

            self.commit_close_connection(conn)

        return result

    def get_unused_redemption_codes(self, rows_per_page, current_page):
        print("get_unused_redemption_codes()")
        conn = self.get_connection()
        cur = conn.cursor(cursor_factory = psycopg2.extras.RealDictCursor)
        cur.execute("""select "productRef", "redeemCode" from redemption_code
            where "tracking" is null and "city" is null
            and "firstName" is null
            and "state" is null
            order by "productRef", "redeemCode"
        LIMIT {rows_per_page} OFFSET {starting_row};""".format(
            rows_per_page=rows_per_page,
            starting_row=((current_page - 1) * rows_per_page) # Need to set an offset to get the right records
        ))

        result = cur.fetchall()

        cur.execute("""select count(*) as result_count
            from redemption_code
            where "tracking" is null and "city" is null
            and "firstName" is null
            and "state" is null""")

        result_count = cur.fetchone()["result_count"]

        print("result_count: {0}".format(result_count))

        self.commit_close_connection(conn)

        return result, result_count

    def get_pending_shipping_redemption_codes(self, rows_per_page, current_page):
        print("get_unused_redemption_codes()")
        conn = self.get_connection()
        cur = conn.cursor(cursor_factory = psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT
                "productRef",
                "redeemCode",
                "firstName",
                "lastName",
                "address1",
                "address2",
                "city",
                "state",
                "postalCode",
                "phone",
                "email",
                "tracking",
                "created",
                "updated",
                CASE
                    WHEN "tracking" is null or "tracking" = '' THEN 'PENDING SHIPPING'
                    ELSE 'SHIPPED'
                END as "status"
            FROM redemption_code
            WHERE "tracking" is null and "city" is not null and "firstName" is not null and "state" is not null order by "created"
            LIMIT {rows_per_page} OFFSET {starting_row};""".format(
            rows_per_page=rows_per_page,
            starting_row=((current_page - 1) * rows_per_page) # Need to set an offset to get the right records
        ))

        result = cur.fetchall()
        
        cur.execute("""select count(*) as result_count
            FROM redemption_code
            WHERE "tracking" is null and "city" is not null and "firstName" is not null and "state" is not null""")

        result_count = cur.fetchone()["result_count"]

        print("result_count: {0}".format(result_count))

        self.commit_close_connection(conn)

        return result, result_count

    def get_shipped_redemption_codes(self):
        print("get_unused_redemption_codes()")
        conn = self.get_connection()
        cur = conn.cursor(cursor_factory = psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT
                "productRef",
                "redeemCode",
                "firstName",
                "lastName",
                "address1",
                "address2",
                "city",
                "state",
                "postalCode",
                "phone",
                "email",
                "tracking",
                "created",
                "updated",
                CASE
                    WHEN "tracking" is null or "tracking" = '' THEN 'PENDING SHIPPING'
                    ELSE 'SHIPPED'
                END as "status"
            FROM redemption_code
            WHERE "tracking" is not null;""")

        result = cur.fetchall()

        self.commit_close_connection(conn)

        return result

    def get_all_used_redemption_codes(self):
        print("get_all_used_redemption_codes()")
        conn = self.get_connection()
        cur = conn.cursor(cursor_factory = psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT
                "productRef",
                "redeemCode",
                "firstName",
                "lastName",
                "address1",
                "address2",
                "city",
                "state",
                "postalCode",
                "phone",
                "email",
                "tracking",
                "created",
                "updated",
                CASE
                    WHEN "tracking" is null or "tracking" = '' THEN 'PENDING SHIPPING'
                    ELSE 'SHIPPED'
                END as "status"
            FROM redemption_code
            WHERE "firstName" is not null and "state" is not null order by "created";""")

        result = cur.fetchall()

        self.commit_close_connection(conn)

        return result

