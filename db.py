import sqlite3


class RedemptionCodeDB:

    DB_FILE = None

    def __init__(self, db_file_path_and_name):
        print("RedemptionCodeDB.__init__")
        print("db_file_path_and_name: {0}".format(db_file_path_and_name))
        self.DB_FILE = db_file_path_and_name

    def dict_factory(self, cursor, row):
        d = {}
        for idx, col in enumerate(cursor.description):
            d[col[0]] = row[idx]
        return d

    def get_connection(self):
        print("get_connection()")
        conn = sqlite3.connect(self.DB_FILE)
        conn.row_factory = self.dict_factory

        return conn

    def commit_close_connection(self, conn):
        print("commit_close_connection()")
        conn.commit()
        conn.close()

    def delete_redemption_code(self, redemption_code):
        print("delete_redemption_code()")
        result = "SUCCESS"
        conn = self.get_connection()
        cur = conn.cursor()
        params = (
            redemption_code,
        )
        cur.execute("delete from redemption_code where redeemCode=?;", params)
        self.commit_close_connection(conn)

        return result

    def create_redemption_code(self, redemption_code, product_ref):
        print("create_redemption_code()")
        conn = self.get_connection()
        cur = conn.cursor()
        params = (
            redemption_code,
            product_ref,
        )
        cur.execute("insert into redemption_code (redeemCode, productRef) values (?, ?);", params)
        cur.execute("select * from redemption_code where redeemCode=?;", (redemption_code,))

        result = cur.fetchone()

        self.commit_close_connection(conn)

        return result

    def update_redemption_code(self, redemption_code_object):
        print("update_redemption_code()")
        conn = self.get_connection()
        cur = conn.cursor()
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
            productRef = ?,
            firstName = ?,
            lastName = ?,
            address1 = ?,
            address2 = ?,
            city = ?,
            state = ?,
            postalCode = ?,
            country = ?,
            phone = ?,
            email = ?,
            tracking = ?,
            updated = CURRENT_TIMESTAMP
            WHERE redeemCode = ?;"""
        cur.execute(sql, params)
        cur.execute("select * from redemption_code where redeemCode=?;", (redemption_code_object["redeemCode"],))

        result = cur.fetchone()

        self.commit_close_connection(conn)

        return result

    def get_redemption_code_by_code(self, redemption_code):
        print("get_redemption_code_by_code()")
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute("select * from redemption_code where redeemCode=?;", (redemption_code,))

        result = cur.fetchone()

        self.commit_close_connection(conn)

        return result

    def get_unused_redemption_codes(self):
        print("get_unused_redemption_codes()")
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute("select productRef, redeemCode from redemption_code where tracking is null and city is null and firstName is null and state is null order by productRef, redeemCode;")

        result = cur.fetchall()

        self.commit_close_connection(conn)

        return result

    def get_pending_shipping_redemption_codes(self):
        print("get_unused_redemption_codes()")
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT
                productRef,
                redeemCode,
                firstName,
                lastName,
                address1,
                address2,
                city,
                state,
                postalCode,
                phone,
                email,
                tracking,
                created,
                updated,
                CASE
                    WHEN tracking is null or tracking = '' THEN 'PENDING SHIPPING'
                    ELSE 'SHIPPED'
                END as status
            FROM redemption_code
            WHERE tracking is null and city is not null and firstName is not null and state is not null order by created;""")

        result = cur.fetchall()

        self.commit_close_connection(conn)

        return result

    def get_shipped_redemption_codes(self):
        print("get_unused_redemption_codes()")
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT
                productRef,
                redeemCode,
                firstName,
                lastName,
                address1,
                address2,
                city,
                state,
                postalCode,
                phone,
                email,
                tracking,
                created,
                updated,
                CASE
                    WHEN tracking is null or tracking = '' THEN 'PENDING SHIPPING'
                    ELSE 'SHIPPED'
                END as status
            FROM redemption_code
            WHERE tracking is not null;""")

        result = cur.fetchall()

        self.commit_close_connection(conn)

        return result

    def get_all_used_redemption_codes(self):
        print("get_all_used_redemption_codes()")
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT
                productRef,
                redeemCode,
                firstName,
                lastName,
                address1,
                address2,
                city,
                state,
                postalCode,
                phone,
                email,
                tracking,
                created,
                updated,
                CASE
                    WHEN tracking is null or tracking = '' THEN 'PENDING SHIPPING'
                    ELSE 'SHIPPED'
                END as status
            FROM redemption_code
            WHERE firstName is not null and state is not null order by created;""")

        result = cur.fetchall()

        self.commit_close_connection(conn)

        return result

