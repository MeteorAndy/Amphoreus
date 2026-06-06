import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { useProjects, type Project } from './useProjects'

function jsonResponse(body: unknown, ok = true, status = 200): Response {
  return {
    ok,
    status,
    json: async () => body,
  } as Response
}

const sample: Project[] = [
  { id: 'p1', name: 'One', created_at: '', updated_at: '', last_stage: 'world' },
  { id: 'p2', name: 'Two', created_at: '', updated_at: '', last_stage: 'plot' },
]

describe('useProjects', () => {
  let fetchMock: ReturnType<typeof vi.fn>

  beforeEach(() => {
    fetchMock = vi.fn()
    globalThis.fetch = fetchMock as unknown as typeof fetch
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('fetchProjects populates projects from {projects: [...]}', async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse({ projects: sample }))
    const { projects, loading, fetchProjects } = useProjects()

    await fetchProjects()

    expect(fetchMock).toHaveBeenCalledWith('/api/projects')
    expect(projects.value).toEqual(sample)
    expect(loading.value).toBe(false)
  })

  it('fetchProjects defaults to an empty array when projects is absent', async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse({}))
    const { projects, fetchProjects } = useProjects()

    await fetchProjects()

    expect(projects.value).toEqual([])
  })

  it('fetchProjects sets error ref on a non-ok response', async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse(null, false, 500))
    const { error, loading, fetchProjects } = useProjects()

    await fetchProjects()

    expect(error.value).toBe('HTTP 500')
    expect(loading.value).toBe(false)
  })

  it('createProject POSTs the payload, refetches, and returns the new id', async () => {
    fetchMock
      .mockResolvedValueOnce(jsonResponse({ id: 'new-id' }))
      .mockResolvedValueOnce(jsonResponse({ projects: sample }))
    const { projects, createProject } = useProjects()

    const id = await createProject('My Story', 'a seed idea')

    expect(id).toBe('new-id')
    const [url, opts] = fetchMock.mock.calls[0]
    expect(url).toBe('/api/projects')
    expect(opts.method).toBe('POST')
    expect(JSON.parse(opts.body)).toEqual({ name: 'My Story', seed_idea: 'a seed idea' })
    expect(fetchMock.mock.calls[1][0]).toBe('/api/projects')
    expect(projects.value).toEqual(sample)
  })

  it('createProject throws on a non-ok response', async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse(null, false, 400))
    const { createProject } = useProjects()

    await expect(createProject('x', 'y')).rejects.toThrow('HTTP 400')
  })

  it('deleteProject removes the project from the local list', async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse({ projects: sample }))
    const { projects, fetchProjects, deleteProject } = useProjects()
    await fetchProjects()

    fetchMock.mockResolvedValueOnce(jsonResponse(null, true, 204))
    await deleteProject('p1')

    expect(fetchMock).toHaveBeenLastCalledWith('/api/projects/p1', { method: 'DELETE' })
    expect(projects.value.map((p) => p.id)).toEqual(['p2'])
  })

  it('deleteProject throws on an error status other than 204', async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse(null, false, 500))
    const { deleteProject } = useProjects()

    await expect(deleteProject('p1')).rejects.toThrow('HTTP 500')
  })
})
