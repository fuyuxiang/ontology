// A common artifact between the real UI exporter and backend import regressions.
export const ontology = {
  id: 'review', iri: 'https://example.test/ontology', versionIRI: 'https://example.test/ontology/v1',
  namespaces: [{prefix:'ex',iri:'https://example.test/ontology#'}], annotations: [], individuals: [],
  classes: ['Asset','Device','WorkOrder'].map(name => ({id:name,iri:`ex:${name}`,localName:name,
    annotations: [{id:`label-${name}`,property:'rdfs:label',value:name === 'Device' ? '设备 & 告警' : name,language:'zh'}],
    superClassExpressions:name === 'Device' ? [{id:'parent',type:'namedClass',classIRI:'ex:Asset'}] : [], equivalentClassExpressions:[],disjointWith:[]})),
  dataProperties: [{id:'risk',iri:'ex:risk',localName:'risk',annotations:[],superProperties:[],domains:['ex:Device'],ranges:['xsd:double'],functional:false}],
  objectProperties: [{id:'hasOrder',iri:'ex:hasOrder',localName:'hasOrder',annotations:[],superProperties:[],domains:['ex:Device'],ranges:['ex:WorkOrder'],characteristics:[],inverseOf:null}]
}
