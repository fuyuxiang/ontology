import i18n from '../i18n'

const routeKeys: Record<string, string> = {
  登录: 'login', 系统看版: 'dashboard', 数据接入: 'connections', 资产目录: 'assets', 本体列表: 'ontologies', 本体详情: 'ontologyDetail',
  手动构建: 'manualBuilder', 模板构建: 'templateBuilder', 文档构建: 'documentBuilder', 资产构建: 'assetBuilder',
  逻辑建模: 'functions', 函数编辑: 'functionEditor', 行动建模: 'actions', 动作编辑: 'actionEditor', 本体发布: 'publish', 本体服务: 'services',
  智能体管理: 'agents', 新建智能体: 'newAgent', 智能体详情: 'agentDetail', 业务技能: 'skills', 新建业务技能: 'newSkill', 技能详情: 'skillDetail', 系统配置: 'config', 首页: 'home',
}
export function platformRouteTitle(title?: string): string {
  const key = routeKeys[title || '首页']
  return key ? i18n.global.t(`shell.${key}`) : title || i18n.global.t('shell.home')
}
