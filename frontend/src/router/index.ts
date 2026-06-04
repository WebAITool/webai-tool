import { createRouter, createWebHistory } from 'vue-router'
import MainLayout from '../layouts/MainLayout.vue'

// Lazy load pages
const Dashboard = () => import('../pages/DashboardPage.vue')
const NewTask = () => import('../pages/NewTaskPage.vue')
const TaskList = () => import('../pages/TaskListPage.vue')
const TaskDetail = () => import('../pages/TaskDetailPage.vue')
const FileBrowser = () => import('../pages/FileBrowserPage.vue')
const VerificationGallery = () => import('../pages/VerificationGalleryPage.vue')
const Settings = () => import('../pages/SettingsPage.vue')

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      component: MainLayout,
      children: [
        { path: '', name: 'Dashboard', component: Dashboard },
        { path: 'tasks/new', name: 'NewTask', component: NewTask },
        { path: 'tasks', name: 'TaskList', component: TaskList },
        { path: 'tasks/:id', name: 'TaskDetail', component: TaskDetail },
        { path: 'files', name: 'FileBrowser', component: FileBrowser },
        { path: 'verification/:task_id', name: 'VerificationGallery', component: VerificationGallery },
        { path: 'settings', name: 'Settings', component: Settings }
      ]
    }
  ]
})

export default router
