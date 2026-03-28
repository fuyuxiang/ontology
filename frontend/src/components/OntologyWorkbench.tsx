import { type ReactNode, useEffect, useMemo, useState } from "react";

import type {
  OntologyWorkspace,
  OntologyWorkspaceActionType,
  OntologyWorkspaceInterface,
  OntologyWorkspaceLinkType,
  OntologyWorkspaceObjectType,
  OntologyWorkspaceObjectTypeGroup,
  OntologyWorkspaceRule,
  OntologyWorkspaceSharedProperty,
} from "../types";

type ResourceGroupKey =
  | "objectTypes"
  | "sharedProperties"
  | "objectTypeGroups"
  | "linkTypes"
  | "actionTypes"
  | "interfaces"
  | "rules";
type DetailTabKey = "overview" | "schema" | "connections" | "governance";

type ObjectTypeResource = OntologyWorkspaceObjectType & { resourceType: "objectTypes" };
type SharedPropertyResource = OntologyWorkspaceSharedProperty & { resourceType: "sharedProperties" };
type ObjectTypeGroupResource = OntologyWorkspaceObjectTypeGroup & { resourceType: "objectTypeGroups" };
type LinkTypeResource = OntologyWorkspaceLinkType & { resourceType: "linkTypes" };
type ActionTypeResource = OntologyWorkspaceActionType & { resourceType: "actionTypes" };
type InterfaceResource = OntologyWorkspaceInterface & { resourceType: "interfaces" };
type RuleResource = OntologyWorkspaceRule & { resourceType: "rules" };

type WorkspaceResource =
  | ObjectTypeResource
  | SharedPropertyResource
  | ObjectTypeGroupResource
  | LinkTypeResource
  | ActionTypeResource
  | InterfaceResource
  | RuleResource;

const RESOURCE_GROUPS: Array<{ key: ResourceGroupKey; label: string }> = [
  { key: "objectTypes", label: "Object Types" },
  { key: "sharedProperties", label: "Shared Properties" },
  { key: "objectTypeGroups", label: "Object Type Groups" },
  { key: "linkTypes", label: "Link Types" },
  { key: "actionTypes", label: "Action Types" },
  { key: "interfaces", label: "Interfaces" },
  { key: "rules", label: "Rules" },
];

function resourceName(resource: WorkspaceResource) {
  return resource.name;
}

function resourceSummary(resource: WorkspaceResource) {
  if (resource.resourceType === "objectTypes") {
    return `${resource.sourceSystem} / ${resource.ontologyType}`;
  }
  if (resource.resourceType === "sharedProperties") {
    return `${resource.fields.length} mappings / ${resource.implementedBy.length} types`;
  }
  if (resource.resourceType === "objectTypeGroups") {
    return `${resource.objectTypeIds.length} object types`;
  }
  if (resource.resourceType === "linkTypes") {
    return `${resource.predicate} / ${resource.cardinality}`;
  }
  if (resource.resourceType === "actionTypes") {
    return `${resource.queueHint} / ${resource.allowedRoles.length} roles`;
  }
  if (resource.resourceType === "interfaces") {
    return `${resource.implementedBy.length} implemented types`;
  }
  return `${resource.riskLevel} / ${resource.hitCount} hits`;
}

function resourceBadges(resource: WorkspaceResource) {
  if (resource.resourceType === "objectTypes") {
    return [...resource.capabilityTags.slice(0, 3), ...resource.implements.slice(0, 1)];
  }
  if (resource.resourceType === "sharedProperties") {
    return resource.typeClasses;
  }
  if (resource.resourceType === "objectTypeGroups") {
    return [...resource.capabilities, ...resource.interfaceIds];
  }
  if (resource.resourceType === "linkTypes") {
    return resource.typeClasses;
  }
  if (resource.resourceType === "actionTypes") {
    return resource.allowedRiskLevels;
  }
  if (resource.resourceType === "interfaces") {
    return resource.capabilities;
  }
  return resource.signalProperties.slice(0, 3);
}

function matchesSearch(resource: WorkspaceResource, search: string) {
  if (!search.trim()) {
    return true;
  }
  const text = `${resource.name} ${resource.description} ${resourceSummary(resource)} ${resourceBadges(resource).join(" ")}`
    .toLowerCase();
  return text.includes(search.trim().toLowerCase());
}

function detailTabsForResource(resource: WorkspaceResource): Array<{ key: DetailTabKey; label: string }> {
  if (resource.resourceType === "objectTypes") {
    return [
      { key: "overview", label: "Overview" },
      { key: "schema", label: "Schema" },
      { key: "connections", label: "Connections" },
      { key: "governance", label: "Governance" },
    ];
  }
  if (resource.resourceType === "sharedProperties") {
    return [
      { key: "overview", label: "Overview" },
      { key: "schema", label: "Mappings" },
      { key: "connections", label: "Implementations" },
    ];
  }
  if (resource.resourceType === "objectTypeGroups") {
    return [
      { key: "overview", label: "Overview" },
      { key: "connections", label: "Members" },
      { key: "governance", label: "Contracts" },
    ];
  }
  if (resource.resourceType === "linkTypes") {
    return [
      { key: "overview", label: "Overview" },
      { key: "connections", label: "Endpoints" },
      { key: "governance", label: "Semantics" },
    ];
  }
  if (resource.resourceType === "actionTypes") {
    return [
      { key: "overview", label: "Overview" },
      { key: "governance", label: "Governance" },
      { key: "connections", label: "Bindings" },
    ];
  }
  if (resource.resourceType === "interfaces") {
    return [
      { key: "overview", label: "Overview" },
      { key: "schema", label: "Contract" },
      { key: "connections", label: "Members" },
    ];
  }
  return [
    { key: "overview", label: "Overview" },
    { key: "schema", label: "Signals" },
    { key: "connections", label: "Outputs" },
  ];
}

function formatChangeValue(value: unknown) {
  if (Array.isArray(value)) {
    return value.length ? value.join(", ") : "-";
  }
  if (value === null || value === undefined || value === "") {
    return "-";
  }
  return String(value);
}

function ResourceMetric({
  label,
  value,
}: {
  label: string;
  value: number;
}) {
  return (
    <div className="ontology-workbench-metric">
      <span className="ontology-workbench-metric-label">{label}</span>
      <strong className="ontology-workbench-metric-value">{value}</strong>
    </div>
  );
}

function DetailSection({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  return (
    <div className="ontology-workbench-section">
      <div className="ontology-workbench-section-title">{title}</div>
      {children}
    </div>
  );
}

function ReferenceList({
  ids,
  namesById,
  onPick,
}: {
  ids: string[];
  namesById: Map<string, string>;
  onPick: (id: string) => void;
}) {
  if (!ids.length) {
    return <div className="ontology-workbench-empty-inline">暂无关联资源。</div>;
  }
  return (
    <div className="ontology-reference-list">
      {ids.map((id) => (
        <button key={id} type="button" className="ontology-reference-chip" onClick={() => onPick(id)}>
          {namesById.get(id) || id}
        </button>
      ))}
    </div>
  );
}

export function OntologyWorkbench({
  workspace,
  loading,
  draftBusy,
  onSaveDraftChange,
  onPublishDraft,
  onRevertDraftChange,
  onDiscardDraft,
}: {
  workspace: OntologyWorkspace | null;
  loading: boolean;
  draftBusy: boolean;
  onSaveDraftChange: (payload: {
    resourceType: string;
    resourceId: string;
    changes: Record<string, unknown>;
  }) => void;
  onPublishDraft: () => void;
  onRevertDraftChange: (changeId: string) => void;
  onDiscardDraft: () => void;
}) {
  const [resourceGroup, setResourceGroup] = useState<ResourceGroupKey>("objectTypes");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detailTab, setDetailTab] = useState<DetailTabKey>("overview");
  const [search, setSearch] = useState("");
  const [descriptionDraft, setDescriptionDraft] = useState("");
  const [tagsDraft, setTagsDraft] = useState("");
  const [secondaryDraft, setSecondaryDraft] = useState("");

  const groupedResources = useMemo(() => {
    if (!workspace) {
      return {
        objectTypes: [],
        sharedProperties: [],
        objectTypeGroups: [],
        linkTypes: [],
        actionTypes: [],
        interfaces: [],
        rules: [],
      } as Record<ResourceGroupKey, WorkspaceResource[]>;
    }
    return {
      objectTypes: workspace.objectTypes.map((item) => ({ ...item, resourceType: "objectTypes" as const })),
      sharedProperties: workspace.sharedProperties.map((item) => ({ ...item, resourceType: "sharedProperties" as const })),
      objectTypeGroups: workspace.objectTypeGroups.map((item) => ({ ...item, resourceType: "objectTypeGroups" as const })),
      linkTypes: workspace.linkTypes.map((item) => ({ ...item, resourceType: "linkTypes" as const })),
      actionTypes: workspace.actionTypes.map((item) => ({ ...item, resourceType: "actionTypes" as const })),
      interfaces: workspace.interfaces.map((item) => ({ ...item, resourceType: "interfaces" as const })),
      rules: workspace.rules.map((item) => ({ ...item, resourceType: "rules" as const })),
    };
  }, [workspace]);

  const currentResources = useMemo(
    () => groupedResources[resourceGroup].filter((item) => matchesSearch(item, search)),
    [groupedResources, resourceGroup, search],
  );

  const allResources = useMemo(
    () =>
      Object.values(groupedResources)
        .flat()
        .reduce<Map<string, WorkspaceResource>>((map, item) => map.set(item.id, item), new Map()),
    [groupedResources],
  );

  const namesById = useMemo(
    () => new Map(Array.from(allResources.values()).map((item) => [item.id, item.name])),
    [allResources],
  );

  useEffect(() => {
    if (!currentResources.length) {
      setSelectedId(null);
      return;
    }
    if (!selectedId || !currentResources.some((item) => item.id === selectedId)) {
      setSelectedId(currentResources[0].id);
    }
  }, [currentResources, selectedId]);

  useEffect(() => {
    setDetailTab("overview");
  }, [selectedId, resourceGroup]);

  const selectedResource = selectedId ? allResources.get(selectedId) ?? null : null;
  const detailTabs = selectedResource ? detailTabsForResource(selectedResource) : [];
  const selectedResourceChanges = useMemo(
    () =>
      (workspace?.governance.changes ?? []).filter(
        (change) => change.resourceType === selectedResource?.resourceType && change.resourceId === selectedResource?.id,
      ),
    [selectedResource, workspace?.governance.changes],
  );

  useEffect(() => {
    if (!selectedResource) {
      setDescriptionDraft("");
      setTagsDraft("");
      setSecondaryDraft("");
      return;
    }
    setDescriptionDraft(selectedResource.description);
    if (selectedResource.resourceType === "objectTypes") {
      setTagsDraft(selectedResource.capabilityTags.join(", "));
      setSecondaryDraft("");
      return;
    }
    if (selectedResource.resourceType === "objectTypeGroups") {
      setTagsDraft(selectedResource.capabilities.join(", "));
      setSecondaryDraft("");
      return;
    }
    if (selectedResource.resourceType === "interfaces") {
      setTagsDraft(selectedResource.capabilities.join(", "));
      setSecondaryDraft(selectedResource.purpose);
      return;
    }
    if (selectedResource.resourceType === "actionTypes") {
      setTagsDraft(selectedResource.allowedRoles.join(", "));
      setSecondaryDraft(selectedResource.queueHint);
      return;
    }
    setTagsDraft("");
    setSecondaryDraft("");
  }, [selectedResource]);

  function splitCommaValues(value: string) {
    return value
      .split(",")
      .map((item) => item.trim())
      .filter((item) => item.length > 0);
  }

  function saveCurrentDraft() {
    if (!selectedResource) {
      return;
    }
    const changes: Record<string, unknown> = {
      description: descriptionDraft,
    };
    if (selectedResource.resourceType === "objectTypes") {
      changes.capabilityTags = splitCommaValues(tagsDraft);
    } else if (selectedResource.resourceType === "objectTypeGroups") {
      changes.capabilities = splitCommaValues(tagsDraft);
    } else if (selectedResource.resourceType === "interfaces") {
      changes.capabilities = splitCommaValues(tagsDraft);
      changes.purpose = secondaryDraft;
    } else if (selectedResource.resourceType === "actionTypes") {
      changes.allowedRoles = splitCommaValues(tagsDraft);
      changes.queueHint = secondaryDraft;
    }
    onSaveDraftChange({
      resourceType: selectedResource.resourceType,
      resourceId: selectedResource.id,
      changes,
    });
  }

  return (
    <div className="ontology-workbench-page">
      <div className="ontology-workbench-topbar">
        <div className="ontology-workbench-hero">
          <div className="ontology-workbench-eyebrow">Ontology Workspace</div>
          <h2 className="ontology-workbench-title">{workspace?.scenario.title || "本体工作台"}</h2>
          <p className="ontology-workbench-subtitle">
            {workspace?.scenario.subtitle || "把对象类型、链接类型、接口、规则和动作提升为产品的一等公民。"}
          </p>
        </div>
        <div className="ontology-workbench-metrics">
          <ResourceMetric label="Object Types" value={workspace?.metrics.objectTypeCount ?? 0} />
          <ResourceMetric label="Shared Props" value={workspace?.metrics.sharedPropertyCount ?? 0} />
          <ResourceMetric label="Groups" value={workspace?.metrics.objectTypeGroupCount ?? 0} />
          <ResourceMetric label="Link Types" value={workspace?.metrics.linkTypeCount ?? 0} />
          <ResourceMetric label="Action Types" value={workspace?.metrics.actionTypeCount ?? 0} />
          <ResourceMetric label="Interfaces" value={workspace?.metrics.interfaceCount ?? 0} />
          <ResourceMetric label="Rules" value={workspace?.metrics.ruleCount ?? 0} />
        </div>
      </div>

      <div className="ontology-philosophy-grid">
        {(workspace?.philosophy ?? []).map((item) => (
          <div key={item.title} className="ontology-philosophy-card">
            <strong>{item.title}</strong>
            <p>{item.description}</p>
          </div>
        ))}
      </div>

      <div className="ontology-governance-bar">
        <div className="ontology-governance-meta">
          <strong>{workspace?.governance.status === "draft" ? "Draft Active" : workspace?.governance.status === "published" ? "Published" : "Clean"}</strong>
          <span>Changes: {workspace?.governance.changeCount ?? 0}</span>
          <span>Draft ID: {workspace?.governance.draftId || "-"}</span>
          <span>Last Published: {workspace?.governance.lastPublishedAt || "-"}</span>
        </div>
        <div className="ontology-governance-actions">
          <button
            type="button"
            className="ontology-governance-btn"
            disabled={draftBusy || (workspace?.governance.changeCount ?? 0) === 0}
            onClick={onDiscardDraft}
          >
            {draftBusy ? "处理中..." : "Discard Draft"}
          </button>
          <button
            type="button"
            className="ontology-governance-btn primary"
            disabled={draftBusy || (workspace?.governance.changeCount ?? 0) === 0}
            onClick={onPublishDraft}
          >
            {draftBusy ? "处理中..." : "Publish Draft"}
          </button>
        </div>
      </div>

      <div className="ontology-workbench-shell">
        <aside className="ontology-workbench-sidebar">
          <div className="ontology-sidebar-search">
            <input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="搜索对象、关系、动作、接口、规则"
            />
          </div>

          <div className="ontology-sidebar-groups">
            {RESOURCE_GROUPS.map((item) => (
              <button
                key={item.key}
                type="button"
                className={`ontology-sidebar-group ${resourceGroup === item.key ? "active" : ""}`}
                onClick={() => setResourceGroup(item.key)}
              >
                <span>{item.label}</span>
                <strong>{groupedResources[item.key].length}</strong>
              </button>
            ))}
          </div>

          <div className="ontology-capability-list">
            {(workspace?.capabilities ?? []).map((item) => (
              <div key={item.name} className="ontology-capability-card">
                <strong>{item.name}</strong>
                <span>{item.summary}</span>
              </div>
            ))}
          </div>
        </aside>

        <section className="ontology-workbench-list">
          <div className="ontology-list-header">
            <div>
              <h3>{RESOURCE_GROUPS.find((item) => item.key === resourceGroup)?.label}</h3>
              <span>{currentResources.length} items</span>
            </div>
          </div>

          <div className="ontology-resource-list">
            {loading ? <div className="ontology-workbench-empty-inline">正在加载本体工作台...</div> : null}
            {!loading && !currentResources.length ? <div className="ontology-workbench-empty-inline">当前分组没有匹配资源。</div> : null}
            {!loading &&
              currentResources.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  className={`ontology-resource-card ${selectedId === item.id ? "active" : ""}`}
                  onClick={() => setSelectedId(item.id)}
                >
                  <div className="ontology-resource-title-row">
                    <strong>{resourceName(item)}</strong>
                    <span>{resourceSummary(item)}</span>
                  </div>
                  <p>{item.description}</p>
                  <div className="ontology-resource-tags">
                    {resourceBadges(item).slice(0, 4).map((badge: string) => (
                      <span key={`${item.id}-${badge}`} className="ontology-resource-tag">
                        {badge}
                      </span>
                    ))}
                  </div>
                </button>
              ))}
          </div>
        </section>

        <section className="ontology-workbench-detail">
          {!selectedResource ? (
            <div className="ontology-workbench-empty">选择左侧资源查看本体详情。</div>
          ) : (
            <>
              <div className="ontology-detail-header">
                <div>
                  <div className="ontology-detail-type">{selectedResource.resourceType}</div>
                  <h3>{selectedResource.name}</h3>
                </div>
                <div className="ontology-resource-tags">
                  {resourceBadges(selectedResource).slice(0, 4).map((badge: string) => (
                    <span key={`${selectedResource.id}-${badge}`} className="ontology-resource-tag">
                      {badge}
                    </span>
                  ))}
                </div>
              </div>

              <div className="ontology-detail-tabs">
                {detailTabs.map((tab) => (
                  <button
                    key={tab.key}
                    type="button"
                    className={`ontology-detail-tab ${detailTab === tab.key ? "active" : ""}`}
                    onClick={() => setDetailTab(tab.key)}
                  >
                    {tab.label}
                  </button>
                ))}
              </div>

              <div className="ontology-detail-body">
                {detailTab === "overview" ? (
                  <>
                    <DetailSection title="Overview">
                      <p className="ontology-detail-copy">{selectedResource.description}</p>
                    </DetailSection>

                    {selectedResource.resourceType === "objectTypes" ? (
                      <DetailSection title="Identity & Capabilities">
                        <div className="ontology-kv-grid">
                          <div>
                            <span>Source System</span>
                            <strong>{selectedResource.sourceSystem}</strong>
                          </div>
                          <div>
                            <span>Ontology Type</span>
                            <strong>{selectedResource.ontologyType}</strong>
                          </div>
                          <div>
                            <span>Identity Fields</span>
                            <strong>{selectedResource.identityFields.join(", ") || "-"}</strong>
                          </div>
                          <div>
                            <span>Title Field</span>
                            <strong>{selectedResource.titleField || "-"}</strong>
                          </div>
                        </div>
                      </DetailSection>
                    ) : null}

                    {selectedResource.resourceType === "sharedProperties" ? (
                      <DetailSection title="Footprint">
                        <div className="ontology-kv-grid">
                          <div>
                            <span>Implemented By</span>
                            <strong>{selectedResource.implementedBy.length}</strong>
                          </div>
                          <div>
                            <span>Property Mappings</span>
                            <strong>{selectedResource.fields.length}</strong>
                          </div>
                        </div>
                      </DetailSection>
                    ) : null}

                    {selectedResource.resourceType === "objectTypeGroups" ? (
                      <DetailSection title="Group Scope">
                        <div className="ontology-kv-grid">
                          <div>
                            <span>Object Types</span>
                            <strong>{selectedResource.objectTypeIds.length}</strong>
                          </div>
                          <div>
                            <span>Interfaces</span>
                            <strong>{selectedResource.interfaceIds.length}</strong>
                          </div>
                        </div>
                      </DetailSection>
                    ) : null}

                    {selectedResource.resourceType === "linkTypes" ? (
                      <DetailSection title="Endpoints">
                        <div className="ontology-kv-grid">
                          <div>
                            <span>Source</span>
                            <strong>{namesById.get(selectedResource.sourceObjectTypeId) || selectedResource.sourceObjectTypeId}</strong>
                          </div>
                          <div>
                            <span>Target</span>
                            <strong>{namesById.get(selectedResource.targetObjectTypeId) || selectedResource.targetObjectTypeId}</strong>
                          </div>
                          <div>
                            <span>Predicate</span>
                            <strong>{selectedResource.predicate}</strong>
                          </div>
                          <div>
                            <span>Cardinality</span>
                            <strong>{selectedResource.cardinality}</strong>
                          </div>
                        </div>
                      </DetailSection>
                    ) : null}

                    {selectedResource.resourceType === "actionTypes" ? (
                      <DetailSection title="Execution Semantics">
                        <div className="ontology-kv-grid">
                          <div>
                            <span>Queue Hint</span>
                            <strong>{selectedResource.queueHint}</strong>
                          </div>
                          <div>
                            <span>Side Effect</span>
                            <strong>{selectedResource.sideEffect}</strong>
                          </div>
                        </div>
                      </DetailSection>
                    ) : null}

                    {selectedResource.resourceType === "interfaces" ? (
                      <DetailSection title="Purpose">
                        <p className="ontology-detail-copy">{selectedResource.purpose}</p>
                      </DetailSection>
                    ) : null}

                    {selectedResource.resourceType === "rules" ? (
                      <DetailSection title="Rule Status">
                        <div className="ontology-kv-grid">
                          <div>
                            <span>Risk Level</span>
                            <strong>{selectedResource.riskLevel}</strong>
                          </div>
                          <div>
                            <span>Hit Count</span>
                            <strong>{selectedResource.hitCount}</strong>
                          </div>
                        </div>
                      </DetailSection>
                    ) : null}
                  </>
                ) : null}

                {detailTab === "schema" && selectedResource.resourceType === "objectTypes" ? (
                  <DetailSection title="Properties">
                    <div className="ontology-property-table">
                      {selectedResource.properties.map((property: OntologyWorkspaceObjectType["properties"][number]) => (
                        <div key={`${selectedResource.id}-${property.name}`} className="ontology-property-row">
                          <div>
                            <strong>{property.label}</strong>
                            <span>{property.name}</span>
                          </div>
                          <div className="ontology-resource-tags">
                            {property.typeClasses.map((item: string) => (
                              <span key={`${property.name}-${item}`} className="ontology-resource-tag subtle">
                                {item}
                              </span>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                  </DetailSection>
                ) : null}

                {detailTab === "schema" && selectedResource.resourceType === "sharedProperties" ? (
                  <DetailSection title="Property Mappings">
                    <div className="ontology-property-table">
                      {selectedResource.fields.map((field) => (
                        <div key={`${selectedResource.id}-${field.objectTypeId}-${field.propertyName}`} className="ontology-property-row">
                          <div>
                            <strong>{namesById.get(field.objectTypeId) || field.objectTypeId}</strong>
                            <span>
                              {field.label} / {field.propertyName}
                            </span>
                          </div>
                          <div className="ontology-resource-tags">
                            <span className="ontology-resource-tag subtle">{field.required ? "required" : "optional"}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </DetailSection>
                ) : null}

                {detailTab === "schema" && selectedResource.resourceType === "interfaces" ? (
                  <DetailSection title="Required Properties / Shared Properties">
                    <div className="ontology-resource-tags">
                      {selectedResource.requiredProperties.map((item: string) => (
                        <span key={`${selectedResource.id}-${item}`} className="ontology-resource-tag">
                          {item}
                        </span>
                      ))}
                    </div>
                    <div className="ontology-spacer-sm" />
                    <ReferenceList ids={selectedResource.sharedPropertyIds} namesById={namesById} onPick={setSelectedId} />
                  </DetailSection>
                ) : null}

                {detailTab === "schema" && selectedResource.resourceType === "rules" ? (
                  <DetailSection title="Signals">
                    <div className="ontology-resource-tags">
                      {selectedResource.signalProperties.map((item: string) => (
                        <span key={`${selectedResource.id}-${item}`} className="ontology-resource-tag">
                          {item}
                        </span>
                      ))}
                    </div>
                  </DetailSection>
                ) : null}

                {detailTab === "connections" && selectedResource.resourceType === "objectTypes" ? (
                  <>
                    <DetailSection title="Shared Properties / Groups">
                      <ReferenceList ids={selectedResource.sharedPropertyIds} namesById={namesById} onPick={setSelectedId} />
                      <div className="ontology-spacer-sm" />
                      <ReferenceList ids={selectedResource.groupIds} namesById={namesById} onPick={setSelectedId} />
                    </DetailSection>
                    <DetailSection title="Interfaces / Links / Actions">
                      <ReferenceList ids={selectedResource.implements} namesById={namesById} onPick={setSelectedId} />
                      <div className="ontology-spacer-sm" />
                      <ReferenceList
                        ids={[...selectedResource.incomingLinkTypeIds, ...selectedResource.outgoingLinkTypeIds]}
                        namesById={namesById}
                        onPick={setSelectedId}
                      />
                      <div className="ontology-spacer-sm" />
                      <ReferenceList ids={selectedResource.actionTypeIds} namesById={namesById} onPick={setSelectedId} />
                    </DetailSection>
                  </>
                ) : null}

                {detailTab === "connections" && selectedResource.resourceType === "sharedProperties" ? (
                  <DetailSection title="Implemented By">
                    <ReferenceList ids={selectedResource.implementedBy} namesById={namesById} onPick={setSelectedId} />
                  </DetailSection>
                ) : null}

                {detailTab === "connections" && selectedResource.resourceType === "objectTypeGroups" ? (
                  <>
                    <DetailSection title="Member Object Types">
                      <ReferenceList ids={selectedResource.objectTypeIds} namesById={namesById} onPick={setSelectedId} />
                    </DetailSection>
                    <DetailSection title="Applied Interfaces">
                      <ReferenceList ids={selectedResource.interfaceIds} namesById={namesById} onPick={setSelectedId} />
                    </DetailSection>
                  </>
                ) : null}

                {detailTab === "connections" && selectedResource.resourceType === "linkTypes" ? (
                  <DetailSection title="Connected Object Types">
                    <ReferenceList
                      ids={[selectedResource.sourceObjectTypeId, selectedResource.targetObjectTypeId]}
                      namesById={namesById}
                      onPick={setSelectedId}
                    />
                  </DetailSection>
                ) : null}

                {detailTab === "connections" && selectedResource.resourceType === "actionTypes" ? (
                  <DetailSection title="Bound Object Types / Interfaces">
                    <ReferenceList ids={selectedResource.boundObjectTypeIds} namesById={namesById} onPick={setSelectedId} />
                    <div className="ontology-spacer-sm" />
                    <ReferenceList ids={selectedResource.implements} namesById={namesById} onPick={setSelectedId} />
                  </DetailSection>
                ) : null}

                {detailTab === "connections" && selectedResource.resourceType === "interfaces" ? (
                  <DetailSection title="Implemented By">
                    <ReferenceList ids={selectedResource.implementedBy} namesById={namesById} onPick={setSelectedId} />
                  </DetailSection>
                ) : null}

                {detailTab === "connections" && selectedResource.resourceType === "rules" ? (
                  <DetailSection title="Outputs">
                    <ReferenceList ids={selectedResource.targetObjectTypeIds} namesById={namesById} onPick={setSelectedId} />
                    <div className="ontology-spacer-sm" />
                    <ReferenceList ids={selectedResource.actionTypeIds} namesById={namesById} onPick={setSelectedId} />
                  </DetailSection>
                ) : null}

                {detailTab === "governance" && selectedResource.resourceType === "objectTypes" ? (
                  <DetailSection title="Capabilities">
                    <div className="ontology-resource-tags">
                      {selectedResource.capabilityTags.map((item: string) => (
                        <span key={`${selectedResource.id}-${item}`} className="ontology-resource-tag">
                          {item}
                        </span>
                      ))}
                    </div>
                  </DetailSection>
                ) : null}

                {detailTab === "governance" && selectedResource.resourceType === "objectTypeGroups" ? (
                  <>
                    <DetailSection title="Capabilities">
                      <div className="ontology-resource-tags">
                        {selectedResource.capabilities.map((item: string) => (
                          <span key={`${selectedResource.id}-${item}`} className="ontology-resource-tag">
                            {item}
                          </span>
                        ))}
                      </div>
                    </DetailSection>
                    <DetailSection title="Contracts">
                      <ReferenceList ids={selectedResource.interfaceIds} namesById={namesById} onPick={setSelectedId} />
                    </DetailSection>
                  </>
                ) : null}

                {detailTab === "governance" && selectedResource.resourceType === "linkTypes" ? (
                  <DetailSection title="Semantics">
                    <div className="ontology-resource-tags">
                      {selectedResource.typeClasses.map((item: string) => (
                        <span key={`${selectedResource.id}-${item}`} className="ontology-resource-tag">
                          {item}
                        </span>
                      ))}
                    </div>
                  </DetailSection>
                ) : null}

                {detailTab === "governance" && selectedResource.resourceType === "actionTypes" ? (
                  <DetailSection title="Allowed Roles / States / Risks">
                    <div className="ontology-resource-tags">
                      {selectedResource.allowedRoles.map((item: string) => (
                        <span key={`${selectedResource.id}-${item}`} className="ontology-resource-tag">
                          {item}
                        </span>
                      ))}
                      {selectedResource.allowedStates.map((item: string) => (
                        <span key={`${selectedResource.id}-state-${item}`} className="ontology-resource-tag subtle">
                          {item}
                        </span>
                      ))}
                      {selectedResource.allowedRiskLevels.map((item: string) => (
                        <span key={`${selectedResource.id}-risk-${item}`} className="ontology-resource-tag subtle">
                          {item}
                        </span>
                      ))}
                    </div>
                  </DetailSection>
                ) : null}

                {detailTab === "governance" && selectedResource.resourceType === "interfaces" ? (
                  <DetailSection title="Capabilities">
                    <div className="ontology-resource-tags">
                      {selectedResource.capabilities.map((item: string) => (
                        <span key={`${selectedResource.id}-cap-${item}`} className="ontology-resource-tag subtle">
                          {item}
                        </span>
                      ))}
                    </div>
                  </DetailSection>
                ) : null}

                {detailTab === "governance" ? (
                  <>
                    <DetailSection title="Draft Editor">
                      <div className="ontology-editor-grid">
                        <label className="ontology-editor-field">
                          <span>Description</span>
                          <textarea value={descriptionDraft} onChange={(event) => setDescriptionDraft(event.target.value)} rows={4} />
                        </label>

                        {selectedResource.resourceType === "objectTypes" ? (
                          <label className="ontology-editor-field">
                            <span>Capability Tags</span>
                            <input value={tagsDraft} onChange={(event) => setTagsDraft(event.target.value)} placeholder="comma separated" />
                          </label>
                        ) : null}

                        {selectedResource.resourceType === "objectTypeGroups" ? (
                          <label className="ontology-editor-field">
                            <span>Capabilities</span>
                            <input value={tagsDraft} onChange={(event) => setTagsDraft(event.target.value)} placeholder="comma separated" />
                          </label>
                        ) : null}

                        {selectedResource.resourceType === "interfaces" ? (
                          <>
                            <label className="ontology-editor-field">
                              <span>Capabilities</span>
                              <input value={tagsDraft} onChange={(event) => setTagsDraft(event.target.value)} placeholder="comma separated" />
                            </label>
                            <label className="ontology-editor-field">
                              <span>Purpose</span>
                              <textarea value={secondaryDraft} onChange={(event) => setSecondaryDraft(event.target.value)} rows={3} />
                            </label>
                          </>
                        ) : null}

                        {selectedResource.resourceType === "actionTypes" ? (
                          <>
                            <label className="ontology-editor-field">
                              <span>Allowed Roles</span>
                              <input value={tagsDraft} onChange={(event) => setTagsDraft(event.target.value)} placeholder="comma separated" />
                            </label>
                            <label className="ontology-editor-field">
                              <span>Queue Hint</span>
                              <input value={secondaryDraft} onChange={(event) => setSecondaryDraft(event.target.value)} />
                            </label>
                          </>
                        ) : null}
                      </div>

                      <div className="ontology-governance-actions">
                        <button type="button" className="ontology-governance-btn" disabled={draftBusy} onClick={saveCurrentDraft}>
                          {draftBusy ? "处理中..." : "Save To Draft"}
                        </button>
                      </div>
                    </DetailSection>

                    <DetailSection title="Pending Changes">
                      {selectedResourceChanges.length ? (
                        <div className="ontology-change-list">
                          {selectedResourceChanges
                            .slice()
                            .reverse()
                            .map((change) => (
                              <div key={change.id} className="ontology-change-card">
                                <div className="ontology-change-head">
                                  <div>
                                    <strong>{change.field}</strong>
                                    <span>{change.actorId}</span>
                                  </div>
                                  <button
                                    type="button"
                                    className="ontology-governance-btn compact"
                                    disabled={draftBusy}
                                    onClick={() => onRevertDraftChange(change.id)}
                                  >
                                    回退
                                  </button>
                                </div>
                                <div className="ontology-change-values">
                                  <div>
                                    <span>Before</span>
                                    <strong>{formatChangeValue(change.oldValue)}</strong>
                                  </div>
                                  <div>
                                    <span>After</span>
                                    <strong>{formatChangeValue(change.newValue)}</strong>
                                  </div>
                                </div>
                                <div className="ontology-change-time">{change.time}</div>
                              </div>
                            ))}
                        </div>
                      ) : (
                        <div className="ontology-workbench-empty-inline">当前资源还没有待发布变更。</div>
                      )}
                    </DetailSection>
                  </>
                ) : null}
              </div>
            </>
          )}
        </section>
      </div>
    </div>
  );
}
