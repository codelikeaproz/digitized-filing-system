import Axios from 'axios'
import { getAccessToken } from '@/lib/auth'


const api = Axios.create({
    baseURL: import.meta.env.VITE_API_URL
})


api.interceptors.request.use(
    (config) => {
        const token = getAccessToken()
        if (token) {
            config.headers.Authorization = `Bearer ${token}`
        }
        return config
    },
    (error) => {
        return Promise.reject(error)
    }
)


export default api
