import pytest
import json
from pydantic import ValidationError
from app.schemas.ontology_output import OntologyOutput, OntologyEntity, OntologyAttribute, OntologyRelation


class TestOntologyAttribute:
    def test_valid_attribute(self):
        attr = OntologyAttribute(
            name="customer_id",
            display_name="客户编号",
            type="string",
            required=True,
            description="客户唯一标识",
        )
        assert attr.name == "customer_id"

    def test_invalid_name_not_snake_case(self):
        with pytest.raises(ValidationError):
            OntologyAttribute(
                name="CustomerID",
                display_name="客户编号",
                type="string",
                required=True,
                description="客户唯一标识",
            )

    def test_display_name_too_long(self):
        with pytest.raises(ValidationError):
            OntologyAttribute(
                name="customer_id",
                display_name="这个中文名超过了十个汉字的限制要求",
                type="string",
                required=True,
                description="desc",
            )

    def test_invalid_type(self):
        with pytest.raises(ValidationError):
            OntologyAttribute(
                name="customer_id",
                display_name="客户编号",
                type="invalid_type",
                required=True,
                description="desc",
            )


class TestOntologyEntity:
    def test_valid_entity(self):
        entity = OntologyEntity(
            name="BroadbandOrder",
            name_cn="宽带订单",
            tier=2,
            description="宽带业务订单",
            attributes=[
                OntologyAttribute(name="order_id", display_name="订单号", type="string", required=True, description="唯一标识")
            ],
        )
        assert entity.name == "BroadbandOrder"

    def test_invalid_name_not_pascal_case(self):
        with pytest.raises(ValidationError):
            OntologyEntity(
                name="broadband_order",
                name_cn="宽带订单",
                tier=2,
                description="desc",
                attributes=[
                    OntologyAttribute(name="id", display_name="编号", type="string", required=True, description="d")
                ],
            )

    def test_empty_attributes(self):
        with pytest.raises(ValidationError):
            OntologyEntity(
                name="BroadbandOrder",
                name_cn="宽带订单",
                tier=2,
                description="desc",
                attributes=[],
            )


class TestOntologyRelation:
    def test_valid_relation(self):
        rel = OntologyRelation(
            from_entity="Customer",
            to_entity="Product",
            name="subscribesTo",
            rel_type="has_many",
            cardinality="1:N",
        )
        assert rel.name == "subscribesTo"

    def test_relation_name_not_camel_case(self):
        with pytest.raises(ValidationError):
            OntologyRelation(from_entity="A", to_entity="B", name="relates_to", rel_type="has_one", cardinality="1:1")


class TestOntologyOutput:
    def test_valid_output(self):
        output = OntologyOutput(
            entities=[
                OntologyEntity(
                    name="Customer", name_cn="客户", tier=1, description="客户实体",
                    attributes=[OntologyAttribute(name="customer_id", display_name="客户编号", type="string", required=True, description="唯一标识")],
                ),
                OntologyEntity(
                    name="Product", name_cn="产品", tier=1, description="产品实体",
                    attributes=[OntologyAttribute(name="product_name", display_name="产品名", type="string", required=True, description="名称")],
                ),
            ],
            relations=[
                OntologyRelation(from_entity="Customer", to_entity="Product", name="subscribesTo", rel_type="has_many", cardinality="1:N")
            ],
        )
        assert len(output.entities) == 2

    def test_relation_references_nonexistent_entity(self):
        with pytest.raises(ValidationError):
            OntologyOutput(
                entities=[
                    OntologyEntity(
                        name="Customer", name_cn="客户", tier=1, description="desc",
                        attributes=[OntologyAttribute(name="id", display_name="编号", type="string", required=True, description="d")],
                    )
                ],
                relations=[
                    OntologyRelation(from_entity="NonExistent", to_entity="Customer", name="relatesTo", rel_type="has_one", cardinality="1:1")
                ],
            )

    def test_empty_entities(self):
        with pytest.raises(ValidationError):
            OntologyOutput(entities=[], relations=[])


from app.services.ontology_constraints import build_constraint_prompt


class TestBuildConstraintPrompt:
    def test_returns_string(self):
        prompt = build_constraint_prompt()
        assert isinstance(prompt, str)
        assert len(prompt) > 100

    def test_contains_naming_rules(self):
        prompt = build_constraint_prompt()
        assert "PascalCase" in prompt
        assert "snake_case" in prompt
        assert "camelCase" in prompt

    def test_contains_tier_rules(self):
        prompt = build_constraint_prompt()
        assert "T1" in prompt
        assert "T2" in prompt
        assert "T3" in prompt

    def test_contains_telecom_knowledge(self):
        prompt = build_constraint_prompt()
        assert "客户" in prompt
        assert "用户" in prompt

    def test_with_existing_entities(self):
        existing = ["Customer", "Product"]
        prompt = build_constraint_prompt(existing_entities=existing)
        assert "Customer" in prompt
        assert "Product" in prompt

    def test_without_existing_entities(self):
        prompt = build_constraint_prompt(existing_entities=None)
        assert "已有实体" not in prompt
