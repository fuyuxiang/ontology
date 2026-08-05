"""EntityRepository.get_ontology_stats 的归属与计数规则测试。"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import EntityRelation, OntologyEntity, ScenarioDict
from app.models.action import EntityAction
from app.models.function import OntologyFunction
from app.models.shared_ref import OntologySharedRef
from app.repositories.entity_repo import EntityRepository


@pytest.fixture()
def db():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


def _ontology(db, oid, code):
    sc = ScenarioDict(id=oid, code=code, name=code)
    db.add(sc)
    return sc


def _entity(db, eid, ontology_id, name=None):
    e = OntologyEntity(
        id=eid, name=name or eid, name_cn=name or eid, tier=1,
        status="active", ontology_id=ontology_id,
    )
    db.add(e)
    return e


def test_counts_owned_entities_and_components(db):
    _ontology(db, "o1", "alpha")
    _entity(db, "e1", "o1")
    _entity(db, "e2", "o1")
    db.add(EntityRelation(
        id="r1", from_entity_id="e1", to_entity_id="e2",
        name="rel", rel_type="assoc", cardinality="1:1",
    ))
    db.add(OntologyFunction(id="f1", entity_id="e1", name="fn"))
    db.add(EntityAction(id="a1", entity_id="e1", name="act", category="operation", action_type="http"))
    db.commit()

    stats = EntityRepository(db).get_ontology_stats()
    assert stats["o1"] == {
        "entity_count": 2, "relation_count": 1, "logic_count": 1, "action_count": 1,
    }


def test_shared_entity_counted_in_both_ontologies(db):
    _ontology(db, "o1", "alpha")
    _ontology(db, "o2", "beta")
    _entity(db, "e1", "o1")
    db.add(OntologySharedRef(id="s1", source_ontology_id="o1", target_ontology_id="o2", entity_id="e1"))
    db.add(OntologyFunction(id="f1", entity_id="e1", name="fn"))
    db.commit()

    stats = EntityRepository(db).get_ontology_stats()
    assert stats["o1"]["entity_count"] == 1
    assert stats["o2"]["entity_count"] == 1
    # 共享实体的逻辑在两个本体下都可见，与 list_with_filters 的 OR 条件一致
    assert stats["o1"]["logic_count"] == 1
    assert stats["o2"]["logic_count"] == 1


def test_cross_ontology_relation_not_counted(db):
    _ontology(db, "o1", "alpha")
    _ontology(db, "o2", "beta")
    _entity(db, "e1", "o1")
    _entity(db, "e2", "o2")
    db.add(EntityRelation(
        id="r1", from_entity_id="e1", to_entity_id="e2",
        name="rel", rel_type="assoc", cardinality="1:1",
    ))
    db.commit()

    stats = EntityRepository(db).get_ontology_stats()
    # 两端不同本体，任一侧都不计入，避免重复统计
    assert stats["o1"]["relation_count"] == 0
    assert stats["o2"]["relation_count"] == 0


def test_component_attached_directly_to_ontology(db):
    _ontology(db, "o1", "alpha")
    db.add(OntologyFunction(id="f1", entity_id=None, ontology_id="o1", name="fn"))
    db.add(EntityAction(
        id="a1", entity_id=None, ontology_id="o1",
        name="act", category="operation", action_type="http",
    ))
    db.commit()

    stats = EntityRepository(db).get_ontology_stats()
    assert stats["o1"]["logic_count"] == 1
    assert stats["o1"]["action_count"] == 1
    assert stats["o1"]["entity_count"] == 0


def test_self_relation_counted_once(db):
    _ontology(db, "o1", "alpha")
    _entity(db, "e1", "o1")
    db.add(EntityRelation(
        id="r1", from_entity_id="e1", to_entity_id="e1",
        name="self", rel_type="assoc", cardinality="1:1",
    ))
    db.commit()

    stats = EntityRepository(db).get_ontology_stats()
    assert stats["o1"]["relation_count"] == 1


def test_ontology_without_data_absent_from_stats(db):
    _ontology(db, "o1", "alpha")
    db.commit()

    stats = EntityRepository(db).get_ontology_stats()
    # 空本体不产生键，接口层用零值兜底
    assert "o1" not in stats
