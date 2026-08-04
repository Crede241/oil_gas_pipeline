-- ============================================
-- Schéma dw_oil_gas - Modèle en étoile
-- ============================================

-- ---------- DIMENSIONS ----------

DROP TABLE IF EXISTS dim_time CASCADE;
CREATE TABLE dim_time (
    date_id      DATE PRIMARY KEY,
    day          INT NOT NULL,
    month        INT NOT NULL,
    quarter      INT NOT NULL,
    year         INT NOT NULL,
    week         INT NOT NULL
);

DROP TABLE IF EXISTS dim_field CASCADE;
CREATE TABLE dim_field (
    field_id        INT PRIMARY KEY,
    field_name      TEXT NOT NULL,
    country         TEXT,
    region          TEXT,
    discovery_year  INT
);

DROP TABLE IF EXISTS dim_well CASCADE;
CREATE TABLE dim_well (
    well_id     INT PRIMARY KEY,
    field_id    INT REFERENCES dim_field(field_id),
    well_name   TEXT NOT NULL,
    drill_date  DATE,
    depth_m     INT,
    status      TEXT
);

DROP TABLE IF EXISTS dim_equipment CASCADE;
CREATE TABLE dim_equipment (
    equipment_id    INT PRIMARY KEY,
    field_id        INT REFERENCES dim_field(field_id),
    well_id         INT REFERENCES dim_well(well_id),
    equipment_type  TEXT,
    install_date    DATE,
    status          TEXT
);

DROP TABLE IF EXISTS dim_employee CASCADE;
CREATE TABLE dim_employee (
    employee_id  INT PRIMARY KEY,
    full_name    TEXT NOT NULL,
    role         TEXT,
    field_id     INT REFERENCES dim_field(field_id),
    hire_date    DATE
);

-- ---------- FAITS ----------

DROP TABLE IF EXISTS fact_production CASCADE;
CREATE TABLE fact_production (
    production_id     BIGINT PRIMARY KEY,
    well_id            INT REFERENCES dim_well(well_id),
    date_id            DATE REFERENCES dim_time(date_id),
    barrels_extracted  NUMERIC(12,2),
    cost               NUMERIC(12,2),
    cost_per_barrel    NUMERIC(12,4)
);

DROP TABLE IF EXISTS fact_maintenance CASCADE;
CREATE TABLE fact_maintenance (
    maintenance_id  INT PRIMARY KEY,
    equipment_id    INT REFERENCES dim_equipment(equipment_id),
    date_id         DATE REFERENCES dim_time(date_id),
    failure_type    TEXT,
    downtime_hours  NUMERIC(10,2),
    cost            NUMERIC(12,2)
);

DROP TABLE IF EXISTS fact_sales CASCADE;
CREATE TABLE fact_sales (
    sale_id            INT PRIMARY KEY,
    date_id            DATE REFERENCES dim_time(date_id),
    field_id           INT REFERENCES dim_field(field_id),
    product_type       TEXT,
    quantity_barrels   NUMERIC(12,2),
    price_per_barrel   NUMERIC(10,2),
    revenue            NUMERIC(14,2)
);

-- Index utiles pour Power BI / requêtes fréquentes
CREATE INDEX idx_fact_production_well ON fact_production(well_id);
CREATE INDEX idx_fact_production_date ON fact_production(date_id);
CREATE INDEX idx_fact_sales_date ON fact_sales(date_id);
CREATE INDEX idx_fact_maintenance_equipment ON fact_maintenance(equipment_id);
