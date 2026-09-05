import { defineStore } from 'pinia'
import { http } from '@/api/http'

export interface UserInfo {
  id: number
  email: string
  nickname: string
  avatar_url: string | null
}

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: localStorage.getItem('token') ?? '',
    user: null as UserInfo | null,
  }),
  getters: {
    isLoggedIn: (state) => !!state.token,
  },
  actions: {
    async register(email: string, password: string, nickname: string) {
      const { data } = await http.post('/auth/register', { email, password, nickname })
      this._apply(data.token, data.user)
    },
    async login(email: string, password: string) {
      const { data } = await http.post('/auth/login', { email, password })
      this._apply(data.token, data.user)
    },
    async fetchMe() {
      const { data } = await http.get('/auth/me')
      this.user = data
    },
    logout() {
      this.token = ''
      this.user = null
      localStorage.removeItem('token')
    },
    _apply(token: string, user: UserInfo) {
      this.token = token
      this.user = user
      localStorage.setItem('token', token)
    },
  },
})
