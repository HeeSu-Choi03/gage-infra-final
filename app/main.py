"""가게장부 API. 매장(테넌트) 격리는 앱이 아니라 PostgreSQL RLS가 최종적으로 보장한다."""
import hashlib, json, os, socket

import psycopg
import redis
from fastapi import Depends, FastAPI, Header, HTTPException
from psycopg_pool import ConnectionPool
from pydantic import BaseModel, Field

pool = ConnectionPool(os.environ["DATABASE_URL"], min_size=2, max_size=10, open=True)
cache = redis.Redis.from_url(os.environ["REDIS_URL"], socket_timeout=0.2, socket_connect_timeout=0.2)
HOST = socket.gethostname()
app = FastAPI(title="gage")


def cache_get(key):
    try:
        v = cache.get(key)
        return json.loads(v) if v else None
    except redis.RedisError:
        return None  # 캐시 장애 → DB로 폴백 (SPOF 아님)


def cache_set(key, value, ttl=10):
    try:
        cache.set(key, json.dumps(value), ex=ttl)
    except redis.RedisError:
        pass


def cache_del(key):
    try:
        cache.delete(key)
    except redis.RedisError:
        pass


def tenant_id(authorization: str = Header(default="")) -> int:
    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(401, "missing token")
    digest = hashlib.sha256(token.encode()).hexdigest()
    with pool.connection() as conn:
        row = conn.execute("SELECT id FROM tenants WHERE token_hash = %s", (digest,)).fetchone()
    if not row:
        raise HTTPException(401, "invalid token")
    return row[0]


def tenant_conn(tid: int):
    """테넌트 컨텍스트를 건 트랜잭션. RLS 정책이 app.tenant_id로 행을 거른다."""
    conn = pool.getconn()
    conn.execute("SELECT set_config('app.tenant_id', %s, true)", (str(tid),))
    return conn


@app.get("/healthz")
def healthz():
    return {"ok": True, "host": HOST}


@app.get("/readyz")
def readyz():
    with pool.connection() as conn:
        conn.execute("SELECT 1")
    return {"ok": True, "host": HOST}


@app.get("/products")
def products(tid: int = Depends(tenant_id)):
    key = f"products:{tid}"
    if (hit := cache_get(key)) is not None:
        return {"host": HOST, "cache": "hit", "items": hit}
    conn = tenant_conn(tid)
    try:
        rows = conn.execute("SELECT sku, name, stock FROM products ORDER BY sku").fetchall()
        conn.commit()
    finally:
        pool.putconn(conn)
    items = [{"sku": s, "name": n, "stock": st} for s, n, st in rows]
    cache_set(key, items)
    return {"host": HOST, "cache": "miss", "items": items}


@app.get("/products/all-tenants")
def products_unscoped(tid: int = Depends(tenant_id)):
    """보안 시험용: 테넌트 필터 없이 전체를 조회해도 RLS 때문에 내 매장 행만 나와야 한다."""
    conn = tenant_conn(tid)
    try:
        rows = conn.execute("SELECT tenant_id, count(*) FROM products GROUP BY tenant_id").fetchall()
        conn.commit()
    finally:
        pool.putconn(conn)
    return {"visible_tenants": {str(t): c for t, c in rows}}


class Order(BaseModel):
    sku: str = Field(max_length=32)
    qty: int = Field(gt=0, le=100)


@app.post("/orders", status_code=201)
def create_order(order: Order, tid: int = Depends(tenant_id)):
    conn = tenant_conn(tid)
    try:
        cur = conn.execute(
            "UPDATE products SET stock = stock - %s WHERE sku = %s AND stock >= %s RETURNING stock",
            (order.qty, order.sku, order.qty))
        row = cur.fetchone()
        if not row:
            conn.rollback()
            raise HTTPException(409, "out of stock or unknown sku")
        oid = conn.execute(
            "INSERT INTO orders (tenant_id, sku, qty) VALUES (%s, %s, %s) RETURNING id",
            (tid, order.sku, order.qty)).fetchone()[0]
        conn.execute("INSERT INTO audit_log (tenant_id, action, detail) VALUES (%s, 'order', %s)",
                     (tid, json.dumps({"order": oid, "sku": order.sku, "qty": order.qty})))
        conn.commit()
    except psycopg.Error:
        conn.rollback()
        raise
    finally:
        pool.putconn(conn)
    cache_del(f"products:{tid}")
    return {"host": HOST, "order_id": oid, "stock_left": row[0]}


@app.get("/orders")
def list_orders(tid: int = Depends(tenant_id)):
    conn = tenant_conn(tid)
    try:
        rows = conn.execute(
            "SELECT id, sku, qty, created_at FROM orders ORDER BY id DESC LIMIT 20").fetchall()
        conn.commit()
    finally:
        pool.putconn(conn)
    return {"host": HOST, "orders": [{"id": i, "sku": s, "qty": q, "at": a.isoformat()} for i, s, q, a in rows]}
