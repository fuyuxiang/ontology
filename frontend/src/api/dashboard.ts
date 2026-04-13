import { get } from './client'
import type { DashboardStats } from '../types'

export const dashboardApi = {
  stats() {
    return get<DashboardStats>('/dashboard/stats')
  },
}
