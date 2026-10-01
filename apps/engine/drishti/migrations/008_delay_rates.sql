-- Delay engine v2 (T051): past late counts per step of the ladder (agents/delay/rates.py), so
-- the engine can score ANY open work, including one recommended after the data was built.
-- Built by data/build_delay_rates.py. level: all | type | state_type | district_type | office.
CREATE TABLE IF NOT EXISTS delay_rates (
    level    text NOT NULL,
    key      text NOT NULL,
    n        integer NOT NULL,
    late     integer NOT NULL,
    version  text NOT NULL,
    PRIMARY KEY (level, key)
);
ALTER TABLE delay_rates ENABLE ROW LEVEL SECURITY;

-- Small learned models an engine applies to any work (T051), stored as data, e.g. the cost
-- engine's word-price model (agents/statistical/price_model.py, data/build_price_model.py).
CREATE TABLE IF NOT EXISTS engine_models (
    name     text PRIMARY KEY,
    version  text NOT NULL,
    data     jsonb NOT NULL
);
ALTER TABLE engine_models ENABLE ROW LEVEL SECURITY;
