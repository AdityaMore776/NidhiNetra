"""The synthetic country: seeded, labelled beside the works, and made of made-up names."""

from drishti import reference
from drishti.evaluation.synthetic import Generator, spelling_variant


def test_the_same_seed_builds_the_same_country_and_another_seed_another():
    a, b = Generator(seed=5, small=True).build(), Generator(seed=5, small=True).build()
    c = Generator(seed=6, small=True).build()
    assert [w["work_id"] for w in a.works] == [w["work_id"] for w in b.works]
    assert [w["description"] for w in a.works] == [w["description"] for w in b.works]
    assert {w["district_name"] for w in a.works} != {w["district_name"] for w in c.works}


def test_labels_sit_beside_the_works_and_every_planted_kind_is_there():
    corpus = Generator(seed=5, small=True).build()
    ids = {w["work_id"] for w in corpus.works}
    assert set(corpus.labels) <= ids
    assert all("label" not in w and "kind" not in w for w in corpus.works)
    kinds = {lab.kind for lab in corpus.labels.values() if lab.positive}
    assert {"COST_X5", "REPEAT_AFTER_DONE", "SPLIT_SAME_SITE", "SPLIT_STRETCHES",
            "REPAIR_SOON_AFTER_BUILT", "RULE_TEMPLE", "OFFICE_PRICES_AT_LIMIT"} <= kinds
    assert all(lab.meant and lab.codes for lab in corpus.labels.values() if lab.positive)


def test_a_village_spelt_otherwise_is_still_close_to_itself():
    import random

    rng = random.Random(1)
    for name in ("Chakwa", "Ghurpur", "Belauli", "Sargaon"):
        v = spelling_variant(name, rng)
        assert v != name and v[0].lower() == name[0].lower()


def test_esakshi_categories_map_to_work_types_and_never_guess():
    road = "Construction of roads, link roads, pathways or any other road with or without " \
           "drainage system"
    assert reference.esakshi_type(road, "CC road at Rampur") == "ROAD_CC"
    assert reference.esakshi_type(road, "Black topping of road at Rampur") == "ROAD_BT"
    assert reference.esakshi_type(road, "Paver block work in lane") == "FOOTPATH"
    assert reference.esakshi_type("Lighting of public spaces") == "STREET_LIGHT"
    assert reference.esakshi_type("  lighting OF public   spaces ") == "STREET_LIGHT"
    assert reference.esakshi_type("A category never seen") is None
    assert reference.work_type_name("EMBANKMENT") == "Flood embankment / protection wall"
