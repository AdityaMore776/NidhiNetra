-- T053: the delay prediction was removed (two methods, both ~0.70 AUC against a 0.80
-- target); its late-rate table is no longer read. Fund Flow counts live from the works.
DROP TABLE IF EXISTS delay_rates;
