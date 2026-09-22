import axios from 'axios'
import { ElMessage } from 'element-plus'

const http = axios.create({
  baseURL: '/api',
  timeout: 20000,
})

http.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const data = error.response?.data as { detail?: string } | undefined
    const message = data?.detail || error.message || '请求失败，请稍后重试'
    ElMessage.error(String(message))
    return Promise.reject(error)
  },
)

export async function apiGet<T>(url: string, params?: object): Promise<T> {
  return (await http.get(url, { params })) as T
}

export async function apiPost<T>(url: string, data?: object): Promise<T> {
  return (await http.post(url, data)) as T
}

export async function apiPut<T>(url: string, data?: object): Promise<T> {
  return (await http.put(url, data)) as T
}

export async function apiDelete<T>(url: string): Promise<T> {
  return (await http.delete(url)) as T
}
