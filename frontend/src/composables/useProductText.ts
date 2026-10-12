import { productDataSource } from '../locales/productDataSource'
import productBusiness from '../locales/productBusiness'
import { usePlatformConfigStore } from '../store/platformConfig'

// Only interface copy is translated. Names, uploaded documents and server receipts
// keep their original language so switching language never changes business data.
const english: Record<string, string> = {
  '文档上传': 'Upload documents', 'AI对话建模': 'Model with AI', '语义映射': 'Semantic mapping', '映射持久化': 'Confirm mappings',
  '目标本体': 'Target ontology', '请选择目标本体': 'Select an ontology', '新本体名称': 'New ontology name', '新建本体': 'Create ontology',
  '工具选择': 'Editor', '本地构建': 'Local builder', '进入业务审核、映射与发布': 'Map, review and publish', '解析中…': 'Parsing…',
  '返回对象定义': 'Back to object definition', '手工建模': 'Define objects', '文件导入': 'Import file', '文档抽取': 'Extract documents', '对话生成': 'Generate with chat',
  '业务描述': 'Business description', '选择数据表': 'Select tables', '选择文档': 'Select documents', 'AI提取': 'AI extraction',
  '数据映射': 'Data mapping', '最终审核': 'Final review', '专家审批': 'Final review', '专家审核': 'Final review', '水合验证': 'Validate and publish', '验证发布': 'Validate and publish',
  '← 返回': '← Back', '返回': 'Back', '一键推荐': 'Suggest mappings', '推荐中...': 'Suggesting…', '进入最终审核 →': 'Continue to final review →',
  '对象': 'Objects', '字段映射': 'Field mappings', '数据资产': 'Data assets', '关联': 'Bind', '解除关联': 'Unbind', '拖入数据表关联': 'Bind a source table',
  '属性名': 'Property', '类型': 'Type', '来源资产': 'Source asset', '映射字段': 'Source column', '置信度': 'Confidence', '选择字段': 'Select a column',
  '搜索表名或字段...': 'Search tables or columns…', '加载中...': 'Loading…', '正在推荐字段映射...': 'Suggesting column mappings…',
  '从右侧数据资产树中选择一张表拖到左栏对象上，或点击表旁的"关联"按钮': 'Choose a table in Data assets and select Bind. On desktop you can also drag a table onto an object.',
  '← 选择一个对象查看映射详情': 'Select an object to view its mappings.', '关系字段映射': 'Relationship mappings',
  '选择两端真实关联属性，验证时使用其已确认的源字段进行 JOIN。': 'Select a mapped property at each end. Validation uses the confirmed source columns for the join.',
  '选择源关联属性': 'Source join property', '选择目标关联属性': 'Target join property',
  '✅ 一键全部通过': 'Approve all objects', '完成审批': 'Finish final review', '确认通过': 'Approve', '✓ 已通过': 'Approved', '已通过': 'Approved', '待确认': 'Pending',
  '基本信息': 'Definition', '名称（英文，PascalCase）': 'Name (PascalCase)', '中文名': 'Display name', '描述': 'Description', '实例主键属性': 'Primary key property',
  '＋ 新建对象': '＋ Add object', '＋ 添加属性': '＋ Add property', '中文属性名': 'Display name', '中文名 ': 'Display name ', '英文名': 'Name',
  '点击或拖拽文件到此区域': 'Select or drop a file here', '正在解析…': 'Parsing…', '解析结果': 'Parsed definition', '已解析': 'Parsed',
  '关联关系': 'Relationships', '属性总数': 'Properties', '动作': 'Actions', '文件大小': 'File size', '本体对象（前 10 个）': 'Objects (first 10)',
  '重新选择文件': 'Choose another file', '确认导入 · 已有本体 →': 'Confirm import →',
  '数据源选择': 'Data sources', '全选': 'Select all', '清空': 'Clear', '开始演练': 'Run validation', '加载资产中...': 'Loading assets…', '重新演练': 'Retry validation',
  '演练进行中': 'Validation in progress', '演练失败 · 请检查日志后重试': 'Validation failed. Check the log and retry.',
  '演练完成 · 全部通过': 'Validation passed', '演练完成 · 存在警告': 'Validation completed with warnings',
  '发布门禁': 'Publication checks', '本体概览': 'Ontology summary', '版本信息': 'Version', '发布至本体工作室': 'Publish ontology', '确认发布': 'Confirm publication',
  '发布成功': 'Published successfully', '当前内容已审核': 'Current definition approved', '内容已修改，请返回专家审核': 'Definition changed. Complete final review again.',
  '本体结构完整': 'Definition complete', '水合演练通过': 'Validation passed', '版本就绪': 'Version ready', '对象审核通过': 'Objects approved',
  '定义对象、属性、关系': 'Define objects, properties and relationships', '数据源接入 · 属性列映射': 'Bind assets and map columns',
  '审核对象、关系与已确认映射': 'Approve the definition and confirmed mappings', '端到端数据验证 · 发布上线': 'Validate with real data and publish',
  '本体服务': 'Ontology services', '服务概览': 'Service overview', '接入文档': 'Integration guide', '今日调用': 'Calls today', '平均响应': 'Average response', '错误率': 'Error rate', '并发请求': 'Active requests',
  '调用趋势': 'Call trend', '工具分布': 'Tool distribution', '工具健康': 'Tool health', '工具名称': 'Tool', '调用次数': 'Calls', '平均耗时': 'Average duration', '错误数': 'Errors', '最近调用': 'Last call',
  '暂无数据': 'No data', '暂无工具调用记录': 'No tool calls recorded', '该时间范围暂无调用记录': 'No calls in this time range', '重试': 'Retry', '复制': 'Copy', '已复制': 'Copied',
}

export function productText(value: string, params: Record<string, unknown> = {}): string {
  const platform = usePlatformConfigStore()
  const translated = platform.language === 'en' ? productDataSource[value] || productBusiness[value] || english[value] || value : value
  return translated.replace(/\{(\w+)\}/g, (match, key) => key in params ? String(params[key]) : match)
}

export function useProductText() {
  return { text: productText }
}
