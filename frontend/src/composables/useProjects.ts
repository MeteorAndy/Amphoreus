import { ref } from 'vue'

export interface Project {
  id: string
  name: string
  created_at: string
  updated_at: string
  last_stage: string
}

export interface CreateProjectPayload {
  name: string
  seed_idea: string
}

export function useProjects() {
  const projects = ref<Project[]>([])
  const loading = ref(false)
  const error = ref('')

  async function fetchProjects(): Promise<void> {
    loading.value = true
    error.value = ''
    try {
      const res = await fetch('/api/projects')
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      projects.value = data.projects ?? []
    } catch (e: unknown) {
      error.value = (e as Error).message
    } finally {
      loading.value = false
    }
  }

  async function createProject(name: string, seedIdea: string): Promise<string> {
    const res = await fetch('/api/projects', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, seed_idea: seedIdea }),
    })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const data = await res.json()
    await fetchProjects()
    return data.id as string
  }

  async function deleteProject(id: string): Promise<void> {
    const res = await fetch(`/api/projects/${id}`, { method: 'DELETE' })
    if (!res.ok && res.status !== 204) throw new Error(`HTTP ${res.status}`)
    projects.value = projects.value.filter((p) => p.id !== id)
  }

  return { projects, loading, error, fetchProjects, createProject, deleteProject }
}
