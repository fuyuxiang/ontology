import { post } from './client'
import type {
  DryRunResult, ExecuteRequest, ExecuteResult,
} from '../types/execution'

export function execute(req: ExecuteRequest) {
  return post<ExecuteResult>('/execute', req)
}

export function dryRun(req: ExecuteRequest) {
  return post<DryRunResult>('/execute/dry-run', req)
}
