"""逻辑与动作创建时 ontology_id 的字段契约测试。

前端在本体详情页内新建逻辑/动作时会带上 ontology_id，但 FunctionCreate /
ActionCreate 曾未声明该字段，pydantic 默认忽略未声明入参，导致该值被静默丢弃：
不绑定实体的逻辑既不计入本体统计，也不出现在按 ontology_id 过滤的列表里。
这里锁定「schema 接得住 + 建模落得下 + 统计数得到」这条链路。
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import ScenarioDict
from app.models.action import EntityAction
from app.models.function import OntologyFunction
from app.repositories.entity_repo import EntityRepository
from app.repositories.function_repo import FunctionRepository
from app.schemas.action import ActionCreate
from app.schemas.function import FunctionCreate


@pytest.fixture()
def db():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


def test_function_create_schema_keeps_ontology_id():
    data = FunctionCreate(name="fn", ontology_id="o1")
    assert data.ontology_id == "o1"


def test_action_create_schema_keeps_ontology_id():
    data = ActionCreate(name="act", category="system", action_type="api_call", ontology_id="o1")
    assert data.ontology_id == "o1"


def test_unbound_function_is_visible_and_counted(db):
    """不绑定实体、仅挂本体的逻辑：既能被列表查到，也计入统计。"""
    db.add(ScenarioDict(id="o1", code="alpha", name="alpha"))
    data = FunctionCreate(name="fn", ontology_id="o1")
    db.add(OntologyFunction(
        entity_id=data.entity_id, entity_ids=data.entity_ids or [],
        ontology_id=data.ontology_id, name=data.name,
    ))
    db.commit()

    listed = FunctionRepository(db).list_with_filters(ontology_id="o1")
    assert [f.name for f in listed] == ["fn"]
    assert EntityRepository(db).get_ontology_stats()["o1"]["logic_count"] == 1


def test_unbound_action_is_counted(db):
    db.add(ScenarioDict(id="o1", code="alpha", name="alpha"))
    data = ActionCreate(name="act", category="system", action_type="api_call", ontology_id="o1")
    db.add(EntityAction(**data.model_dump()))
    db.commit()

    assert EntityRepository(db).get_ontology_stats()["o1"]["action_count"] == 1


def test_function_without_ontology_id_stays_unbound(db):
    """未传 ontology_id 时不应臆造归属，避免逻辑被错误计入某个本体。"""
    db.add(ScenarioDict(id="o1", code="alpha", name="alpha"))
    data = FunctionCreate(name="fn")
    assert data.ontology_id is None
    db.add(OntologyFunction(ontology_id=data.ontology_id, name=data.name))
    db.commit()

    assert "o1" not in EntityRepository(db).get_ontology_stats()
