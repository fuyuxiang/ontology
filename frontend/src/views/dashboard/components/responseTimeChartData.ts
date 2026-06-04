import type { ResponseHistoryPoint } from '../../../api/monitor'

export interface ResponseTimeSeriesData {
  name: string
  points: Array<[string, number | null]>
}

export interface ResponseTimeChartData {
  series: ResponseTimeSeriesData[]
}

export function buildResponseTimeChartData(data: ResponseHistoryPoint[]): ResponseTimeChartData {
  const pointsByService = new Map<string, Array<[string, number | null]>>()

  for (const point of data) {
    const points = pointsByService.get(point.service_name) ?? []
    points.push([point.collected_at, point.response_ms])
    pointsByService.set(point.service_name, points)
  }

  const series = Array.from(pointsByService.entries()).map(([name, points]) => {
    return {
      name,
      points: points.sort(([left], [right]) => left.localeCompare(right)),
    }
  })

  return { series }
}
