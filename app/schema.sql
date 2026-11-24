-- 가게장부 스키마. 테이블 소유자는 gage_owner, 앱은 gage_app(비소유자)로 접속해 RLS를 강제로 받는다.
CREATE TABLE tenants (
  id         serial PRIMARY KEY,
  name       text NOT NULL,
  token_hash text NOT NULL UNIQUE          -- API 토큰의 sha256. 원문은 저장하지 않는다.
);

CREATE TABLE products (
  tenant_id int  NOT NULL REFERENCES tenants(id),
  sku       text NOT NULL,
  name      text NOT NULL,
  stock     int  NOT NULL CHECK (stock >= 0),
  PRIMARY KEY (tenant_id, sku)
);

CREATE TABLE orders (
  id         bigserial PRIMARY KEY,
  tenant_id  int  NOT NULL REFERENCES tenants(id),
  sku        text NOT NULL,
  qty        int  NOT NULL CHECK (qty > 0),
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE audit_log (                    -- 변경 기록 (S3: 12개월 보존)
  id        bigserial PRIMARY KEY,
  tenant_id int  NOT NULL,
  action    text NOT NULL,
  detail    jsonb,
  at        timestamptz NOT NULL DEFAULT now()
);

DO $$
DECLARE t text;
BEGIN
  FOREACH t IN ARRAY ARRAY['products', 'orders', 'audit_log'] LOOP
    EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', t);
    EXECUTE format('ALTER TABLE %I FORCE ROW LEVEL SECURITY', t);
    EXECUTE format($p$CREATE POLICY tenant_isolation ON %I
      USING (tenant_id = current_setting('app.tenant_id', true)::int)
      WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::int)$p$, t);
  END LOOP;
END $$;

GRANT SELECT ON tenants TO gage_app;
GRANT SELECT, UPDATE ON products TO gage_app;
GRANT SELECT, INSERT ON orders TO gage_app;
GRANT INSERT ON audit_log TO gage_app;           -- 감사로그는 앱이 지우거나 고칠 수 없다
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO gage_app;
