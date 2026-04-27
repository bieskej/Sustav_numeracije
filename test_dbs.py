from __future__ import annotations

import psycopg


BASE_DSN = "postgresql://admin_user:admin_lozinka@localhost:5432"


def main() -> None:
    try:
        with psycopg.connect(f"{BASE_DSN}/postgres") as conn:
            role = conn.execute(
                """
                SELECT rolname, rolcreatedb, rolcreaterole, rolsuper
                FROM pg_roles
                WHERE rolname = current_user
                """
            ).fetchone()
            print(
                "Role privileges: "
                f"name={role[0]} createdb={role[1]} createrole={role[2]} superuser={role[3]}"
            )

        for db_name in ["numeracija", "postgres", "template1"]:
            try:
                with psycopg.connect(f"{BASE_DSN}/{db_name}") as conn:
                    row = conn.execute(
                        "select current_database(), current_user"
                    ).fetchone()
                    print(f"OK: connected to db={row[0]} user={row[1]}")
            except Exception as exc:
                print(f"FAIL: db={db_name}: {exc}")
    except Exception as exc:
        print(f"ERROR: {exc}")


if __name__ == "__main__":
    main()
