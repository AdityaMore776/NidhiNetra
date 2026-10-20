-- ONE TIME ONLY (owner, 20 Oct 2026; T169): the cost forms and site visits saved before this
-- date were test data. A migration runs once per database (schema_migrations records it), so
-- this clears them once; a form or visit saved afterwards is never touched again, and a reload
-- of the works keeps them (drishti/reload.py).
--
-- Works whose assessment counted a submitted form keep that assessment until the next batch run
-- (data/batch_assess.py). The site-visits storage bucket keeps any frames the deleted rows named.
DELETE FROM site_visits;
DELETE FROM cost_forms;
