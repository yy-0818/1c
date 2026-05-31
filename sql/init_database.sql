-- =============================================
-- 1C Clobus 数据库初始化脚本
-- 在 Supabase SQL 编辑器中执行
-- =============================================

-- 启用 UUID 扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =============================================
-- 客户数据表 (Catalog_Контрагенты)
-- =============================================
CREATE TABLE IF NOT EXISTS customers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ref_key UUID UNIQUE NOT NULL,
    code TEXT,
    description TEXT NOT NULL,
    description_full TEXT,
    inn TEXT,
    kpp TEXT,
    legal_entity_type TEXT,
    is_folder BOOLEAN DEFAULT FALSE,
    parent_key UUID,
    parent_path TEXT[],
    phone_work TEXT,
    phone_mobile TEXT,
    email TEXT,
    address_legal TEXT,
    address_actual TEXT,
    deletion_mark BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    last_synced_at TIMESTAMPTZ DEFAULT NOW()
);

-- 客户银行账户
CREATE TABLE IF NOT EXISTS customer_bank_accounts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id UUID NOT NULL,
    ref_key UUID UNIQUE NOT NULL,
    bank_name TEXT,
    bik TEXT,
    account_number TEXT,
    account_name TEXT,
    correspondent_account TEXT,
    is_default BOOLEAN DEFAULT FALSE,
    deletion_mark BOOLEAN DEFAULT FALSE,
    last_synced_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT fk_customer_bank_customers FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE
);

-- =============================================
-- 产品数据表 (Catalog_Номенклатура)
-- =============================================
CREATE TABLE IF NOT EXISTS products (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ref_key UUID UNIQUE NOT NULL,
    code TEXT,
    description TEXT NOT NULL,
    description_full TEXT,
    article TEXT,
    product_type TEXT,
    is_folder BOOLEAN DEFAULT FALSE,
    parent_key UUID,
    parent_path TEXT[],
    unit_ref_key UUID,
    unit_name TEXT,
    vat_rate TEXT,
    weight DECIMAL(10,3),
    is_group BOOLEAN DEFAULT FALSE,
    deletion_mark BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    last_synced_at TIMESTAMPTZ DEFAULT NOW()
);

-- 产品价格表
CREATE TABLE IF NOT EXISTS product_prices (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    product_id UUID NOT NULL,
    ref_key UUID UNIQUE NOT NULL,
    price_type TEXT NOT NULL,
    price DECIMAL(18,4) NOT NULL,
    currency TEXT DEFAULT 'UZS',
    unit_ref_key UUID,
    unit_name TEXT,
    valid_from DATE,
    valid_until DATE,
    deletion_mark BOOLEAN DEFAULT FALSE,
    last_synced_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT fk_product_prices_product FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
);

-- =============================================
-- 库存数据表
-- =============================================
CREATE TABLE IF NOT EXISTS inventory (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    product_id UUID NOT NULL,
    ref_key UUID UNIQUE NOT NULL,
    warehouse_ref_key UUID,
    warehouse_name TEXT NOT NULL,
    store_ref_key UUID,
    store_name TEXT,
    quantity DECIMAL(18,3) DEFAULT 0,
    reserved_quantity DECIMAL(18,3) DEFAULT 0,
    available_quantity DECIMAL(18,3),
    period DATE,
    record_type TEXT,
    deletion_mark BOOLEAN DEFAULT FALSE,
    last_synced_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT fk_inventory_product FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
);

-- 库存快照表
CREATE TABLE IF NOT EXISTS inventory_snapshots (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    product_id UUID NOT NULL,
    warehouse_name TEXT NOT NULL,
    quantity DECIMAL(18,3),
    reserved_quantity DECIMAL(18,3),
    available_quantity DECIMAL(18,3),
    snapshot_date DATE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT fk_inventory_snapshot_product FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
    CONSTRAINT uq_inventory_snapshot_unique UNIQUE (product_id, warehouse_name, snapshot_date)
);

-- =============================================
-- 销售订单表
-- =============================================
CREATE TABLE IF NOT EXISTS orders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ref_key UUID UNIQUE NOT NULL,
    document_type TEXT NOT NULL,
    order_number TEXT,
    order_date TIMESTAMPTZ NOT NULL,
    due_date DATE,
    status TEXT,
    status_reason TEXT,
    customer_id UUID,
    customer_name TEXT,
    customer_inn TEXT,
    partner_ref_key UUID,
    agreement_ref_key UUID,
    agreement_name TEXT,
    contract_ref_key UUID,
    contract_number TEXT,
    legal_entity_id UUID,
    legal_entity_name TEXT,
    warehouse_ref_key UUID,
    warehouse_name TEXT,
    subtotal DECIMAL(18,2),
    discount_amount DECIMAL(18,2) DEFAULT 0,
    vat_amount DECIMAL(18,2),
    total_amount DECIMAL(18,2),
    currency TEXT DEFAULT 'UZS',
    exchange_rate DECIMAL(18,6) DEFAULT 1,
    delivery_address TEXT,
    comment TEXT,
    author_name TEXT,
    deletion_mark BOOLEAN DEFAULT FALSE,
    posted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    last_synced_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT fk_orders_customer FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE SET NULL
);

-- 订单明细表
CREATE TABLE IF NOT EXISTS order_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    order_id UUID NOT NULL,
    line_number INTEGER,
    product_id UUID,
    product_ref_key UUID,
    product_name TEXT NOT NULL,
    product_sku TEXT,
    unit_ref_key UUID,
    unit_name TEXT,
    quantity DECIMAL(18,3) NOT NULL,
    unit_price DECIMAL(18,4),
    discount_percent DECIMAL(5,2) DEFAULT 0,
    discount_amount DECIMAL(18,2) DEFAULT 0,
    vat_rate TEXT,
    vat_amount DECIMAL(18,2),
    amount DECIMAL(18,2) NOT NULL,
    reserved_quantity DECIMAL(18,3) DEFAULT 0,
    shipment_date DATE,
    cancellation_reason TEXT,
    is_cancelled BOOLEAN DEFAULT FALSE,
    deletion_mark BOOLEAN DEFAULT FALSE,
    last_synced_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT fk_order_items_order FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
    CONSTRAINT fk_order_items_product FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE SET NULL
);

-- =============================================
-- 财务凭证表
-- =============================================
CREATE TABLE IF NOT EXISTS accounting_entries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ref_key UUID UNIQUE NOT NULL,
    entry_number TEXT,
    entry_date DATE NOT NULL,
    period_year INTEGER,
    period_month INTEGER,
    description TEXT,
    accounting_type TEXT,
    source_document_type TEXT,
    source_document_ref_key UUID,
    source_document_number TEXT,
    company_ref_key UUID,
    company_name TEXT,
    account_code TEXT NOT NULL,
    account_name TEXT,
    account_type TEXT,
    debit DECIMAL(18,2) DEFAULT 0,
    credit DECIMAL(18,2) DEFAULT 0,
    currency TEXT DEFAULT 'UZS',
    currency_amount DECIMAL(18,2),
    analytics_type TEXT,
    analytics_ref_key UUID,
    analytics_name TEXT,
    deletion_mark BOOLEAN DEFAULT FALSE,
    posted BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_synced_at TIMESTAMPTZ DEFAULT NOW()
);

-- 科目余额表
CREATE TABLE IF NOT EXISTS account_balances (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_ref_key UUID NOT NULL,
    company_name TEXT,
    account_code TEXT NOT NULL,
    account_name TEXT,
    account_type TEXT,
    period_year INTEGER NOT NULL,
    period_month INTEGER NOT NULL,
    opening_debit DECIMAL(18,2) DEFAULT 0,
    opening_credit DECIMAL(18,2) DEFAULT 0,
    debit_turnover DECIMAL(18,2) DEFAULT 0,
    credit_turnover DECIMAL(18,2) DEFAULT 0,
    closing_debit DECIMAL(18,2) DEFAULT 0,
    closing_credit DECIMAL(18,2) DEFAULT 0,
    currency TEXT DEFAULT 'UZS',
    last_synced_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT uq_account_balance_unique UNIQUE (company_ref_key, account_code, period_year, period_month, currency)
);

-- =============================================
-- 报表数据表
-- =============================================
CREATE TABLE IF NOT EXISTS reports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    report_type TEXT NOT NULL,
    report_name TEXT,
    report_date DATE NOT NULL,
    period_start DATE,
    period_end DATE,
    company_ref_key UUID,
    company_name TEXT,
    currency TEXT DEFAULT 'UZS',
    data JSONB NOT NULL,
    summary JSONB,
    parameters JSONB,
    generated_by TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_synced_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT uq_report_unique UNIQUE (report_type, company_ref_key, period_start, period_end)
);

-- =============================================
-- 同步日志表
-- =============================================
CREATE TABLE IF NOT EXISTS sync_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    sync_type TEXT NOT NULL,
    sync_mode TEXT DEFAULT 'full',
    status TEXT NOT NULL,
    records_processed INTEGER DEFAULT 0,
    records_created INTEGER DEFAULT 0,
    records_updated INTEGER DEFAULT 0,
    records_deleted INTEGER DEFAULT 0,
    records_failed INTEGER DEFAULT 0,
    error_message TEXT,
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    duration_seconds INTEGER
);

-- =============================================
-- 索引
-- =============================================
CREATE INDEX IF NOT EXISTS idx_customers_ref_key ON customers(ref_key);
CREATE INDEX IF NOT EXISTS idx_customers_inn ON customers(inn);
CREATE INDEX IF NOT EXISTS idx_customers_parent ON customers(parent_key);
CREATE INDEX IF NOT EXISTS idx_customers_deletion ON customers(deletion_mark) WHERE deletion_mark = TRUE;
CREATE INDEX IF NOT EXISTS idx_customers_updated ON customers(updated_at);

CREATE INDEX IF NOT EXISTS idx_customer_bank_accounts_customer ON customer_bank_accounts(customer_id);
CREATE INDEX IF NOT EXISTS idx_customer_bank_accounts_ref ON customer_bank_accounts(ref_key);

CREATE INDEX IF NOT EXISTS idx_products_ref_key ON products(ref_key);
CREATE INDEX IF NOT EXISTS idx_products_article ON products(article);
CREATE INDEX IF NOT EXISTS idx_products_parent ON products(parent_key);
CREATE INDEX IF NOT EXISTS idx_products_deletion ON products(deletion_mark) WHERE deletion_mark = TRUE;
CREATE INDEX IF NOT EXISTS idx_products_updated ON products(updated_at);

CREATE INDEX IF NOT EXISTS idx_product_prices_product ON product_prices(product_id);
CREATE INDEX IF NOT EXISTS idx_product_prices_type ON product_prices(price_type);

CREATE INDEX IF NOT EXISTS idx_inventory_product ON inventory(product_id);
CREATE INDEX IF NOT EXISTS idx_inventory_warehouse ON inventory(warehouse_name);
CREATE INDEX IF NOT EXISTS idx_inventory_period ON inventory(period);

CREATE INDEX IF NOT EXISTS idx_orders_ref_key ON orders(ref_key);
CREATE INDEX IF NOT EXISTS idx_orders_number ON orders(order_number);
CREATE INDEX IF NOT EXISTS idx_orders_customer ON orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_orders_date ON orders(order_date);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS idx_orders_deletion ON orders(deletion_mark) WHERE deletion_mark = TRUE;

CREATE INDEX IF NOT EXISTS idx_order_items_order ON order_items(order_id);
CREATE INDEX IF NOT EXISTS idx_order_items_product ON order_items(product_id);

CREATE INDEX IF NOT EXISTS idx_accounting_ref_key ON accounting_entries(ref_key);
CREATE INDEX IF NOT EXISTS idx_accounting_date ON accounting_entries(entry_date);
CREATE INDEX IF NOT EXISTS idx_accounting_account ON accounting_entries(account_code);
CREATE INDEX IF NOT EXISTS idx_accounting_company ON accounting_entries(company_ref_key);

CREATE INDEX IF NOT EXISTS idx_account_balances_company ON account_balances(company_ref_key);
CREATE INDEX IF NOT EXISTS idx_account_balances_account ON account_balances(account_code);
CREATE INDEX IF NOT EXISTS idx_account_balances_period ON account_balances(period_year, period_month);

CREATE INDEX IF NOT EXISTS idx_reports_type_date ON reports(report_type, report_date);
CREATE INDEX IF NOT EXISTS idx_reports_company ON reports(company_ref_key);

CREATE INDEX IF NOT EXISTS idx_sync_logs_type ON sync_logs(sync_type);
CREATE INDEX IF NOT EXISTS idx_sync_logs_status ON sync_logs(status);
CREATE INDEX IF NOT EXISTS idx_sync_logs_started ON sync_logs(started_at DESC);

-- =============================================
-- 视图
-- =============================================
CREATE OR REPLACE VIEW v_active_customers AS
SELECT * FROM customers WHERE deletion_mark = FALSE;

CREATE OR REPLACE VIEW v_active_products AS
SELECT * FROM products WHERE deletion_mark = FALSE;

CREATE OR REPLACE VIEW v_pending_orders AS
SELECT 
    o.id, o.ref_key, o.order_number, o.order_date, o.status, o.total_amount, o.currency,
    o.customer_id, o.customer_name as order_customer_name, 
    c.description as customer_name, c.inn as customer_inn,
    o.created_at, o.updated_at
FROM orders o
LEFT JOIN customers c ON o.customer_id = c.id
WHERE o.deletion_mark = FALSE AND o.status NOT IN ('Completed', 'Cancelled');

CREATE OR REPLACE VIEW v_monthly_sales AS
SELECT 
    DATE_TRUNC('month', order_date) as month,
    COUNT(*) as order_count,
    SUM(total_amount) as total_sales,
    currency
FROM orders
WHERE deletion_mark = FALSE AND posted = TRUE
GROUP BY DATE_TRUNC('month', order_date), currency;

-- =============================================
-- 触发器
-- =============================================
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS tr_customers_updated_at ON customers;
CREATE TRIGGER tr_customers_updated_at 
    BEFORE UPDATE ON customers 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

DROP TRIGGER IF EXISTS tr_products_updated_at ON products;
CREATE TRIGGER tr_products_updated_at 
    BEFORE UPDATE ON products 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

DROP TRIGGER IF EXISTS tr_orders_updated_at ON orders;
CREATE TRIGGER tr_orders_updated_at 
    BEFORE UPDATE ON orders 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

DROP TRIGGER IF EXISTS tr_order_items_updated_at ON order_items;
CREATE TRIGGER tr_order_items_updated_at 
    BEFORE UPDATE ON order_items 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

DROP TRIGGER IF EXISTS tr_accounting_updated_at ON accounting_entries;
CREATE TRIGGER tr_accounting_updated_at 
    BEFORE UPDATE ON accounting_entries 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- =============================================
-- RLS 策略 (可选启用)
-- =============================================
-- ALTER TABLE customers ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE products ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE orders ENABLE ROW LEVEL SECURITY;

-- 示例策略
-- CREATE POLICY customers_select ON customers FOR SELECT USING (deletion_mark = FALSE);
-- CREATE POLICY products_select ON products FOR SELECT USING (deletion_mark = FALSE);
-- CREATE POLICY orders_select ON orders FOR SELECT USING (deletion_mark = FALSE);

-- =============================================
-- 存储过程
-- =============================================
CREATE OR REPLACE FUNCTION get_customer_stats()
RETURNS TABLE (
    total_count BIGINT,
    active_count BIGINT,
    deleted_count BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        COUNT(*)::BIGINT,
        COUNT(*) FILTER (WHERE deletion_mark = FALSE)::BIGINT,
        COUNT(*) FILTER (WHERE deletion_mark = TRUE)::BIGINT
    FROM customers;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION get_product_stats()
RETURNS TABLE (
    total_count BIGINT,
    active_count BIGINT,
    deleted_count BIGINT,
    categories_count BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        COUNT(*)::BIGINT,
        COUNT(*) FILTER (WHERE deletion_mark = FALSE)::BIGINT,
        COUNT(*) FILTER (WHERE deletion_mark = TRUE)::BIGINT,
        COUNT(DISTINCT parent_key) FILTER (WHERE is_folder = TRUE)::BIGINT
    FROM products;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION get_order_stats(
    p_start_date DATE DEFAULT NULL,
    p_end_date DATE DEFAULT NULL
)
RETURNS TABLE (
    total_orders BIGINT,
    total_amount DECIMAL(18,2),
    pending_orders BIGINT,
    completed_orders BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        COUNT(*)::BIGINT,
        COALESCE(SUM(total_amount), 0)::DECIMAL(18,2),
        COUNT(*) FILTER (WHERE status NOT IN ('Completed', 'Cancelled'))::BIGINT,
        COUNT(*) FILTER (WHERE status IN ('Completed'))::BIGINT
    FROM orders o
    WHERE (p_start_date IS NULL OR o.order_date >= p_start_date)
      AND (p_end_date IS NULL OR o.order_date <= p_end_date);
END;
$$ LANGUAGE plpgsql;

-- =============================================
-- 注释
-- =============================================
COMMENT ON TABLE customers IS '客户数据表 (Catalog_Контрагенты)';
COMMENT ON TABLE customer_bank_accounts IS '客户银行账户表';
COMMENT ON TABLE products IS '产品数据表 (Catalog_Номенклатура)';
COMMENT ON TABLE product_prices IS '产品价格表';
COMMENT ON TABLE inventory IS '库存数据表';
COMMENT ON TABLE inventory_snapshots IS '库存历史快照';
COMMENT ON TABLE orders IS '销售订单表 (Document_ЗаказКлиента)';
COMMENT ON TABLE order_items IS '订单明细表';
COMMENT ON TABLE accounting_entries IS '财务凭证表';
COMMENT ON TABLE account_balances IS '科目余额表';
COMMENT ON TABLE reports IS '报表数据表';
COMMENT ON TABLE sync_logs IS '同步日志表';

-- =============================================
-- 授予权限 (根据需要调整)
-- =============================================
-- GRANT SELECT ON ALL TABLES IN SCHEMA public TO anon;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO authenticated;
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO service_role;

-- =============================================
-- 完成提示
-- =============================================
DO $$
BEGIN
    RAISE NOTICE 'Database initialization completed successfully!';
END $$;
