export interface TaskCreate {
  goal: string
  spec: string
  prjdir: string
  max_steps?: number
  enable_commits?: boolean
  commit_branch?: string
}

export type TaskStatusEnum = 'pending' | 'running' | 'completed' | 'failed' | 'stopped'
export type CurrentStepEnum = 'thinking' | 'code_writing' | 'code_executing' | 'frontend_verify' | 'idle' | 'error'

export interface TaskStatus {
  id: string
  goal: string
  status: TaskStatusEnum
  current_step: string
  step_number: number
  max_steps: number
  created_at: string
  updated_at: string
  prjdir: string
  spec?: string
  enable_commits?: boolean
}

export type EventType = 'thinking' | 'code_writing' | 'code_executing' | 'frontend_verify' | 'goal_achieved' | 'error' | 'screenshot' | 'state_check'

export interface AgentEvent {
  task_id: string
  event_type: EventType
  timestamp: string
  data: Record<string, any>
}

export interface FileNode {
  name: string
  path: string
  is_directory: boolean
  children?: FileNode[]
  size?: number
  modified_at?: string
}

export type VerificationStatusEnum = 'OK' | 'NEEDS_WORK' | 'BROKEN'

export interface VerificationResult {
  route: string
  screenshot_path: string
  screenshot_base64?: string
  analysis: string
  status: VerificationStatusEnum
}
